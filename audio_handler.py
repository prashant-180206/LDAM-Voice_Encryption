"""
Audio handling module for voice-controlled system.

This module manages all audio input/output operations including microphone
capture, audio buffering, file operations, and audio preprocessing. It handles
the continuous audio stream from the microphone and provides utilities for
audio file manipulation and format conversion.

Key responsibilities:
- Audio stream capture and callback handling
- Rolling audio buffer management for pre-roll functionality
- Audio file writing and format conversion
- Audio preprocessing (trimming, normalization, resampling)
"""

import queue
import sounddevice as sd
import soundfile as sf
import numpy as np
import librosa
import os
from collections import deque
from config import SAMPLE_RATE, PRE_ROLL_SECONDS, MIN_VERIFY_SECONDS, TRIM_TOP_DB, TARGET_RMS

# Global audio queue for inter-thread communication
audio_q = queue.Queue()

# Rolling buffer for pre-roll audio capture
# Maintains recent audio history before wake word detection
rolling_chunks = deque()
rolling_bytes = 0
max_rolling_bytes = int(SAMPLE_RATE * PRE_ROLL_SECONDS) * 2  # bytes (int16 = 2 bytes/sample)

# Set to track temporary files for cleanup
temp_files = set()


def audio_callback(indata, frames, time_info, status):
    """
    Real-time audio input callback for sounddevice RawInputStream.
    
    Called automatically by sounddevice when new audio data is available.
    Converts incoming audio data to bytes and queues it for processing.
    Reports any input status issues for debugging audio problems.
    
    Args:
        indata: Raw audio data as numpy array (int16 format)
        frames: Number of audio frames in this callback
        time_info: Timing information from audio system
        status: Audio input status flags
    """
    if status:
        print("⚠️ Audio input status:", status)
    # Convert numpy array to bytes and queue for processing
    audio_q.put(bytes(indata))


def maintain_rolling_buffer(chunk):
    """
    Maintain rolling audio buffer for pre-roll capture.
    
    Keeps a sliding window of recent audio data to include context before
    wake word detection. Automatically removes oldest chunks when buffer
    exceeds maximum size to prevent memory growth.
    
    Args:
        chunk (bytes): New audio chunk to add to rolling buffer
    """
    global rolling_chunks, rolling_bytes
    
    rolling_chunks.append(chunk)
    rolling_bytes += len(chunk)
    
    # Remove oldest chunks if buffer exceeds maximum size
    while rolling_bytes > max_rolling_bytes and rolling_chunks:
        removed = rolling_chunks.popleft()
        rolling_bytes -= len(removed)


def write_wav_from_bytes(path, bytes_data, samplerate=SAMPLE_RATE):
    """
    Write raw audio bytes to WAV file with proper formatting.
    
    Converts byte array to numpy int16 array and saves as standard WAV file.
    Registers file for cleanup tracking to prevent temporary file accumulation.
    
    Args:
        path (str): Output file path for WAV file
        bytes_data (bytes): Raw audio data in int16 format
        samplerate (int): Audio sample rate for WAV header
    """
    # Convert bytes to numpy array and write WAV file
    arr = np.frombuffer(bytes_data, dtype=np.int16)
    sf.write(path, arr, samplerate, subtype='PCM_16')
    temp_files.add(path)


def fix_audio_format(src_path, dst_path, target_sr=SAMPLE_RATE, min_dur=MIN_VERIFY_SECONDS,
                     trim_silence=True, top_db=TRIM_TOP_DB, target_rms=TARGET_RMS):
    """
    Normalize and process audio file for speaker verification.
    
    Performs comprehensive audio preprocessing including resampling,
    silence trimming, duration padding, and RMS normalization.
    Ensures consistent audio format for reliable speaker verification.
    
    Args:
        src_path (str): Source audio file path
        dst_path (str): Destination processed audio file path
        target_sr (int): Target sample rate
        min_dur (float): Minimum duration in seconds (pads with silence)
        trim_silence (bool): Whether to trim leading/trailing silence
        top_db (float): Silence threshold for trimming
        target_rms (float): Target RMS level for normalization
    
    Returns:
        str: Path to processed audio file
    
    Raises:
        FileNotFoundError: If source file doesn't exist
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(src_path)
    
    # Load and resample audio
    y, sr = librosa.load(src_path, sr=None, mono=True)
    if sr != target_sr:
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
        sr = target_sr
    
    # Trim silence if requested
    if trim_silence:
        y_trimmed, _ = librosa.effects.trim(y, top_db=top_db)
    else:
        y_trimmed = y
    
    # Pad to minimum duration if necessary
    cur_dur = len(y_trimmed) / sr
    if cur_dur < min_dur:
        need = int((min_dur - cur_dur) * sr)
        left = need // 2
        right = need - left
        y_trimmed = np.concatenate([
            np.zeros(left, dtype=y_trimmed.dtype),
            y_trimmed,
            np.zeros(right, dtype=y_trimmed.dtype)
        ])
    
    # Normalize RMS level
    def rms(x):
        return np.sqrt(np.mean(x**2) + 1e-12)
    
    cur_r = rms(y_trimmed)
    if cur_r > 0:
        y_trimmed = y_trimmed * (target_rms / cur_r)
    
    # Write processed audio file
    sf.write(dst_path, y_trimmed.astype(np.float32), sr, subtype='PCM_16')
    temp_files.add(dst_path)
    return dst_path


def cleanup_temp_files():
    """
    Clean up all temporary audio files created during session.
    
    Removes all files tracked in temp_files set and clears the tracking set.
    Safe cleanup that handles file access errors gracefully.
    Used during application shutdown to prevent disk space accumulation.
    """
    if temp_files:
        print("🧹 Cleaning up temporary audio files...")
        for file_path in list(temp_files):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass  # Ignore cleanup errors
        temp_files.clear()
        print("🧹 Audio file cleanup completed.")