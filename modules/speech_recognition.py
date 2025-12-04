"""
Speech recognition module for voice-controlled system.

This module handles all speech recognition operations using the Vosk speech-to-text
engine. It manages the recognition model, processes audio streams, and extracts
spoken commands from audio input. Supports both final and partial recognition
results for responsive voice command detection.

Key responsibilities:
- Vosk model initialization and management  
- Real-time audio stream processing for speech recognition
- Command word extraction and filtering from recognized text
- Wake word and end word detection for system state control
"""

import json
import os
import sys
from vosk import Model, KaldiRecognizer
from modules.config import VOSK_MODEL_PATH, SAMPLE_RATE, WAKE_WORD, END_WORD, signal_to_command

# Global speech recognition objects
model = None
recognizer = None


def initialize_speech_recognition():
    """
    Initialize Vosk speech recognition model and recognizer.
    
    Loads the Vosk speech recognition model from configured path and creates
    a recognizer instance for processing audio streams. Validates model
    availability and exits gracefully if model files are missing.
    
    Returns:
        bool: True if initialization successful, False if failed
    
    Global Variables Modified:
        model: Vosk Model instance for speech recognition
        recognizer: KaldiRecognizer instance for audio processing
    """
    global model, recognizer
    
    # Validate model path exists
    if not os.path.exists(VOSK_MODEL_PATH):
        print(f"❌ Vosk model not found at '{VOSK_MODEL_PATH}'")
        print("📥 Please download Vosk model and update VOSK_MODEL_PATH in config.py")
        return False
    
    try:
        # Initialize Vosk model and recognizer
        model = Model(VOSK_MODEL_PATH)
        recognizer = KaldiRecognizer(model, SAMPLE_RATE)
        recognizer.SetWords(True)  # Enable word-level timing information
        
        print(f"✅ Speech recognition initialized with model: {VOSK_MODEL_PATH}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize speech recognition: {e}")
        return False


def process_audio_chunk(chunk):
    """
    Process audio chunk through speech recognition engine.
    
    Feeds audio data to Vosk recognizer and returns both final and partial
    recognition results. Handles JSON parsing of recognition results and
    extracts spoken text for further command processing.
    
    Args:
        chunk (bytes): Raw audio data chunk in int16 format
    
    Returns:
        tuple: (final_text, partial_text) where:
            - final_text: Confirmed recognition result (empty string if none)
            - partial_text: In-progress recognition result (empty string if none)
    
    Raises:
        RuntimeError: If speech recognition not initialized
    """
    if recognizer is None:
        raise RuntimeError("Speech recognition not initialized")
    
    # Process audio chunk and get recognition results
    if recognizer.AcceptWaveform(chunk):
        # Final recognition result available
        res = json.loads(recognizer.Result())
        final_text = res.get("text", "").lower()
        partial_text = ""
    else:
        # Only partial recognition available
        pres = json.loads(recognizer.PartialResult()) 
        final_text = ""
        partial_text = pres.get("partial", "").lower()
    
    return final_text, partial_text


def extract_command_words(text):
    """
    Extract valid command words from recognized speech text.
    
    Filters recognized text to find words that match configured command
    vocabulary. Removes duplicates while preserving order of first occurrence.
    Only returns words that have corresponding Arduino actions defined.
    
    Args:
        text (str): Recognized speech text (should be lowercase)
    
    Returns:
        list: List of unique command words found in text, in order of appearance
    
    Examples:
        extract_command_words("turn left now") -> ["left"]
        extract_command_words("go forward and stop") -> ["forward", "stop"]
    """
    if not text:
        return []
    
    # Split text into words and filter for command vocabulary
    words = text.split()
    matched_words = [word for word in words if word in signal_to_command]
    
    # Remove duplicates while preserving order
    unique_commands = list(dict.fromkeys(matched_words))
    
    return unique_commands


def contains_wake_word(text):
    """
    Check if recognized text contains the wake word.
    
    Args:
        text (str): Recognized speech text to check
    
    Returns:
        bool: True if wake word found in text, False otherwise
    """
    return WAKE_WORD in text.split() if text else False


def contains_end_word(text):
    """
    Check if recognized text contains the end word.
    
    Args:
        text (str): Recognized speech text to check
    
    Returns:
        bool: True if end word found in text, False otherwise
    """
    return END_WORD in text.split() if text else False