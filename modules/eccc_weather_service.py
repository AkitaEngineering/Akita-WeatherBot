import requests
import logging
import time
from lxml import etree

class ECCCWeatherService:
    """
    Handles all data fetching and parsing from Environment and Climate Change Canada (ECCC).
    Includes caching to minimize redundant API calls.
    """
    BASE_URL = "https://dd.weather.gc.ca/citypage_weather/xml"
    ALERT_URL = "https://weather.gc.ca/rss/cap/canada_e.xml"

    def __init__(self, settings):
        self.location_code = settings.get('ECCC_LOCATION_CODE')
        self.province_code = settings.get('ALERT_PROVINCE_CODE')
        self.user_agent = f"{settings.get('USER_AGENT_APP', 'AkitaWeatherBot/1.0')} ({settings.get('USER_AGENT_EMAIL', 'user@example.com')})"
        
        # Caching
        self.forecast_cache = {'daily': None, 'hourly': None}
        self.forecast_cache_time = {'daily': 0, 'hourly': 0}
        self.alert_cache = None
        self.alert_cache_time = 0
        self.sent_alert_ids = set() # To track broadcasted alerts and avoid duplicates

        if not self.location_code or not self.province_code:
            raise ValueError("ECCC_LOCATION_CODE and ALERT_PROVINCE_CODE must be set in settings.")

    def _make_request(self, url):
        """
        Private helper to make HTTP requests with proper headers and error handling.
        """
        headers = {'User-Agent': self.user_agent}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
            return response.content
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch data from {url}: {e}")
            return None

    def get_forecast(self, hourly=False):
        """
        Fetches daily or hourly forecast data for the configured location.
        Uses a cache to avoid fetching data more than once per hour.
        """
        cache_key = 'hourly' if hourly else 'daily'
        cache_duration = 3600  # 1 hour

        if time.time() - self.forecast_cache_time[cache_key] < cache_duration and self.forecast_cache[cache_key]:
            logging.info(f"Using cached {cache_key} forecast data.")
            return self.forecast_cache[cache_key]

        # URL format is BASE_URL/{PROVINCE_CODE}/{LOCATION_CODE}_e.xml
        forecast_url = f"{self.BASE_URL}/{self.province_code}/{self.location_code}_e.xml"
        xml_data = self._make_request(forecast_url)

        if not xml_data:
            return None
        
        logging.info(f"Successfully fetched new {cache_key} forecast data.")
        root = etree.fromstring(xml_data)

        # Parse both daily and hourly forecasts at once, since they are in the same file
        self.forecast_cache['daily'] = self._parse_daily_forecast(root)
        self.forecast_cache['hourly'] = self._parse_hourly_forecast(root)
        
        # Update cache times for both
        self.forecast_cache_time['daily'] = time.time()
        self.forecast_cache_time['hourly'] = time.time()

        return self.forecast_cache[cache_key]

    def _parse_daily_forecast(self, root):
        """Parses the daily forecast data from the XML tree."""
        forecasts = []
        # XPath to get each daily forecast entry
        for entry in root.xpath('//forecastGroup/forecast'):
            period = entry.findtext('period')
            icon = entry.findtext('abbreviatedForecast/iconCode')
            temp = entry.findtext('temperatures/temperature')
            summary = entry.findtext('textSummary')
            
            forecasts.append({
                'period': period,
                'icon': icon,
                'temp': temp,
                'summary': summary
            })
        return forecasts

    def _parse_hourly_forecast(self, root):
        """Parses the hourly forecast data from the XML tree."""
        forecasts = []
        # XPath to get each hourly forecast entry
        for entry in root.xpath('//hourlyForecastGroup/hourlyForecast'):
            # dateTimeUTC may be missing or in different formats; guard access
            dt_attr = entry.get('dateTimeUTC') or entry.findtext('dateTimeUTC')
            hour = ''
            if dt_attr and len(dt_attr) >= 4:
                try:
                    hour = dt_attr[-4:-2]
                except Exception:
                    hour = ''

            condition = entry.findtext('condition')
            icon = entry.findtext('iconCode')
            temp = entry.findtext('temperature')
            pop = entry.findtext('lop') or entry.findtext('pop')  # try common tags
            
            forecasts.append({
                'hour': hour,
                'condition': condition,
                'icon': icon,
                'temp': temp,
                'pop': pop if pop else '0' # Default to 0 if PoP is not present
            })
        return forecasts

    def get_alerts(self):
        """
        Fetches all active alerts for the configured province.
        Uses a cache to avoid fetching data too frequently.
        """
        cache_duration = 300 # 5 minutes
        if time.time() - self.alert_cache_time < cache_duration and self.alert_cache is not None:
            logging.info("Using cached alert data.")
            return self.alert_cache

        xml_data = self._make_request(self.ALERT_URL)
        if not xml_data:
            return []

        root = etree.fromstring(xml_data)
        # XML Namespace for CAP alerts
        ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
        
        alerts = []
        # Iterate CAP alerts and filter by area description containing the province code.
        for entry in root.xpath('//cap:alert', namespaces=ns):
            area_desc = entry.findtext('cap:info/cap:area/cap:areaDesc', namespaces=ns)
            if not area_desc or self.province_code not in area_desc:
                continue

            alert_id = entry.findtext('cap:identifier', namespaces=ns)
            event = entry.findtext('cap:info/cap:event', namespaces=ns)
            headline = entry.findtext('cap:info/cap:headline', namespaces=ns)
            description = entry.findtext('cap:info/cap:description', namespaces=ns)

            alerts.append({
                'id': alert_id,
                'event': event,
                'headline': headline,
                'description': description
            })
        
        logging.info(f"Fetched {len(alerts)} alerts for province {self.province_code}.")
        self.alert_cache = alerts
        self.alert_cache_time = time.time()
        return self.alert_cache

    def get_new_alerts(self):
        """
        Checks for alerts and returns only those that haven't been sent before.
        """
        all_alerts = self.get_alerts()
        new_alerts = []
        for alert in all_alerts:
            if alert['id'] not in self.sent_alert_ids:
                new_alerts.append(alert)
                self.sent_alert_ids.add(alert['id'])
        
        return new_alerts
