"""
Modular Voice-Controlled Arduino System - Main Entry Point

This is the main entry point for the modular voice-controlled Arduino system.
The original monolithic code has been refactored into separate modules for
better maintainability, readability, and testability. Each module handles
a specific aspect of the voice control system.

Architecture Overview:
- config.py: Configuration parameters and constants
- audio_handler.py: Audio input/output and processing
- arduino_comm.py: Serial communication with Arduino
- speech_recognition.py: Voice-to-text conversion
- speaker_verification.py: Biometric voice authentication  
- utils.py: Common utility functions
- voice_controller.py: Main system orchestrator

Usage:
    python main.py
    
The system will initialize all components and start listening for voice commands.
Say the wake word to begin, speak commands, and use the end word to stop listening.
"""

from modules.voice_controller import run_voice_control_system

def main():
    """
    Main entry point for the modular voice control system.
    
    This function serves as the primary entry point that delegates to the
    modular voice controller system. The original monolithic implementation
    has been completely refactored into separate, maintainable modules.
    
    The new modular architecture provides:
    - Better code organization and maintainability
    - Easier testing and debugging of individual components
    - Improved reusability of system components
    - Cleaner separation of concerns
    - Enhanced documentation and code clarity
    
    All functionality from the original implementation is preserved while
    providing a much more maintainable and extensible codebase.
    """
    run_voice_control_system()


if __name__ == "__main__":
    main()
