# record_ref.py  - records and overwrites refVoice.wav
import sounddevice as sd
import soundfile as sf
import sys

DURATION = 6
FS = 16000
OUT = "refVoice.wav"

print(f"Recording {DURATION}s → {OUT}")
data = sd.rec(int(DURATION * FS), samplerate=FS, channels=1, dtype="float32")
sd.wait()
sf.write(OUT, data, FS)
print("Done.")
