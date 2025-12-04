"""
Configuration module for voice-controlled Arduino system.

This module centralizes all configuration parameters including audio settings,
file paths, device communication parameters, and command mappings. Having all
configurations in one place makes the system easier to maintain and customize.

Key configuration categories:
- Audio recording parameters (sample rate, channels, buffer sizes)
- Model and file paths (Vosk model, reference voice file)
- Arduino communication settings (port, baud rate)
- Timing parameters (cooldowns, gaps, minimum durations)
- Command word to Arduino action mappings
"""

# Audio recording configuration
# Standard 16kHz mono audio for voice recognition compatibility
SAMPLE_RATE = 16000
CHANNELS = 1

# Model and file paths
# Path to downloaded Vosk speech recognition model directory
VOSK_MODEL_PATH = "model/model"
# Reference voice file for speaker verification (user's enrolled voice)
REF_VOICE = "refVoice.wav"

# Temporary file naming patterns
# Base names for generated temporary audio files during processing
AUDIO_TEMP_BASE = "captured_command"
AUDIO_FIXED_BASE = "captured_fixed"

# Arduino communication settings
# Serial port and baud rate for Arduino/Bluetooth module communication
ARDUINO_PORT = "COM5"
ARDUINO_BAUD = 9600

# Audio timing parameters (all in seconds)
# Include some audio before wake word detection to capture complete words
PRE_ROLL_SECONDS = 0.5
# Minimum duration for speaker verification (shorter clips are padded)
MIN_VERIFY_SECONDS = 1.8
# Minimum duration to accept any captured audio (shorter clips discarded)
MIN_ACCEPT_SECONDS = 1.5
# Optional buffer after command detection to capture trailing phonemes
POST_BUFFER_SECONDS = 0.0
# Gap before allowing new recording after command execution
NEXT_RECORD_GAP_SECONDS = 0.5
# Cooldown period per command to prevent repeated triggers
TRIGGER_COOLDOWN = 1.0

# Audio processing parameters
# Silence trimming threshold in decibels
TRIM_TOP_DB = 25
# Target RMS level for audio normalization
TARGET_RMS = 0.1

# Command word mappings
# Maps recognized speech to Arduino command strings
signal_to_command = {
    "on": "forward",      # Power on or move forward
    "off": "stop",        # Power off or stop movement
    "of": "stop",         # Alternative pronunciation of "off"
    "turn": "forward",    # Generic turn command mapped to forward
    "stop": "stop",       # Explicit stop command
    "left": "left",       # Turn left
    "right": "right",     # Turn right
    "forward": "forward", # Move forward
    "backward": "backward", # Move backward
}

# Wake and control words
# Word to activate continuous listening mode
WAKE_WORD = "alexa"
# Word to deactivate continuous listening mode
END_WORD = "go"