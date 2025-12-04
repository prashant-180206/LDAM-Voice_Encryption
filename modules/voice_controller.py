"""
Voice control system orchestrator module.

This module coordinates all components of the voice-controlled Arduino system
including audio processing, speech recognition, speaker verification, and
command execution. Manages the main application lifecycle, state transitions,
and inter-module communication for seamless voice control operation.

Key responsibilities:
- System initialization and component coordination
- Main audio processing loop with state management
- Wake word detection and continuous recording control
- Command processing pipeline orchestration
- Graceful system shutdown and resource cleanup
"""

import threading
import time
import sounddevice as sd
from collections import deque

# Import all required modules
from modules.config import SAMPLE_RATE, CHANNELS, WAKE_WORD, END_WORD, POST_BUFFER_SECONDS
from modules.audio_handler import audio_callback, maintain_rolling_buffer, rolling_chunks, audio_q
from modules.arduino_comm import initialize_serial_connection, close_serial_connection
from modules.speech_recognition import (initialize_speech_recognition, process_audio_chunk, 
                               extract_command_words, contains_wake_word, contains_end_word)
from modules.speaker_verification import (initialize_speaker_verification, verify_reference_voice,
                                 verify_and_execute_commands, can_record_now)
from modules.utils import filter_allowed_commands, calculate_audio_duration_seconds

# Global system state variables
is_recording = False
recording_buffer = bytearray()
stop_all = False


def initialize_system():
    """
    Initialize all system components and validate readiness.
    
    Performs sequential initialization of all required components including
    Arduino communication, speech recognition, and speaker verification.
    Validates system readiness before starting main operation loop.
    
    Returns:
        bool: True if all components initialized successfully, False otherwise
    """
    print("🚀 Initializing voice control system...")
    
    # Initialize Arduino communication
    arduino_ready = initialize_serial_connection()
    
    # Initialize speech recognition engine
    speech_ready = initialize_speech_recognition()
    if not speech_ready:
        return False
    
    # Initialize speaker verification system
    verification_ready = initialize_speaker_verification()
    if not verification_ready:
        return False
    
    # Validate reference voice availability
    ref_voice_ready = verify_reference_voice()
    if not ref_voice_ready:
        print("⚠️ System will run without speaker verification")
    
    print("✅ System initialization completed")
    return True


def process_speech_and_commands(text_final, text_partial):
    """
    Process recognized speech for wake words and commands.
    
    Handles state transitions based on wake word and end word detection.
    Processes command words during continuous recording mode and initiates
    verification and execution pipeline for detected commands.
    
    Args:
        text_final (str): Final recognition result from speech engine
        text_partial (str): Partial recognition result from speech engine
    
    Global Variables Modified:
        is_recording: Recording state flag
        recording_buffer: Audio buffer for continuous recording
    """
    global is_recording, recording_buffer
    
    # Combine final and partial text for comprehensive analysis
    combined_text = f"{text_final} {text_partial}".strip()
    
    # Wake word detection - start continuous recording
    if not is_recording and contains_wake_word(combined_text):
        if can_record_now():
            start_continuous_recording()
        else:
            print("⏭️ Wake word detected but in cooldown period")
    
    # Command processing during recording
    if is_recording:
        command_words = extract_command_words(combined_text)
        if command_words:
            process_detected_commands(command_words)
        
        # End word detection - stop continuous recording
        if contains_end_word(combined_text):
            stop_continuous_recording()


def start_continuous_recording():
    """
    Begin continuous audio recording with pre-roll inclusion.
    
    Transitions system to recording state and includes recent audio history
    from rolling buffer to capture complete wake word context. Initializes
    recording buffer with pre-roll audio for better command capture.
    
    Global Variables Modified:
        is_recording: Set to True
        recording_buffer: Initialized with pre-roll audio
    """
    global is_recording, recording_buffer
    
    # Include pre-roll audio from rolling buffer
    pre_roll_audio = b"".join(rolling_chunks) if rolling_chunks else b""
    is_recording = True
    recording_buffer = bytearray(pre_roll_audio)
    print("🔔 Wake word detected - continuous recording started with pre-roll")


