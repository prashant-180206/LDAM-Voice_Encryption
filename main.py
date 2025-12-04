# voice_continuous_main_arduino_final.py
import json
import queue
import sounddevice as sd
import soundfile as sf
import time
import threading
import os
import sys
import serial
import numpy as np
import librosa
import uuid
from vosk import Model, KaldiRecognizer
from collections import deque
from speechbrain.inference.speaker import SpeakerRecognition

# ===== CONFIG =====
SAMPLE_RATE = 16000
CHANNELS = 1
VOSK_MODEL_PATH = "model/model"   # path to vosk model folder
REF_VOICE = "refVoice.wav"

# base names (unique files will be created per capture)
AUDIO_TEMP_BASE = "captured_command"
AUDIO_FIXED_BASE = "captured_fixed"

ARDUINO_PORT = "COM5"
ARDUINO_BAUD = 9600

# pre-roll (include a little audio when starting recording)
PRE_ROLL_SECONDS = 0.5

# min duration for verifier (seconds). fix_audio_format will pad to this.
MIN_VERIFY_SECONDS = 1.8

# minimum duration to accept a captured clip (don't store/verify anything shorter)
MIN_ACCEPT_SECONDS = 1.5

# trim / normalization settings
TRIM_TOP_DB = 25
TARGET_RMS = 0.1

# cooldown (seconds) per command to avoid repeated triggers
TRIGGER_COOLDOWN = 1.0

# optional tiny post-buffer (in seconds) to capture trailing phonemes after detection
POST_BUFFER_SECONDS = 0.0   # set to 0.15-0.3 if you want a short tail

# Gap before starting the next recording — user requested 500 ms (0.5s)
NEXT_RECORD_GAP_SECONDS = 0.5

# Map words to Arduino commands (strings). Arduino reads string commands like "left", "right".
signal_to_command = {
    "on": "forward",      # adjust if you want 1:1 mapping
    "off": "stop",
    "of": "stop",
    "turn": "forward",
    "stop": "stop",
    "left": "left",
    "right": "right",
    "forward": "forward",
    "backward": "backward",
}

# keywords
WAKE_WORD = "alexa"
END_WORD = "go"

# ===== STATE =====
audio_q = queue.Queue()
# rolling pre-roll bytes queue (keeps last PRE_ROLL_SECONDS)
rolling_chunks = deque()
rolling_bytes = 0
max_rolling_bytes = int(SAMPLE_RATE * PRE_ROLL_SECONDS) * 2  # bytes (int16 = 2 bytes/sample)

# active continuous recording buffer
is_recording = False
recording_buffer = bytearray()
stop_all = False

# last trigger times per command word to debounce
last_trigger_time = {}
trigger_lock = threading.Lock()

# verification file read/write lock (extra safety)
verify_lock = threading.Lock()

# prevent starting new recording until this timestamp
next_record_allowed_at = 0.0

# track temp files to cleanup on exit
temp_files = set()

# ===== SERIAL =====
ser = None
try:
    ser = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
    time.sleep(2)
    print("✅ Connected to Arduino on", ARDUINO_PORT)
except Exception as e:
    print("⚠️ Serial not opened:", e)
    ser = None

# ===== MODELS =====
if not os.path.exists(VOSK_MODEL_PATH):
    print(f"Vosk model not found at '{VOSK_MODEL_PATH}'. Please download it and set VOSK_MODEL_PATH.")
    sys.exit(1)

model = Model(VOSK_MODEL_PATH)
verification = SpeakerRecognition.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
)


# ===== UTIL FUNCTIONS =====
def send_command_to_arduino(cmd_str):
    """Send an ASCII command string (with newline) to Arduino/Bluetooth module."""
    if ser and ser.is_open:
        try:
            ser.write((cmd_str + "\n").encode())
            print(f"📨 Sent to Arduino: {cmd_str}")
        except Exception as e:
            print("⚠️ Serial write error:", e)
    else:
        # Simulation if serial not connected
        print(f"🔌 (Simulated) Would send to Arduino: {cmd_str}")


def write_wav_from_bytes(path, bytes_data, samplerate=SAMPLE_RATE):
    arr = np.frombuffer(bytes_data, dtype=np.int16)
    sf.write(path, arr, samplerate, subtype='PCM_16')  # blocking write
    temp_files.add(path)


