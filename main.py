import warnings
warnings.filterwarnings("ignore")

import sounddevice as sd
import soundfile as sf
from speechbrain.inference.speaker import SpeakerRecognition
import speech_recognition as sr
import serial
import time

# Embedded signal-to-pin mapping (no external file needed if you define it here)
signal_to_pin = {
    "on": 2,
    "off": 3,
    "of": 3,
    "turn": 4,
    "stop": 5,
    "left": 6,
    "right": 7,
    "forward": 8,
    "backward": 9,
}

# Try to connect to Arduino (change 'COM3' to your port)
arduino_port = 'COM5'  # ← CHANGE THIS TO YOUR ARDUINO PORT (e.g., 'COM4', '/dev/ttyUSB0')
ser = None

try:
    ser = serial.Serial(arduino_port, 9600, timeout=1)
    time.sleep(2)  # Wait for Arduino to reset
    print("✅ Connected to Arduino on", arduino_port)
except serial.SerialException as e:
    print("⚠️ Arduino not found. Running without LED control:", e)
    print("Check if the port is correct or Arduino is connected.")
except Exception as e:
    print("⚠️ Serial error:", e)

def record_audio(filename="voice.wav", duration=3, fs=16000):
    print(f"\n🎙️ Recording {duration} seconds...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()
    sf.write(filename, recording, fs)
    print(f"💾 Saved {filename}")

def transcribe_audio(filename="voice.wav"):
    recognizer = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return "[Unintelligible]"
    except sr.RequestError as e:
        return f"[API Error: {e}]"

def send_led_signal(pin):
    if ser and ser.is_open:
        ser.write(f"{pin}\\n".encode())  # Send pin number
        print(f"💡 LED on pin {pin} triggered.")
    else:
        print(f"🔌 LED {pin}: Would blink (Arduino not connected).")

def check_signals(text):
    words = text.lower().split()
    triggered = False
    for word in words:
        if word in signal_to_pin:
            pin = signal_to_pin[word]
            send_led_signal(pin)
            triggered = True
        if word == "finish":
            print("🛑 Signal: stop")
            print("⏹️ Terminating program.")
            return True
    return False

def main():
    # Load speaker verification model
    verification = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
    )

    print("🔊 Listening for voice commands (3-second intervals)...\n")
    try:
        while True:
            record_audio()
            text = transcribe_audio()
            print(f"📝 Transcription: {text}")

            # Perform speaker verification
            try:
                score, prediction = verification.verify_files("refVoice.wav", "voice.wav")
                print(f"📊 Similarity score: {score.item():.3f}")  # ← Use .item()
                if prediction == 1:
                    print("✅ Authentication: Speaker matched")
                    if check_signals(text):
                        break
                else:
                    print("❌ Authentication: Speaker NOT matched")
                    if "stop" in text.lower().split():
                        print("🛑 Stop detected. Terminating.")
                        break
            except Exception as e:
                print(f"⚠️  Verification error: {e}")
                continue


    except KeyboardInterrupt:
        print("\n👋 Program interrupted by user.")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("🔌 Serial connection closed.")

if __name__ == "__main__":
    main()
