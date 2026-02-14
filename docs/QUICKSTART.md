# Akita WeatherBot — Quickstart

This quickstart gets you running the `Akita WeatherBot` locally for testing or short-term use.

Prerequisites
- Python 3.11+ installed
- A Meshtastic device connected (USB) or reachable via TCP on your network
- Internet access for ECCC API requests

1) Clone repository
```bash
git clone https://github.com/AkitaEngineering/Akita-WeatherBot.git
cd Akita-WeatherBot
```

2) Create and activate a virtual environment

Linux / macOS:
```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```

3) Install dependencies
```bash
pip install -r requirements.txt
```

4) Configure `settings_canada.yaml`
- Set `ECCC_LOCATION_CODE` to your site code (see README for how to find it).
- Set `ALERT_PROVINCE_CODE` to your two-letter province code (e.g., `ON`).
- Adjust `MYNODES`, `DM_MODE`, `FIREWALL` and message settings as needed.

5) Run the bot
- Using serial/USB (replace with your port):
```bash
python akitabot.py --port /dev/ttyUSB0
# Windows example
python akitabot.py --port COM7
```
- Using TCP (if your Meshtastic node is reachable on the network):
```bash
python akitabot.py --host meshtastic.local
```

6) Verify
- Send a DM to the bot node with `?` to get the menu.
- Check logs printed in the terminal for startup information and errors.

Helpful commands
```bash
# Run basic health check from repo root (venv active)
python -c "from modules.eccc_weather_service import ECCCWeatherService; print('OK' if ECCCWeatherService({'ECCC_LOCATION_CODE':'s0000000','ALERT_PROVINCE_CODE':'ON'}) else 'INIT_FAIL')"
```

Notes
- For 24/7 deployments see `Deployment Guide - Akita WeatherBot` or `docs/TROUBLESHOOTING.md` for `systemd` instructions.
