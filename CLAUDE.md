# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# Run the main application (requires sudo for hardware access on Raspberry Pi)
sudo python3 main.py

# Run with specific mode
sudo python3 main.py --mode MTA

# Run with fake MTA data for testing
sudo python3 main.py --mta-fake-data
```

### System Service Management
```bash
# Start/stop/restart the systemd service
make start
make stop
make restart

# View logs
make logs

# Update from git and restart
make update

# Update font preview images
make update-font-images
```

### Emulation Mode
Set `EMULATE_RGB_MATRIX = True` in `config/config.py` to run without physical LED matrix hardware. This enables development on non-Raspberry Pi systems using the RGBMatrixEmulator.

## Architecture Overview

### Core Components

**Main Application (`main.py`)**
- Entry point that orchestrates all system components
- Manages multiple threaded tasks for different data providers
- Handles command-line arguments and initialization
- Sets up queues for inter-thread communication

**Display System (`display/`)**
- `Display` class manages the LED matrix hardware/emulator
- Renders different content types (MBTA, MTA, music, clock, widgets)
- `AnimationManager` handles animated transitions
- Separate render modules for each content type (`render_*.py`)

**Data Providers (`providers/`)**
- **MBTA**: Boston transit data with real-time predictions
- **MTA**: NYC subway data with route icons and alerts
- **Music**: Spotify integration with album covers
- Each provider runs in its own thread and updates display queue

**Configuration (`config/`)**
- API keys and settings in `config.py`
- Use `config.example.py` as template for new installations
- Hardware emulation toggle for development

**Common Utilities (`common/`)**
- `SignMode` enum defines display modes (MBTA, MTA, MUSIC, CLOCK, WIDGET)
- Button handling for mode switching and shutdown
- Status broadcasting between components
- Shared fonts, colors, and image resources

### Threading Architecture

The application uses a producer-consumer pattern with these key threads:
- **UI Task**: Processes button presses and web interface commands
- **Render Task**: Consumes render queue and updates display
- **Provider Tasks**: Each data source (MBTA, MTA, Music) runs independently
- **Web Server**: Flask server for remote control interface

### Queue System

Two main queues facilitate communication:
- `ui_queue`: UI events (button presses, web commands)
- `render_queue`: Display commands and content updates

### Configuration Management

API keys and settings are centralized in `config/config.py`. Key configuration options:
- `DEFAULT_SIGN_MODE`: Starting display mode
- `EMULATE_RGB_MATRIX`: Enable/disable hardware emulation
- Provider-specific API keys (MBTA, MTA, Spotify, etc.)
- Default station IDs for transit providers

### Font and Asset Management

Custom pixel fonts optimized for LED matrix display:
- `MBTASans` and `MTASans`: Transit agency branded fonts
- Font images can be regenerated with `update-font-images.py`
- Route icons and symbols stored in `img/` directory

### Web Interface

Flask server provides remote control via web browser:
- Station selection for transit modes
- Mode switching without physical button
- Test message display
- Responsive design for mobile devices