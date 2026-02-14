import textwrap

class MeshtasticFormatter:
    """
    Formats weather data from the ECCC service into user-friendly strings
    suitable for display on a Meshtastic device.
    """
    ICON_TO_EMOJI = {
        "00": "☀️", "01": "🌤️", "02": "⛅", "03": "☁️", "06": "🌧️",
        "07": "🌨️", "08": "🌦️", "09": "⛈️", "10": "🌫️", "12": "🌧️",
        "13": "🌧️", "15": "🌬️", "16": "❄️", "19": "⛈️", "22": "🌤️",
        "23": "⛅", "24": "☁️", "29": "❄️", "30": "☀️", "31": "🌤️",
        "32": "⛅", "33": "☁️", "34": "☁️", "35": "🌧️", "36": "🌨️",
        "38": "🌦️", "39": "⛈️", "40": "❄️", "43": "💨", "44": "🌫️",
    }

    def __init__(self, settings):
        self.settings = settings

    def get_emoji(self, icon_code):
        """Returns an emoji for a given ECCC weather icon code."""
        # ECCC icon codes can have leading zeros, ensure it's a 2-char string
        code_str = str(icon_code).zfill(2)
        return self.ICON_TO_EMOJI.get(code_str, "❓")

    def format_help_menu(self):
        """Generates the help menu text."""
        menu = "Akita WeatherBot Menu:\n"
        menu += "? - This menu\n"
        menu += "test, tst-detail\n"
        menu += "alert-status, advertise\n"

        if self.settings.get('FULL_MENU'):
            if self.settings.get('ENABLE_5DAY_FORECAST'):
                menu += "5day - 5 day forecast\n"
            if self.settings.get('ENABLE_7DAY_FORECAST'):
                 menu += "7day - 7 day emoji forecast\n"
            if self.settings.get('ENABLE_HOURLY_WEATHER'):
                 menu += "hourly - 24hr hourly forecast\n"
        
        menu += "4day - 4 day simple forecast\n"
        menu += "2day - Today & Tomorrow\n"
        menu += "rain, temp - 24hr forecasts"
        return menu
    
    def format_test_detail(self, packet):
        """Formats the detailed test response."""
        rssi = packet.get('rssi', 'N/A')
        snr = packet.get('snr', 'N/A')
        hops = packet.get('hopLimit', 'N/A')
        return f"ACK! RSSI:{rssi} SNR:{snr} Hops:{hops}"

    def format_daily_forecast(self, forecast_data, days=5, details=False):
        """Formats a daily forecast. Can be simple (emoji) or detailed."""
        if not forecast_data:
            return f"Could not retrieve {days}-day forecast."

        output = []
        # ECCC data has day/night separated. We iterate to find unique day periods.
        day_periods = []
        for entry in forecast_data:
            if "night" not in entry['period'].lower() and entry['period'] not in day_periods:
                day_periods.append(entry['period'])
            if len(day_periods) >= days:
                break
        
        if details:
            # Multi-line, detailed format
            for period_name in day_periods:
                # Find the matching entry
                day_entry = next((e for e in forecast_data if e['period'] == period_name), None)
                if day_entry:
                    emoji = self.get_emoji(day_entry['icon'])
                    temp = day_entry['temp']
                    summary = day_entry['summary']
                    output.append(f"{period_name}: {emoji} {temp}°C\n{summary}")
            return "\n\n".join(output)
        else:
            # Single-line, emoji-only format
            for period_name in day_periods:
                day_entry = next((e for e in forecast_data if e['period'] == period_name), None)
                if day_entry:
                    # Abbreviate period name (e.g., "Monday" -> "Mon")
                    period_abbr = period_name.split()[0][:3]
                    emoji = self.get_emoji(day_entry['icon'])
                    temp = day_entry['temp']
                    output.append(f"{period_abbr}:{emoji}{temp}°")
            return f"{days}-Day: " + " ".join(output)

    def format_hourly(self, hourly_data):
        """Formats the 24-hour forecast into a multi-message string."""
        if not hourly_data:
            return "Could not retrieve hourly forecast."
        
        # Group into chunks of 6 hours for readability; base on available data (cap at 24)
        count = min(len(hourly_data), 24)
        chunks = [hourly_data[i:i + 6] for i in range(0, count, 6)]
        output_parts = []
        for chunk in chunks:
            part = []
            for entry in chunk:
                emoji = self.get_emoji(entry.get('icon'))
                part.append(f"{entry.get('hour')}h:{entry.get('temp')}° {entry.get('pop')}% {emoji}")
            output_parts.append("\n".join(part))
        return "\n\n".join(output_parts)

    def format_rain(self, hourly_data):
        """Formats the 24-hour rain forecast into a compact, single message."""
        if not hourly_data:
            return "Could not retrieve rain forecast."
        
        # Creates a string like "13h:10% 14h:15% 15h:20%..."
        parts = [f"{entry['hour']}h:{entry['pop']}%" for entry in hourly_data[:24]]
        return "24hr POP: " + " ".join(parts)

    def format_temp(self, hourly_data):
        """Formats the 24-hour temperature forecast into a compact, single message."""
        if not hourly_data:
            return "Could not retrieve temperature forecast."
            
        # Creates a string like "13h:15C 14h:14C 15h:13C..."
        parts = [f"{entry['hour']}h:{entry['temp']}C" for entry in hourly_data[:24]]
        return "24hr Temp: " + " ".join(parts)

    def format_alert(self, alert):
        """Formats a weather alert for broadcast."""
        output = f"!! WEATHER ALERT !!\n"
        # Truncate long event names
        output += f"Event: {alert['event'][:40]}\n"
        output += f"Headline: {alert['headline']}"

        if self.settings.get('ALERT_INCLUDE_DESCRIPTION'):
            # Wrap the description to avoid overly long lines
            wrapped_desc = textwrap.fill(alert['description'], width=35)
            output += f"\n\nDetails:\n{wrapped_desc}"

        return output
