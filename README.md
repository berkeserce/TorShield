# TorShield

TorShield is a secure and user-friendly desktop application that routes your internet traffic through the Tor network, providing enhanced privacy and anonymity.

## Features

- Modern matte black UI design
- System tray integration
- Real-time connection status monitoring
- Download/Upload speed display
- Connection history tracking
- Auto-reconnect capability
- System proxy integration
- Secure Tor network routing

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/torshield.git
cd torshield
```

2. Install required packages
```bash
pip install -r requirements.txt
```

3. Make sure Tor binaries are in the `tor` folder

## Usage

1. Run the application:
```bash
python src/main.py
```

2. Click "Connect" to start routing traffic through Tor
3. The system tray icon will show connection status
4. Access settings through the "Settings" button

## Settings

- Auto-connect on startup
- Minimize to system tray
- Save connection history
- Show speed information
- Auto-reconnect timer
- System proxy configuration

## Security Features

- Secure socket handling
- Tor connection verification
- System proxy integration
- Port security checks
- Clean session management
