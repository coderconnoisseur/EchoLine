# EchoLine - Real-Time Speech-to-Text Overlay

EchoLine is a real-time speech-to-text overlay application that displays live captions on your screen. It's perfect for accessibility, transcription, or any scenario where you need live captions.

## Features
- Real-time speech-to-text conversion
- Always-on-top overlay window
- Adjustable transparency
- Movable overlay position
- Scrollable text history

## Requirements
- Python 3.7 or higher
- Windows operating system
- Stereo Mix enabled in sound settings

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/coderconnoisseur/EchoLine.git
   cd EchoLine

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt

### Step 3: Enable Stereo Mix
1. Right-click the speaker icon in your system tray
2. Select "Sounds"
3. Go to the "Recording" tab
4. Right-click and enable "Show Disabled Devices"
5. Right-click "Stereo Mix" and select "Enable"
6. Set Stereo Mix as the default device

### Step 4: Download and Install Vosk Model
1. Download the model from: https://alphacephei.com/vosk/models
2. Choose vosk-model-small-en-us-0.15
3. Extract the model to: C:\Users\<YourUsername>\.cache\vosk\

### Step 5: Run the Application
    ```bash
    python main.py

## Usage
- The overlay will appear at the bottom of your screen
- Speak into your microphone or play any audio to see live captions
- Click and drag to move the overlay window
- The window automatically scrolls to show the latest text
## Troubleshooting
### No Audio Captured
- Ensure Stereo Mix is enabled and set as default
- Check that your audio output is not muted
### Model Not Found
- Verify the Vosk model is in: C:\Users\<YourUsername>\.cache\vosk\vosk-model-small-en-us-0.15
## Contributing
Contributions are welcome! Please open an issue or submit a pull request