# TorShield

<p align="center">
  <img src="src/ui/logo.ico" alt="TorShield Logo" width="200"/>
</p>

TorShield is a powerful desktop application that provides a secure and user-friendly interface for connecting to the Tor network. It allows users to browse the internet anonymously while offering real-time connection statistics and advanced privacy controls.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Settings](#settings)
- [Security Features](#security-features)
- [Development](#development)
- [License](#license)
- [Disclaimer](#disclaimer)

## Features

### Core Functionality
- **One-Click Tor Connection**: Seamlessly connect and disconnect from the Tor network with a single button
- **IP Address Management**: Change your IP address on demand with a single click
- **Automatic IP Rotation**: Configure automatic IP address changes at specified intervals for enhanced anonymity
- **System Proxy Integration**: Automatic system proxy configuration for secure routing of all your traffic

### Connection Monitoring
- **Real-Time Status Display**: Monitor your Tor connection health in real-time with visual indicators
- **Traffic Statistics**: View live download and upload speeds to monitor your connection performance
- **Connection Timer**: Track how long you've been connected to the Tor network with a precise timer
- **IP Address Display**: See your current Tor exit node IP address to verify your anonymous identity

### User Interface
- **Modern Dark Theme**: Sleek matte black UI design that's easy on the eyes during extended sessions
- **System Tray Integration**: Run the application in the background with quick access from the system tray
- **Connection Notifications**: Receive alerts about connection status changes and IP rotations
- **Intuitive Controls**: User-friendly interface designed for all skill levels

### Advanced Features
- **Connection History**: Save and review your previous connections with timestamps and duration
- **Exit Node Selection**: Choose specific countries for your Tor exit nodes for targeted browsing
- **Display Preferences**: Customize what information is shown in the interface
- **Notification Settings**: Control when and how you receive connection alerts

## Requirements

- Windows 10/11
- Python 3.9+
- PySide6
- Tor binaries (included in the `/tor` folder)
- Administrative privileges (for system proxy configuration)

## Installation

### From Source

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/torshield.git
   cd torshield
   ```

2. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Tor binaries**
   - Make sure the `tor` folder contains all necessary Tor binary files
   - These are used to create and manage the Tor connection

4. **Run the application**
   ```bash
   python src/main.py
   ```

### Using Pre-built Release

1. **Download the latest release**
   - Visit the [Releases](https://github.com/berkeserce/torshield/releases) page
   - Download the latest `.zip` or `.exe` package

2. **Extract the archive**
   - Extract to a directory of your choice
   - Ensure you maintain the folder structure

3. **Run the application**
   - Execute `TorShield.exe` to start the application
   - Administrative privileges may be required

## Usage Guide

### Getting Started

1. **Launch TorShield**
   - Double-click the application icon or run from the command line

2. **Connect to Tor**
   - Click the "Connect" button to establish a Tor connection
   - The application will:
     - Terminate any existing Tor processes
     - Configure system proxy settings
     - Start the Tor service
     - Verify the connection is secure

3. **Monitor Your Connection**
   - Once connected, the status indicator will turn green
   - Your new IP address will be displayed
   - Connection timer will start counting
   - Traffic statistics will begin updating in real-time

### Managing Your Identity

- **Manual IP Change**
  - Click the "Change IP" button to get a new Tor circuit and IP address
  - The application will request a new circuit from Tor and verify the IP has changed

- **Automatic IP Rotation**
  - Enable automatic IP changing in settings
  - Set your preferred interval (e.g., every 15 minutes)
  - TorShield will automatically rotate your identity at the specified interval

### Using the System Tray

- **Access Quick Actions**
  - Right-click the TorShield icon in the system tray
  - Use the context menu for quick actions like connect/disconnect

- **Minimize to Tray**
  - Close the main window to minimize to tray (if enabled in settings)
  - Click the tray icon to restore the main window

### Disconnecting

- Click the "Disconnect" button to safely terminate the Tor connection
- The application will:
  - Close the Tor controller
  - Reset system proxy settings
  - Terminate Tor processes
  - Return your connection to normal

## Settings

Access the settings dialog by clicking the "Settings" button in the main interface.

### General Settings

- **Auto-connect on startup**: Automatically connect to Tor when the application starts
- **Minimize to tray**: Keep the application running in the background when closed
- **Save connection history**: Record and store connection details for future reference
- **Show speed information**: Display download/upload speed in the main interface

### Privacy Settings

- **Automatic IP changing**: Enable/disable automatic IP rotation
- **IP change interval**: Set the time between automatic IP changes (in minutes)
- **Show IP change notifications**: Enable/disable notifications when IP changes
- **Exit country selection**: Choose preferred countries for Tor exit nodes

### Advanced Settings

- **Proxy host**: Configure custom proxy host (default: 127.0.0.1)
- **Proxy port**: Configure custom proxy port (default: 9050)
- **Custom Tor configuration**: Advanced Tor settings (for experienced users)

## Security Features

- **Clean Process Management**: Proper termination of Tor processes to prevent leaks
- **Port Security**: Checks for port conflicts and resolves them automatically
- **Connection Verification**: Multiple checks to ensure you're actually connected to Tor
- **Secure Proxy Integration**: Properly configures system proxy settings for all traffic
- **Data Directory Management**: Securely handles and cleans Tor data files
- **Connection Monitoring**: Continuous verification of Tor connection status

## Development

### Project Structure

- `main.py` - Application entry point
- `src/ui/` - User interface components
  - `main_window.py` - Main application window
  - `settings_dialog.py` - Settings interface
- `src/utils/` - Utility functions
  - `tor_utils.py` - Tor connection handling
  - `system_utils.py` - System configuration utilities
- `src/models/` - Data models
  - `connection_history.py` - Connection tracking
- `tor/` - Tor binary files

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

TorShield is designed to enhance your privacy online, but no tool can guarantee complete anonymity. Always practice safe browsing habits and be aware of the limitations of anonymity tools. The developers of TorShield are not responsible for any misuse of this software or any consequences arising from its use.

---

<p align="center">
  © 2025 TorShield | v1.0.0
</p>