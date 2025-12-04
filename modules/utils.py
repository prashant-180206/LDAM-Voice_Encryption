"""
Utility functions module for voice-controlled system.

This module provides common utility functions used across the voice control
system including timing operations, command cooldown management, and general
helper functions. Centralizes shared functionality to avoid code duplication
and provide consistent behavior across modules.

Key responsibilities:
- Command cooldown and debouncing logic
- Timing utilities and timestamp management  
- Thread-safe state tracking for command triggers
- Helper functions for system-wide operations
"""

import time
import threading
from modules.config import TRIGGER_COOLDOWN

# Thread-safe tracking of last command trigger times
last_trigger_time = {}
trigger_lock = threading.Lock()


def get_current_timestamp():
    """
    Get current system timestamp in seconds.
    
    Provides consistent timestamp source across the application for timing
    operations, cooldown calculations, and event logging. Uses system time
    for high precision timing measurements.
    
    Returns:
        float: Current timestamp in seconds since epoch
    """
    return time.time()


def should_trigger_command(command_word):
    """
    Check if command should trigger based on cooldown period.
    
    Implements command debouncing to prevent rapid repeated triggers of the
    same command. Thread-safe operation ensures accurate cooldown tracking
    in multi-threaded environment. Updates last trigger time if allowed.
    
    Args:
        command_word (str): Command word to check for trigger eligibility
    
    Returns:
        bool: True if command should trigger, False if in cooldown period
    
    Thread Safety:
        Uses thread lock to ensure atomic read-modify-write operations
        on trigger time tracking dictionary.
    """
    current_time = get_current_timestamp()
    
    with trigger_lock:
        # Get last trigger time for this command (default to 0 if new)
        last_time = last_trigger_time.get(command_word, 0)
        
        # Check if enough time has passed since last trigger
        if current_time - last_time < TRIGGER_COOLDOWN:
            return False  # Still in cooldown period
        
        # Update last trigger time and allow command
        last_trigger_time[command_word] = current_time
        return True


def filter_allowed_commands(command_words):
    """
    Filter command list to only include those allowed by cooldown.
    
    Takes list of detected command words and returns only those that pass
    cooldown checking. Maintains original order of commands while filtering
    out those that are still in their cooldown period.
    
    Args:
        command_words (list): List of command words to filter
    
    Returns:
        list: Filtered list containing only commands allowed to trigger
    
    Examples:
        filter_allowed_commands(["left", "right", "left"]) 
        # -> ["left", "right"] (second "left" filtered by cooldown)
    """
    allowed_commands = []
    
    for command in command_words:
        if should_trigger_command(command):
            allowed_commands.append(command)
    
    return allowed_commands


def reset_command_cooldowns():
    """
    Reset all command cooldown timers.
    
    Clears all tracked trigger times, allowing immediate triggering of any
    command. Useful for system resets or when switching between different
    operational modes. Thread-safe operation.
    """
    with trigger_lock:
        last_trigger_time.clear()
    print("🔄 Command cooldowns reset")


def get_command_cooldown_status():
    """
    Get current cooldown status for all tracked commands.
    
    Returns dictionary showing remaining cooldown time for each command.
    Useful for debugging timing issues and monitoring system state.
    
    Returns:
        dict: Command names mapped to remaining cooldown seconds (0 if ready)
    """
    current_time = get_current_timestamp()
    status = {}
    
    with trigger_lock:
        for command, last_time in last_trigger_time.items():
            remaining = max(0, TRIGGER_COOLDOWN - (current_time - last_time))
            status[command] = remaining
    
    return status


def calculate_audio_duration_seconds(audio_bytes, sample_rate=16000, bytes_per_sample=2):
    """
    Calculate duration of audio data in seconds.
    
    Converts byte length to duration based on audio format parameters.
    Assumes standard 16-bit (2 bytes per sample) mono audio format.
    
    Args:
        audio_bytes (bytes): Raw audio data
        sample_rate (int): Audio sample rate in Hz
        bytes_per_sample (int): Bytes per audio sample (2 for 16-bit)
    
    Returns:
        float: Audio duration in seconds
    """
    num_samples = len(audio_bytes) // bytes_per_sample
    return num_samples / sample_rate


def format_duration(seconds):
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds (float): Duration in seconds
    
    Returns:
        str: Formatted duration string (e.g., "2.50s", "1m 30.25s")
    """
    if seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.2f}s"