def fix_audio_format(src_path, dst_path, target_sr=SAMPLE_RATE, min_dur=MIN_VERIFY_SECONDS,
                     trim_silence=True, top_db=TRIM_TOP_DB, target_rms=TARGET_RMS):
    """
    Normalize/resample/trim/pad & write 16-bit PCM to dst_path.
    Ensures at least min_dur seconds of audio (pads with silence).
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(src_path)
    y, sr = librosa.load(src_path, sr=None, mono=True)
    if sr != target_sr:
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
        sr = target_sr
    if trim_silence:
        y_trimmed, _ = librosa.effects.trim(y, top_db=top_db)
    else:
        y_trimmed = y
    cur_dur = len(y_trimmed) / sr
    if cur_dur < min_dur:
        need = int((min_dur - cur_dur) * sr)
        left = need // 2
        right = need - left
        y_trimmed = np.concatenate([np.zeros(left, dtype=y_trimmed.dtype),
                                    y_trimmed,
                                    np.zeros(right, dtype=y_trimmed.dtype)])
    # normalize RMS
    def rms(x): return np.sqrt(np.mean(x**2) + 1e-12)
    cur_r = rms(y_trimmed)
    if cur_r > 0:
        y_trimmed = y_trimmed * (target_rms / cur_r)
    sf.write(dst_path, y_trimmed.astype(np.float32), sr, subtype='PCM_16')
    temp_files.add(dst_path)
    return dst_path


def verify_and_act(fixed_wav, matched_words):
    """
    Run verification on fixed_wav and act. Runs in background thread.
    We protect with verify_lock while opening/verifying to avoid read conflicts.
    """
    global next_record_allowed_at
    try:
        with verify_lock:
            score, prediction = verification.verify_files(REF_VOICE, fixed_wav)
        try:
            score_val = score.item()
        except Exception:
            score_val = float(score)
        print(f"📊 Similarity score: {score_val:.3f} for {matched_words}")
        if prediction == 1:
            print("✅ Authenticated — executing:", matched_words)
            # send mapped Arduino commands (dedupe)
            sent = set()
            for w in matched_words:
                cmd = signal_to_command.get(w)
                if cmd and cmd not in sent:
                    send_command_to_arduino(cmd)
                    sent.add(cmd)
        else:
            print("❌ Authentication failed for:", matched_words)
    except Exception as e:
        print("⚠️ Verification error:", e)
    finally:
        # set next allowed record time to avoid immediate retriggering
        next_record_allowed_at = time.time() + NEXT_RECORD_GAP_SECONDS
        # cleanup of files removed here as well (verify_and_act removes if present)
        try:
            if fixed_wav and os.path.exists(fixed_wav):
                os.remove(fixed_wav)
                temp_files.discard(fixed_wav)
        except Exception:
            pass
        try:
            # base temp file (raw) named from fixed_wav pattern
            # fixed_wav looks like "captured_fixed_<uid>_fixed.wav"
            base_temp = None
            if fixed_wav:
                base_temp = fixed_wav.replace(AUDIO_FIXED_BASE + "_", AUDIO_TEMP_BASE + "_").replace("_fixed.wav", ".wav")
            if base_temp and os.path.exists(base_temp):
                os.remove(base_temp)
                temp_files.discard(base_temp)
        except Exception:
            pass


# ===== AUDIO CALLBACK & WORKER =====
def audio_callback(indata, frames, time_info, status):
    """RawInputStream callback. indata is bytes-like (int16)."""
    if status:
        print("⚠️ Input status:", status)
    audio_q.put(bytes(indata))


def now_s():
    return time.time()


def should_trigger(word):
    """Return True if allowed by cooldown, and update last_trigger_time."""
    t = now_s()
    with trigger_lock:
        last = last_trigger_time.get(word, 0)
        if t - last < TRIGGER_COOLDOWN:
            return False
        last_trigger_time[word] = t
        return True


def consume_and_handle():
    """
    Main loop feeding Vosk, handling wake -> continuous recording -> on-command cut/verify -> continue.
    Fixed to avoid duplicate triggers and file races and includes next-record gap and duration check.
    """
    global rolling_chunks, rolling_bytes, is_recording, recording_buffer, stop_all, next_record_allowed_at

    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    recognizer.SetWords(True)

    print("🔊 Worker started. Listening for wake word...")

    while not stop_all:
        try:
            chunk = audio_q.get(timeout=1)
        except queue.Empty:
            continue

        # maintain rolling pre-roll
        rolling_chunks.append(chunk)
        rolling_bytes += len(chunk)
        while rolling_bytes > max_rolling_bytes and rolling_chunks:
            removed = rolling_chunks.popleft()
            rolling_bytes -= len(removed)

        # feed recognizer
        if recognizer.AcceptWaveform(chunk):
            res = json.loads(recognizer.Result())
            text = res.get("text", "")
            if text:
                print("→ (final):", text)
            words = text.lower().split()
        else:
            pres = json.loads(recognizer.PartialResult())
            text = pres.get("partial", "")
            words = text.lower().split() if text else []

        # Wake: start continuous recording (include pre-roll) but respect gap
        if (not is_recording) and (WAKE_WORD in words):
            now = time.time()
            if now < next_record_allowed_at:
                # ignore wake because we're still in the gap period after a capture
                print(f"⏭️ Wake ignored due to NEXT_RECORD_GAP (wait {next_record_allowed_at - now:.2f}s more).")
            else:
                pre_bytes = b"".join(rolling_chunks) if rolling_chunks else b""
                is_recording = True
                recording_buffer = bytearray(pre_bytes)
                print("🔔 Wake detected — continuous recording STARTED (includes pre-roll).")

        # If recording, append chunk and check for command/end
        if is_recording:
            recording_buffer.extend(chunk)

            # immediate detection of command words (partial or final)
            matched = [w for w in words if w in signal_to_command]
            if matched:
                # dedupe matched words
                unique_matched = list(dict.fromkeys(matched))
                # check cooldown for all words; if all are blocked, skip
                allowed_words = [w for w in unique_matched if should_trigger(w)]
                if not allowed_words:
                    # None allowed by cooldown — skip repeated trigger
                    pass
                else:
                    # Optionally add a tiny post-buffer
                    if POST_BUFFER_SECONDS > 0:
                        time.sleep(POST_BUFFER_SECONDS)

                    # We end the current recording at this point and verify it.
                    print(f"⚡ Command word(s) detected: {allowed_words} — cutting buffer and verifying.")
                    captured = bytes(recording_buffer)
                    # Clear buffer and continue recording immediately (so next command can be captured)
                    recording_buffer = bytearray()

                    # compute duration of captured (seconds)
                    captured_dur = len(captured) / (2 * SAMPLE_RATE)
                    if captured_dur < MIN_ACCEPT_SECONDS:
                        # skip saving/verification, enforce gap before next recording
                        print(f"⏸️ Captured duration {captured_dur:.3f}s < {MIN_ACCEPT_SECONDS}s — skipping verification.")
                        next_record_allowed_at = time.time() + NEXT_RECORD_GAP_SECONDS
                        continue

                    # create unique temp filenames
                    uid = uuid.uuid4().hex
                    temp_raw = f"{AUDIO_TEMP_BASE}_{uid}.wav"
                    temp_fixed = f"{AUDIO_FIXED_BASE}_{uid}_fixed.wav"

                    try:
                        write_wav_from_bytes(temp_raw, captured, SAMPLE_RATE)
                        # fix to unique fixed file
                        fix_audio_format(temp_raw, temp_fixed, target_sr=SAMPLE_RATE, min_dur=MIN_VERIFY_SECONDS,
                                         trim_silence=True, top_db=TRIM_TOP_DB, target_rms=TARGET_RMS)
                        print(f"💾 Captured audio saved -> {temp_fixed} (verifying...)")
                        # perform verification in background thread (it will set next_record_allowed_at on completion)
                        threading.Thread(target=verify_and_act, args=(temp_fixed, allowed_words), daemon=True).start()
                    except Exception as e:
                        print("⚠️ Error preparing captured audio:", e)
                        # ensure we still enforce a small gap
                        next_record_allowed_at = time.time() + NEXT_RECORD_GAP_SECONDS

            # end word stops continuous recording until next wake
            if END_WORD in words:
                print("🛑 End word detected — stopping continuous recording until next wake.")
                is_recording = False
                recording_buffer = bytearray()
                rolling_chunks.clear()
                rolling_bytes = 0
                continue

    print("Worker exiting.")


# ===== MAIN =====
def main():
    global stop_all
    if not os.path.exists(REF_VOICE):
        print(f"⚠️ Reference file '{REF_VOICE}' not found. Please create a good-quality refVoice.wav (3s+, 16kHz mono).")

    worker = threading.Thread(target=consume_and_handle if 'consume_and_handle' in globals() else consume_and_handle, daemon=True)
    worker.start()

    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000, dtype='int16',
                               channels=CHANNELS, callback=audio_callback):
            print("📡 Microphone open. Say wake word ('alexa') to start continuous recording.")
            print("Speak a command (e.g., 'left') — it will be cut & verified immediately.")
            print("Say 'go' to stop continuous recording. Press Ctrl-C to exit.")
            while True:
                time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user.")
    except Exception as e:
        print("🔴 Microphone error:", e)
    finally:
        # signal worker to stop and wait a short moment
        stop_all = True
        time.sleep(0.5)
        # close serial
        if ser and ser.is_open:
            ser.close()
            print("🔌 Serial closed.")
        # cleanup any remaining temp files produced during this run
        if temp_files:
            print("🧹 Cleaning up temporary files...")
            for p in list(temp_files):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            print("🧹 Cleanup done.")
        print("Bye.")

if __name__ == "__main__":
    main()
