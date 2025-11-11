# LDAM Voice Encryption Project 🎙️🔒

A voice-controlled authentication system that combines speaker verification with Arduino hardware control. This project uses machine learning for voice recognition and speaker authentication to control LED outputs on an Arduino board.

## 🔥 Features

- **Speaker Verification**: Uses SpeechBrain's ECAPA-VOXCELEB model for biometric voice authentication
- **Voice Command Recognition**: Converts speech to text using Google Speech Recognition API
- **Arduino Integration**: Controls LEDs on Arduino pins based on authenticated voice commands
- **Real-time Processing**: Continuous voice monitoring with 3-second recording intervals
- **Security**: Only executes commands when the speaker is authenticated

## 🛠️ System Requirements

- **Operating System**: Windows 10/11 (can be adapted for Linux/macOS)
- **Python**: 3.8 or higher
- **Hardware**: 
  - Arduino Uno/Nano (or compatible board)
  - LEDs and resistors (220Ω recommended)
  - Breadboard and jumper wires
  - Microphone (built-in or external)
  - USB cable for Arduino connection

## 📦 Installation Guide

### Step 1: Clone the Repository

```bash
git clone https://github.com/prashant-180206/LDAM-Voice_Encryption.git
cd LDAM-Voice_Encryption
```

### Step 2: Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv voiceenv

# Activate virtual environment
# On Windows:
voiceenv\Scripts\activate
# On Linux/macOS:
# source voiceenv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# If you encounter any issues, install packages individually:
pip install speechbrain torch torchaudio sounddevice soundfile SpeechRecognition pyserial
```

### Step 4: Arduino Setup

#### Hardware Wiring:
Connect LEDs to the following Arduino pins:
- Pin 2: "on" command LED
- Pin 3: "off"/"of" command LED  
- Pin 4: "turn" command LED
- Pin 5: "stop" command LED
- Pin 6: "left" command LED
- Pin 7: "right" command LED
- Pin 8: "forward" command LED
- Pin 9: "backward" command LED

**Wiring Diagram:**
```
Arduino Pin → 220Ω Resistor → LED Anode(+) → LED Cathode(-) → GND
```

#### Arduino Code Upload:
1. Open Arduino IDE
2. Load `voice_control/voice_control.ino`
3. Select your board type (Tools → Board)
4. Select the correct COM port (Tools → Port)
5. Upload the sketch to your Arduino

### Step 5: Configure Serial Port

1. Find your Arduino's COM port:
   - Windows: Check Device Manager → Ports (COM & LPT)
   - Linux: Usually `/dev/ttyUSB0` or `/dev/ttyACM0`
   - macOS: Usually `/dev/cu.usbmodem*`

2. Update the port in `main.py`:
```python
arduino_port = 'COM5'  # Change this to your actual port
```

### Step 6: Create Reference Voice Sample

1. Record your reference voice sample and save it as `refVoice.wav` in the project root
2. Ensure the sample is clear and at least 2-3 seconds long
3. The system will compare all future recordings against this reference

## 🚀 Usage Instructions

### Running the Application

1. **Ensure Arduino is connected** and the sketch is uploaded
2. **Activate your virtual environment**:
```bash
voiceenv\Scripts\activate
```
3. **Run the main application**:
```bash
python main.py
```

### Voice Commands

The system recognizes the following voice commands (only when speaker is authenticated):

| Command | Arduino Pin | Action |
|---------|-------------|---------|
| "on" | Pin 2 | Blink LED |
| "off" or "of" | Pin 3 | Blink LED |
| "turn" | Pin 4 | Blink LED |
| "stop" | Pin 5 | Blink LED |
| "left" | Pin 6 | Blink LED |
| "right" | Pin 7 | Blink LED |
| "forward" | Pin 8 | Blink LED |
| "backward" | Pin 9 | Blink LED |
| "finish" | - | Terminate program |

### Application Flow

1. **Recording**: The application records 3 seconds of audio
2. **Transcription**: Converts speech to text using Google Speech Recognition
3. **Authentication**: Compares voice with reference sample using speaker verification
4. **Command Execution**: If authenticated, executes the voice command
5. **Repeat**: Continues until "finish" command or Ctrl+C

## ⚙️ Configuration Options

### Adjusting Recording Settings
In `main.py`, modify these parameters:
```python
def record_audio(filename="voice.wav", duration=3, fs=16000):
    # duration: Recording length in seconds
    # fs: Sample rate (16kHz recommended)
```

### Voice Command Mapping
Modify the `signal_to_pin` dictionary to add/change commands:
```python
signal_to_pin = {
    "your_command": pin_number,
    # Add more commands here
}
```

### Authentication Sensitivity
The speaker verification threshold can be adjusted by modifying the model's behavior in the verification step.

## 🔧 Troubleshooting

### Common Issues

**1. Arduino Not Detected:**
```
⚠️ Arduino not found. Running without LED control
```
- Check if Arduino is properly connected
- Verify the correct COM port in `main.py`
- Ensure Arduino drivers are installed

**2. Audio Recording Issues:**
- Check microphone permissions
- Ensure microphone is working in other applications
- Try adjusting the recording duration

**3. Speech Recognition Errors:**
- Ensure internet connection (Google Speech API required)
- Speak clearly and at moderate pace
- Reduce background noise

**4. Speaker Verification Fails:**
- Ensure `refVoice.wav` exists and is clear
- Record reference sample in similar conditions
- Speak in the same tone/volume as reference

**5. Package Installation Issues:**
```bash
# If torch installation fails, try:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# If sounddevice fails on Linux:
sudo apt-get install portaudio19-dev python3-pyaudio

# If serial issues on Linux:
sudo chmod 666 /dev/ttyUSB0  # Replace with your port
```

## 📁 Project Structure

```
LDAM-Voice_Encryption/
├── main.py                 # Main application script
├── requirements.txt        # Python dependencies
├── refVoice.wav           # Reference voice sample (you create this)
├── voice_control/
│   └── voice_control.ino  # Arduino sketch
├── voiceenv/              # Virtual environment
├── pretrained_models/     # SpeechBrain model cache
└── README.md             # This file
```

## 🔒 Security Considerations

- The reference voice sample (`refVoice.wav`) should be kept secure
- Consider implementing additional authentication layers for sensitive applications
- Voice samples are processed locally, but transcription uses Google's API
- Arduino commands are sent via serial communication (unencrypted)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and commit: `git commit -m 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## 📝 Dependencies

### Python Packages:
- `speechbrain`: Speaker recognition and verification
- `torch` & `torchaudio`: Deep learning framework
- `sounddevice` & `soundfile`: Audio recording and processing
- `SpeechRecognition`: Speech-to-text conversion
- `pyserial`: Arduino communication
- `numpy`, `scipy`: Scientific computing

### Hardware:
- Arduino board (Uno/Nano recommended)
- LEDs and current-limiting resistors
- Microphone (built-in or external)

## 📄 License

This project is open-source. Please check the repository for license details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Open an issue on GitHub
3. Ensure you've followed all setup steps correctly

---

**Made with ❤️ for voice-controlled automation and biometric security**