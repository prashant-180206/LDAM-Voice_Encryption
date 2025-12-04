"""
Arduino communication module for voice-controlled system.

This module handles all serial communication with Arduino devices including
connection management, command transmission, and error handling. It provides
a clean interface for sending movement commands to Arduino-based robots or
IoT devices via serial or Bluetooth connections.

Key responsibilities:
- Serial port connection initialization and management
- Command string transmission to Arduino
- Connection error handling and recovery
- Graceful connection cleanup and resource management
"""

import serial
import time
from modules.config import ARDUINO_PORT, ARDUINO_BAUD

# Global serial connection object
ser = None


def initialize_serial_connection():
    """
    Initialize serial connection to Arduino/Bluetooth module.
    
    Attempts to establish serial communication on configured port and baud rate.
    Includes startup delay to allow Arduino to initialize properly after connection.
    Handles connection errors gracefully with fallback to simulation mode.
    
    Returns:
        bool: True if connection successful, False if failed
    
    Global Variables Modified:
        ser: Serial connection object set to active connection or None
    """
    global ser
    
    try:
        # Establish serial connection with configured parameters
        ser = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
        # Allow Arduino time to reset and initialize after connection
        time.sleep(2)
        print(f"✅ Arduino connected successfully on {ARDUINO_PORT}")
        return True
        
    except Exception as e:
        print(f"⚠️ Failed to connect to Arduino: {e}")
        print(f"📝 Will run in simulation mode (commands logged only)")
        ser = None
        return False


def send_command_to_arduino(cmd_str):
    """
    Send ASCII command string to Arduino via serial connection.
    
    Transmits command with newline terminator for Arduino parsing.
    Handles both real hardware communication and simulation mode.
    Provides error handling for connection issues during transmission.
    
    Args:
        cmd_str (str): Command string to send (e.g., "forward", "left", "stop")
    
    Examples:
        send_command_to_arduino("forward")  # Move robot forward
        send_command_to_arduino("left")     # Turn robot left  
        send_command_to_arduino("stop")     # Stop robot movement
    """
    if ser and ser.is_open:
        try:
            # Send command with newline terminator for Arduino parsing
            ser.write((cmd_str + "\n").encode())
            print(f"📨 Command sent to Arduino: {cmd_str}")
            
        except Exception as e:
            print(f"⚠️ Serial transmission error: {e}")
            print(f"🔄 Check connection and try again")
    else:
        # Simulation mode when no hardware connection available
        print(f"🔌 (Simulation) Arduino command: {cmd_str}")


def close_serial_connection():
    """
    Safely close serial connection and release resources.
    
    Performs graceful shutdown of serial communication with proper resource
    cleanup. Safe to call multiple times or when connection already closed.
    Should be called during application shutdown to prevent resource leaks.
    
    Global Variables Modified:
        ser: Set to None after closing connection
    """
    global ser
    
    if ser and ser.is_open:
        try:
            ser.close()
            print("🔌 Arduino connection closed successfully")
        except Exception as e:
            print(f"⚠️ Error closing Arduino connection: {e}")
    
    ser = None


def is_connected():
    """
    Check if Arduino connection is active and ready for communication.
    
    Returns:
        bool: True if serial connection is open and ready, False otherwise
    
    Useful for conditional command sending and connection status checking
    before attempting communication operations.
    """
    return ser is not None and ser.is_open