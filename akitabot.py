import meshtastic
import meshtastic.serial_interface
import meshtastic.tcp_interface
import yaml
import time
import argparse
import logging
from pubsub import pub
from datetime import datetime, time as dt_time
from modules.eccc_weather_service import ECCCWeatherService
from modules.meshtastic_formatter import MeshtasticFormatter

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main Application Logic ---

class AkitaBot:
    """
    The main class for the Akita WeatherBot.
    Orchestrates the Meshtastic interface, weather data fetching, and message handling.
    """
    def __init__(self, settings, port=None, host=None):
        self.settings = settings
        self.port = port
        self.host = host
        self.interface = None
        self.bot_node_num = None
        self.last_alert_check = 0
        self.reboot_scheduled = not self.settings.get('ENABLE_AUTO_REBOOT', False) # True if disabled

        # Initialize services
        self.weather_service = ECCCWeatherService(settings)
        self.formatter = MeshtasticFormatter(settings)
        
        # Subscribe to Meshtastic events
        pub.subscribe(self.on_receive, "meshtastic.receive")
        pub.subscribe(self.on_connection, "meshtastic.connection.established")

    def connect(self):
        """Establishes connection to the Meshtastic device."""
        logging.info("Connecting to Meshtastic device...")
        try:
            if self.port:
                self.interface = meshtastic.serial_interface.SerialInterface(self.port)
            elif self.host:
                self.interface = meshtastic.tcp_interface.TCPInterface(self.host)
            else:
                self.interface = meshtastic.serial_interface.SerialInterface()
        except Exception as e:
            logging.error(f"Could not connect to Meshtastic device: {e}")
            exit(1)

    def on_connection(self, interface, topic=None):
        """Callback fired when a connection to a radio is established."""
        self.bot_node_num = interface.myInfo.my_node_num
        self.bot_node_id = interface.myInfo.node_num_as_string
        logging.info(f"Connection established to node! My node number is: {self.bot_node_num}")
        logging.info(f"My node ID is: {self.bot_node_id}")

    def on_receive(self, packet, interface):
        """Callback fired when a packet is received."""
        decoded = packet.get('decoded', {}) or {}

        # Only proceed if this packet contains a text payload
        if 'text' not in decoded:
            return  # Not a text message

        sender_id = packet.get('from')
        message_text = decoded.get('text', '').strip().lower()
        
        # Try to get the node object to find its string ID for the firewall
        sender_node = interface.nodes.get(sender_id)
        sender_node_id_str = None
        try:
            if sender_node:
                sender_node_id_str = sender_node.get('user', {}).get('id')
        except Exception:
            # Fallback: leave sender_node_id_str as None if structure is unexpected
            sender_node_id_str = None

        if not message_text or sender_id == self.bot_node_num:
            return # Ignore empty messages or messages from ourselves

        # Safely build a display string for logging (avoid formatting strings with :x)
        sender_display = sender_node_id_str if sender_node_id_str else format(sender_id, 'x') if isinstance(sender_id, int) else str(sender_id)
        logging.info(f"Received '{message_text}' from {sender_display}")

        # Enforce DM Mode if enabled
        if self.settings.get('DM_MODE') and packet.get('to') != self.bot_node_num:
            logging.info("Ignoring message on public channel due to DM_MODE=true")
            return

        # Enforce Firewall if enabled
        if self.settings.get('FIREWALL') and sender_node_id_str not in self.settings.get('MYNODES', []):
            logging.warning(f"Ignoring message from non-whitelisted node {sender_node_id_str}")
            return

        self.handle_command(message_text, packet, interface)

    def handle_command(self, command, packet, interface):
        """Processes the received command and sends a reply."""
        reply = ""
        destination_id = packet.get('from')
        forecast = None
        try:
            if command == "?":
                reply = self.formatter.format_help_menu()
            elif command == "test":
                reply = "ACK - Message received."
            elif command == "tst-detail":
                reply = self.formatter.format_test_detail(packet)
            elif command == "alert-status":
                alerts = self.weather_service.get_alerts()
                reply = f"Alert system OK. Found {len(alerts)} active alerts for {self.settings['ALERT_PROVINCE_CODE']}."
            elif command == "advertise":
                logging.info(f"Broadcasting menu from {self.bot_node_id}")
                interface.sendText(self.formatter.format_help_menu())
                return # No direct reply needed
            elif command in ["hourly", "5day", "7day", "4day", "2day", "rain", "temp"]:
                # Fetch data only if needed for the command group
                is_hourly_cmd = command in ["hourly", "rain", "temp"]
                forecast = self.weather_service.get_forecast(hourly=is_hourly_cmd)
                
                if not forecast:
                    reply = "Weather data is currently unavailable."
                elif command == "hourly" and self.settings.get('ENABLE_HOURLY_WEATHER'):
                    reply = self.formatter.format_hourly(forecast)
                elif command == "5day" and self.settings.get('ENABLE_5DAY_FORECAST'):
                    reply = self.formatter.format_daily_forecast(forecast, days=5, details=True)
                elif command == "7day" and self.settings.get('ENABLE_7DAY_FORECAST'):
                    reply = self.formatter.format_daily_forecast(forecast, days=7)
                elif command == "4day":
                    reply = self.formatter.format_daily_forecast(forecast, days=4)
                elif command == "2day":
                    reply = self.formatter.format_daily_forecast(forecast, days=2, details=True)
                elif command == "rain":
                    reply = self.formatter.format_rain(forecast)
                elif command == "temp":
                    reply = self.formatter.format_temp(forecast)
                else:
                    reply = f"Command '{command}' is disabled in settings."
            else:
                reply = f"Unknown command '{command}'. Send '?' for a list of commands."

        except Exception as e:
            logging.error(f"Error handling command '{command}': {e}", exc_info=True)
            reply = "An error occurred. Please try again later."
        
        self.send_reply(reply, destination_id)

    def send_reply(self, text, destination_id):
        """Sends a reply, splitting it into multiple messages if necessary."""
        if not text:
            return
        
        MAX_LEN = 200 # A safe character limit for Meshtastic packets
        messages = [text[i:i+MAX_LEN] for i in range(0, len(text), MAX_LEN)]
        
        for i, msg in enumerate(messages):
            # Build a safe display string for the destination id for logging
            dest_display = format(destination_id, 'x') if isinstance(destination_id, int) else str(destination_id)
            logging.info(f"Sending reply to {dest_display}: {msg}")
            self.interface.sendText(msg, destinationId=destination_id)
            if i < len(messages) - 1:
                time.sleep(self.settings.get('MESSAGE_DELAY', 5))

    def check_for_alerts(self):
        """Periodically checks for new weather alerts and broadcasts them."""
        interval = self.settings.get('ALERT_CHECK_INTERVAL', 300)
        if time.time() - self.last_alert_check < interval:
            return

        logging.info("Checking for new weather alerts...")
        self.last_alert_check = time.time()
        try:
            new_alerts = self.weather_service.get_new_alerts() 
            if new_alerts:
                logging.info(f"Found {len(new_alerts)} new alerts. Broadcasting...")
                for alert in new_alerts:
                    formatted_alert = self.formatter.format_alert(alert)
                    # Broadcast to the primary channel
                    self.interface.sendText(formatted_alert)
                    time.sleep(self.settings.get('MESSAGE_DELAY', 15))
        except Exception as e:
            logging.error(f"Failed to check for or broadcast alerts: {e}")

    def check_for_reboot(self):
        """Periodically checks if a scheduled reboot is due."""
        if not self.settings.get('ENABLE_AUTO_REBOOT', False):
            return

        now = datetime.now()
        reboot_hour = self.settings.get('AUTO_REBOOT_HOUR', 3)
        reboot_minute = self.settings.get('AUTO_REBOOT_MINUTE', 0)
        reboot_time = dt_time(reboot_hour, reboot_minute)

        # If it's the reboot time and we haven't already rebooted today
        if now.time() >= reboot_time and not self.reboot_scheduled:
            logging.info(f"Scheduled reboot time reached. Rebooting node in {self.settings.get('REBOOT_DELAY_SECONDS', 10)} seconds.")
            self.interface.reboot(self.settings.get('REBOOT_DELAY_SECONDS', 10))
            self.reboot_scheduled = True # Mark that we've scheduled it for today
        
        # Reset the flag after midnight
        if now.time() < reboot_time and self.reboot_scheduled:
            logging.info("Past the reboot time. Resetting daily reboot schedule flag.")
            self.reboot_scheduled = False

    def run(self):
        """The main loop of the bot."""
        self.connect()
        while True:
            self.check_for_alerts()
            self.check_for_reboot()
            time.sleep(1) 

    def close(self):
        """Closes the connection to the Meshtastic device."""
        if self.interface:
            self.interface.close()
        logging.info("Connection closed. Shutting down.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Akita WeatherBot for Meshtastic")
    parser.add_argument("--port", help="The serial port for the Meshtastic device (e.g., /dev/ttyUSB0)")
    parser.add_argument("--host", help="The hostname or IP of the Meshtastic device (e.g., meshtastic.local)")
    parser.add_argument("--settings", default="settings_canada.yaml", help="Path to the settings file")
    args = parser.parse_args()

    try:
        with open(args.settings, 'r') as f:
            settings = yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"FATAL: Settings file not found at '{args.settings}'")
        exit(1)
    except Exception as e:
        logging.error(f"FATAL: Error loading settings file: {e}")
        exit(1)

    bot = AkitaBot(settings, port=args.port, host=args.host)
    try:
        bot.run()
    except KeyboardInterrupt:
        logging.info("Shutdown signal received.")
    finally:
        bot.close()