def process_detected_commands(command_words):
    """
    Process detected command words through verification pipeline.
    
    Filters commands by cooldown restrictions, captures current recording
    buffer, and initiates background verification process. Continues recording
    immediately to enable rapid successive command processing.
    
    Args:
        command_words (list): List of detected command words
    
    Global Variables Modified:
        recording_buffer: Cleared and reinitialized for next command
    """
    global recording_buffer
    
    # Filter commands based on cooldown restrictions
    allowed_commands = filter_allowed_commands(command_words)
    if not allowed_commands:
        return  # All commands filtered by cooldown
    
    # Optional post-buffer for complete phoneme capture
    if POST_BUFFER_SECONDS > 0:
        time.sleep(POST_BUFFER_SECONDS)
    
    # Capture current recording for verification
    captured_audio = bytes(recording_buffer)
    audio_duration = calculate_audio_duration_seconds(captured_audio)
    
    print(f"⚡ Commands detected: {allowed_commands}")
    print(f"📊 Captured {audio_duration:.3f}s of audio for verification")
    
    # Start verification in background thread
    verification_thread = threading.Thread(
        target=verify_and_execute_commands,
        args=(captured_audio, allowed_commands),
        daemon=True
    )
    verification_thread.start()
    
    # Reset recording buffer for next command
    recording_buffer = bytearray()


def stop_continuous_recording():
    """
    Stop continuous recording and reset system state.
    
    Transitions system back to wake word listening mode and clears all
    recording buffers and audio history. Prepares system for next wake
    word detection cycle.
    
    Global Variables Modified:
        is_recording: Set to False
        recording_buffer: Cleared
        rolling_chunks: Cleared
    """
    global is_recording, recording_buffer
    
    is_recording = False
    recording_buffer = bytearray()
    rolling_chunks.clear()
    print("🛑 End word detected - continuous recording stopped")


def main_audio_processing_loop():
    """
    Main audio processing loop with speech recognition integration.
    
    Continuously processes audio chunks from input queue, maintains rolling
    buffer, feeds speech recognition engine, and orchestrates system state
    transitions. Runs in dedicated thread for non-blocking operation.
    """
    print("🎤 Audio processing loop started")
    
    while not stop_all:
        try:
            # Get audio chunk with timeout to allow clean shutdown
            chunk = audio_q.get(timeout=1)
        except:
            continue  # Timeout or queue empty
        
        # Maintain rolling buffer for pre-roll functionality
        maintain_rolling_buffer(chunk)
        
        # Add chunk to recording buffer if actively recording
        if is_recording:
            recording_buffer.extend(chunk)
        
        # Process chunk through speech recognition
        try:
            final_text, partial_text = process_audio_chunk(chunk)
            
            # Log recognition results
            if final_text:
                print(f"→ Final: {final_text}")
            if partial_text and not final_text:
                print(f"→ Partial: {partial_text}")
            
            # Process speech for commands and state changes
            process_speech_and_commands(final_text, partial_text)
            
        except Exception as e:
            print(f"⚠️ Speech processing error: {e}")
    
    print("🔚 Audio processing loop terminated")


def run_voice_control_system():
    """
    Main system entry point and lifecycle manager.
    
    Orchestrates complete system operation including initialization,
    audio stream setup, processing loop execution, and graceful shutdown.
    Handles user interruption and system errors with proper cleanup.
    """
    global stop_all
    
    # Initialize all system components
    if not initialize_system():
        print("❌ System initialization failed - exiting")
        return
    
    # Start audio processing in background thread
    processing_thread = threading.Thread(
        target=main_audio_processing_loop, 
        daemon=True
    )
    processing_thread.start()
    
    try:
        # Start real-time audio input stream
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=4000,
            dtype='int16',
            channels=CHANNELS,
            callback=audio_callback
        ):
            print("📡 Voice control system active")
            print(f"🔊 Say '{WAKE_WORD}' to start, command words to control, '{END_WORD}' to stop")
            print("⌨️ Press Ctrl+C to exit system")
            
            # Keep main thread alive
            while not stop_all:
                time.sleep(0.2)
                
    except KeyboardInterrupt:
        print("\n👋 System shutdown requested by user")
    except Exception as e:
        print(f"🔴 System error: {e}")
    finally:
        # Initiate graceful shutdown
        shutdown_system()


def shutdown_system():
    """
    Perform graceful system shutdown with resource cleanup.
    
    Signals all threads to stop, closes hardware connections, cleans up
    temporary files, and ensures proper resource deallocation. Safe to
    call multiple times during error conditions.
    """
    global stop_all
    
    print("🔄 Initiating system shutdown...")
    stop_all = True
    
    # Allow threads time to finish current operations
    time.sleep(0.5)
    
    # Close hardware connections
    close_serial_connection()
    
    # Clean up temporary files
    from modules.audio_handler import cleanup_temp_files
    cleanup_temp_files()
    
    print("✅ System shutdown completed successfully")


# Module entry point for direct execution
if __name__ == "__main__":
    run_voice_control_system()