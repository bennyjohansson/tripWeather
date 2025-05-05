import requests
import polyline
from datetime import datetime, timedelta
import pytz
import openai
import os
from typing import Optional, Dict, List, Tuple, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_api_key(file_path): 
    """Read API key from a file."""
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        logger.error(f"Error: File not found - {file_path}")
        return None

class Config:
    """Configuration management class following the principle of separating configuration from code."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.GOOGLE_API_KEY = read_api_key('../hemligheter/google_api.txt')
            self.WEATHERAPI_API_KEY = read_api_key('../hemligheter/weather_api.txt')
            self.OPENAI_API_KEY = read_api_key('../hemligheter/openai_api.txt')
            
            if not all([self.GOOGLE_API_KEY, self.WEATHERAPI_API_KEY, self.OPENAI_API_KEY]):
                raise ValueError("One or more API keys are missing")
            
            self._initialized = True
    
    def reset(self):
        """Reset the configuration instance (useful for testing)."""
        self._initialized = False

class APIError(Exception):
    """Custom exception for API-related errors."""
    pass

def get_config() -> Config:
    """Get the configuration instance."""
    try:
        return Config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

def get_route_data_detailed(origin: str, destination: str) -> Tuple[List[Tuple[float, float]], List[Dict[str, Any]]]:
    """
    Fetch route data from Google Maps Directions API and decode waypoints.
    
    Args:
        origin: Starting location
        destination: Destination location
        
    Returns:
        Tuple containing:
        - List of (latitude, longitude) tuples
        - List of route steps
        
    Raises:
        APIError: If there's an error fetching the route data
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "key": get_config().GOOGLE_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'OK':
            raise APIError(f"Google Maps API error: {data.get('error_message', 'Unknown error')}")
        
        polyline_points = data["routes"][0]["overview_polyline"]["points"]
        steps = data["routes"][0]["legs"][0]["steps"]
        
        return polyline.decode(polyline_points), steps
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching route data: {e}")
        raise APIError(f"Failed to fetch route data: {e}")

def get_weather_comment(weather_data: List[Dict[str, Any]]) -> str:
    """
    Generate a comment using OpenAI's GPT model.
    
    Args:
        weather_data: List of weather data dictionaries
        
    Returns:
        Generated weather comment
        
    Raises:
        APIError: If there's an error with the OpenAI API
    """
    try:
        client = openai.OpenAI(api_key=get_config().OPENAI_API_KEY)
        prompt = f"Provide a short and high level travel comment based on the following weather data, without going into details on all the stops. However, if there are any indications in the weather forecast that driving can be difficult, such as snowfall, temperatures around 0C or heavy winds, please highlight this. Be quite clean in your comments without unnecessary comments: {weather_data}"
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generating weather comment: {e}")
        raise APIError(f"Failed to generate weather comment: {e}")

