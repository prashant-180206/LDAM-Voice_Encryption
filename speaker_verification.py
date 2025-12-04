"""
Speaker verification module for voice-controlled system.

This module handles biometric speaker verification using SpeechBrain ECAPA-TDNN
models. It compares captured voice commands against enrolled reference voice
to authenticate users before executing commands. Provides security layer to
prevent unauthorized voice command execution.

Key responsibilities:
- SpeechBrain speaker verification model initialization
- Reference voice enrollment and validation
- Real-time voice authentication against reference
- Thread-safe verification operations with file locking
"""

import os
import threading
import time
import uuid
from speechbrain.inference.speaker import SpeakerRecognition
from config import REF_VOICE, MIN_ACCEPT_SECONDS, NEXT_RECORD_GAP_SECONDS, AUDIO_TEMP_BASE, AUDIO_FIXED_BASE
from audio_handler import write_wav_from_bytes, fix_audio_format, temp_files
from arduino_comm import send_command_to_arduino
from config import signal_to_command

# Global verification model and thread safety
verification = None
verify_lock = threading.Lock()
next_record_allowed_at = 0.0


def initialize_speaker_verification():
    """
    Initialize SpeechBrain speaker verification model.
    
    Loads pre-trained ECAPA-TDNN model from SpeechBrain for speaker verification.
    This model compares voice embeddings to determine if two audio samples
    are from the same speaker. Handles model loading errors gracefully.
    
    Returns:
        bool: True if initialization successful, False if failed
    
    Global Variables Modified:
        verification: SpeechBrain SpeakerRecognition model instance
    """
    global verification
    
    try:
        # Load pre-trained ECAPA-TDNN speaker verification model
        verification = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
        )
        print("✅ Speaker verification model loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize speaker verification: {e}")
        print("📥 Check internet connection and SpeechBrain installation")
        return False


def verify_reference_voice():
    """
    Validate that reference voice file exists and is accessible.
    
    Checks for enrolled reference voice file required for speaker verification.
    Provides guidance for creating proper reference voice recordings if missing.
    
    Returns:
        bool: True if reference voice file exists, False otherwise
    """
    if not os.path.exists(REF_VOICE):
        print(f"⚠️ Reference voice file '{REF_VOICE}' not found")
        print("📝 Create a high-quality reference voice recording:")
        print("   - 3+ seconds of clear speech")
        print("   - 16kHz sample rate, mono channel") 
        print("   - Minimal background noise")
        return False
    
    print(f"✅ Reference voice file found: {REF_VOICE}")
    return True


def verify_and_execute_commands(captured_audio, matched_words):
    """
    Verify speaker identity and execute commands if authenticated.
    
    Processes captured audio through verification pipeline: creates temporary
    files, performs speaker verification against reference voice, and executes
    Arduino commands if authentication succeeds. Runs in background thread
    to avoid blocking main audio processing loop.
    
    Args:
        captured_audio (bytes): Raw audio data containing voice command
        matched_words (list): List of command words detected in audio
    
    Global Variables Modified:
        next_record_allowed_at: Timestamp when next recording is allowed
    
    Threading:
        Designed to run in background thread for non-blocking operation
    """
    global next_record_allowed_at
    
    try:
        # Check minimum duration requirement
        captured_dur = len(captured_audio) / (2 * 16000)  # bytes to seconds
        if captured_dur < MIN_ACCEPT_SECONDS:
            print(f"⏸️ Audio too short ({captured_dur:.3f}s) - skipping verification")
            next_record_allowed_at = time.time() + NEXT_RECORD_GAP_SECONDS
            return
        
        # Create unique temporary files for verification
        uid = uuid.uuid4().hex
        temp_raw = f"{AUDIO_TEMP_BASE}_{uid}.wav"
        temp_fixed = f"{AUDIO_FIXED_BASE}_{uid}_fixed.wav"
        
        try:
            # Save captured audio and process for verification
            write_wav_from_bytes(temp_raw, captured_audio)
            fix_audio_format(temp_raw, temp_fixed)
            print(f"💾 Audio processed for verification: {temp_fixed}")
            
            # Perform thread-safe speaker verification
            with verify_lock:
                score, prediction = verification.verify_files(REF_VOICE, temp_fixed)
            
            # Extract numerical score for logging
            try:
                score_val = score.item()
            except Exception:
                score_val = float(score)
            
            print(f"📊 Verification score: {score_val:.3f} for commands: {matched_words}")
            
            # Execute commands if authentication successful
            if prediction == 1:
                print("✅ Speaker authenticated - executing commands")
                execute_unique_commands(matched_words)
            else:
                print("❌ Speaker authentication failed - commands rejected")
                
        except Exception as e:
            print(f"⚠️ Verification processing error: {e}")
            
        finally:
            # Clean up temporary files and set next recording delay
            cleanup_verification_files(temp_raw, temp_fixed)
            next_record_allowed_at = time.time() + NEXT_RECORD_GAP_SECONDS
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        next_record_allowed_at = time.time() + NEXT_RECORD_GAP_SECONDS


def execute_unique_commands(command_words):
    """
    Execute Arduino commands from verified voice input.
    
    Maps command words to Arduino actions and sends unique commands only.
    Prevents duplicate command transmission when multiple instances of
    same command word are detected in single audio capture.
    
    Args:
        command_words (list): List of command words to execute
    """
    executed_commands = set()
    
    for word in command_words:
        arduino_cmd = signal_to_command.get(word)
        if arduino_cmd and arduino_cmd not in executed_commands:
            send_command_to_arduino(arduino_cmd)
            executed_commands.add(arduino_cmd)


def cleanup_verification_files(temp_raw, temp_fixed):
    """
    Clean up temporary files created during verification process.
    
    Safely removes temporary audio files and updates global tracking.
    Handles file access errors gracefully to prevent cleanup failures
    from affecting system operation.
    
    Args:
        temp_raw (str): Path to raw temporary audio file
        temp_fixed (str): Path to processed temporary audio file  
    """
    for file_path in [temp_raw, temp_fixed]:
        if file_path:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    temp_files.discard(file_path)
            except Exception:
                pass  # Ignore cleanup errors


def can_record_now():
    """
    Check if new audio recording is allowed based on timing constraints.
    
    Returns:
        bool: True if recording allowed now, False if in cooldown period
    """
    return time.time() >= next_record_allowed_at