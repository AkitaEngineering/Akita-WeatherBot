# Troubleshooting — Akita WeatherBot

Common issues and how to diagnose/fix them.

1) Bot fails to start: `FATAL: Settings file not found`
- Ensure `settings_canada.yaml` exists in the repository root and contains `ECCC_LOCATION_CODE` and `ALERT_PROVINCE_CODE`.

2) No connection to Meshtastic device
- Verify the correct serial port (Windows: Device Manager, Linux: `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`).
- If using TCP, ensure the device exposes a TCP interface and the host is reachable.
- Check permissions on Linux: you may need to add your user to the `dialout` group or run with appropriate privileges.

3) Alerts not appearing or `get_alerts()` returns empty
- Confirm internet connectivity from the host.
- Verify `ALERT_PROVINCE_CODE` is correct (e.g., `ON`, `BC`, `QC`).
- Test the ECCC feed manually:
```bash
python -c "import requests; print(requests.get('https://weather.gc.ca/rss/cap/canada_e.xml').status_code)"
```

4) Emoji not showing or encoding errors in Windows console
- This is an environment/display issue. Try using Windows Terminal with UTF-8 encoding or view messages on a Meshtastic device.
- Set your console encoding to UTF-8: `chcp 65001` (PowerShell/Command Prompt), or configure Windows Terminal to use UTF-8.

5) Bot reboots unexpectedly
- If `ENABLE_AUTO_REBOOT` is true, the bot may schedule a daily reboot. Check `settings_canada.yaml`.
- Check logs for exceptions or `systemd` restarts if running as a service.

6) Firewall / whitelist blocking messages
- If `FIREWALL` is enabled, ensure the sender node ID is present in `MYNODES` in `settings_canada.yaml`.
- Node IDs are strings like `!c4b787a0` — ensure exact matches.

7) Service logs (systemd)
- `sudo journalctl -u akitabot.service -f` shows logs when running as a `systemd` service.

If an issue persists, collect the bot's logs and open an issue with sample logs and configuration snippets (remove sensitive data).