def get_route_data(origin: str, destination: str) -> List[Dict[str, Any]]:
    """
    Fetch route data from Google Maps Directions API.
    
    Args:
        origin: Starting location
        destination: Destination location
        
    Returns:
        List of route steps
        
    Raises:
        APIError: If there's an error fetching the route data
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "key": get_config().GOOGLE_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "OK":
            raise APIError(f"Google Maps API error: {data['status']}")
        
        return data["routes"][0]["legs"][0]["steps"]
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching route data: {e}")
        raise APIError(f"Failed to fetch route data: {e}")

def get_city_name(lat: float, lng: float) -> str:
    """
    Get city name from latitude and longitude coordinates.
    
    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate
        
    Returns:
        City name or "Unknown Location" if not found
        
    Raises:
        APIError: If there's an error with the geocoding API
    """
    try:
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={get_config().GOOGLE_API_KEY}"
        response = requests.get(geocode_url, timeout=10)
        response.raise_for_status()
        geocode_result = response.json()
        
        for component in geocode_result.get('results', []):
            address_components = component.get('address_components', [])
            for addr_component in address_components:
                if 'postal_town' in addr_component.get('types', []):
                    return addr_component.get('long_name')
        
        return "Unknown Location"
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching city name: {e}")
        raise APIError(f"Failed to fetch city name: {e}")

def get_weatherAPI_forecast(lat: float, lng: float, date_time: datetime) -> Optional[Dict[str, Any]]:
    """
    Get weather forecast for a specific location and time.
    
    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate
        date_time: Date and time for the forecast
        
    Returns:
        Weather forecast data or None if not available
        
    Raises:
        APIError: If there's an error with the weather API
    """
    try:
        date_str = date_time.strftime("%Y-%m-%d")
        url = f"http://api.weatherapi.com/v1/forecast.json?key={get_config().WEATHERAPI_API_KEY}&q={lat},{lng}&dt={date_str}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        forecast_data = response.json()
        forecast_day = forecast_data.get('forecast', {}).get('forecastday', [])[0]
        
        if not forecast_day:
            return None
        
        closest_hour = min(
            forecast_day['hour'],
            key=lambda h: abs(datetime.strptime(h['time'], "%Y-%m-%d %H:%M") - date_time)
        )
        
        return extract_weatherAPI_details(closest_hour)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather forecast: {e}")
        raise APIError(f"Failed to fetch weather forecast: {e}")

def extract_weatherAPI_details(weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and format weather details from API response.
    
    Args:
        weather_data: Raw weather data from API
        
    Returns:
        Formatted weather details
    """
    temperature = weather_data.get('temp_c', None)
    precipitation = weather_data.get('precip_mm', None)
    wind_speed = weather_data.get('wind_kph', None)
    icon_url = weather_data.get('condition', {}).get('icon', None)
    
    if icon_url and not icon_url.startswith("http"):
        icon_url = "https:" + icon_url
    
    if wind_speed is not None:
        wind_speed = round(wind_speed / 3.6, 1)  # Convert kph to mps
        
    return {
        "temperature": temperature,
        "precipitation": precipitation,
        "wind_speed": wind_speed,
        "icon_url": icon_url
    }

def find_weather_along_route(origin: str, destination: str, start_date_time: datetime) -> List[Dict[str, Any]]:
    """
    Find weather conditions along a route at regular intervals.
    
    Args:
        origin: Starting location
        destination: Destination location
        start_date_time: Start time of the journey
        
    Returns:
        List of weather data points along the route
        
    Raises:
        APIError: If there's an error fetching route or weather data
    """
    try:
        waypoints, steps = get_route_data_detailed(origin, destination)
        
        if not waypoints:
            return []
        
        current_time = start_date_time
        weather_data_list = []
        lat_start, lng_start = waypoints[0]
        total_stops = 10
        interval = max(1, len(waypoints) // (total_stops - 1))
        
        for i, (lat, lng) in enumerate(waypoints):
            if i % interval == 0 or i == len(waypoints) - 1:
                steps = get_route_data(f"{lat_start},{lng_start}", f"{lat},{lng}")
                
                for step in steps:
                    duration = step['duration']['value']
                    current_time = current_time + timedelta(seconds=duration)
                
                city = get_city_name(lat, lng)
                weather = get_weatherAPI_forecast(lat, lng, current_time)
                
                if weather:
                    weather_dict = {
                        "City": city,
                        "Time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "Temperature": weather['temperature'],
                        "Precipitation": weather['precipitation'],
                        "WindSpeed": weather['wind_speed'],
                        "IconURL": weather['icon_url']
                    }
                    weather_data_list.append(weather_dict)
                
                lat_start, lng_start = lat, lng
        
        return weather_data_list
        
    except Exception as e:
        logger.error(f"Error finding weather along route: {e}")
        raise APIError(f"Failed to find weather along route: {e}")

if __name__ == "__main__":
    # Example usage
    try:
        test_origin = "Sundsvall, Sweden"
        test_destination = "Stockholm, Sweden"
        test_start_time = datetime.now()
        
        weather_data = find_weather_along_route(test_origin, test_destination, test_start_time)
        print(weather_data)
        
    except APIError as e:
        logger.error(f"API Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
