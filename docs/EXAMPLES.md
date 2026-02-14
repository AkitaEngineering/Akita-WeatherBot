# Examples — Akita WeatherBot

This file shows typical commands you can send to the bot and example replies.

Commands (send as a DM to the bot node):

- `?`
  - Reply: a short menu listing available commands.

- `test`
  - Reply: `ACK - Message received.`

- `tst-detail`
  - Reply: `ACK! RSSI:-75 SNR:7.5 Hops:2` (values vary by packet)

- `alert-status`
  - Reply: `Alert system OK. Found 1 active alerts for ON.` (value depends on ECCC feed)

- `hourly`
  - Reply: A multi-line hourly forecast (grouped in 6-hour chunks).
    Example snippet:
    ```
    12h:5° 10% ☀️
    13h:4° 20% ☁️
    ...
    ```

- `5day`, `7day`, `4day`, `2day`
  - Reply: daily forecasts either detailed or emoji summaries depending on command and settings.

- `rain`
  - Reply: `24hr POP: 12h:10% 13h:15% 14h:20% ...`

- `temp`
  - Reply: `24hr Temp: 12h:5C 13h:4C 14h:3C ...`

Notes
- Output formatting depends on the settings in `settings_canada.yaml` (e.g., `FULL_MENU`, enabled forecasts).
- Emojis may not render properly in all terminal environments but will appear correctly on many Meshtastic devices and modern terminals that support Unicode.
