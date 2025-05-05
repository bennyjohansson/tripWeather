import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from tripweather import (
    Config,
    APIError,
    get_route_data_detailed,
    get_weather_comment,
    get_route_data,
    get_city_name,
    get_weatherAPI_forecast,
    extract_weatherAPI_details,
    find_weather_along_route
)

class TestConfig(unittest.TestCase):
    """Test cases for the Config class."""
    
    def setUp(self):
        """Reset the Config singleton before each test."""
        Config._instance = None
    
    @patch('os.getenv')
    def test_config_initialization(self, mock_getenv):
        """Test that Config properly initializes with environment variables."""
        mock_getenv.side_effect = lambda x: {
            'GOOGLE_API_KEY': 'test_google_key',
            'WEATHERAPI_API_KEY': 'test_weather_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }[x]
        
        config = Config()
        self.assertEqual(config.GOOGLE_API_KEY, 'test_google_key')
        self.assertEqual(config.WEATHERAPI_API_KEY, 'test_weather_key')
        self.assertEqual(config.OPENAI_API_KEY, 'test_openai_key')
    
    @patch('os.getenv')
    def test_missing_api_key(self, mock_getenv):
        """Test that Config raises ValueError when API key is missing."""
        mock_getenv.return_value = None
        with self.assertRaises(ValueError):
            Config()

class TestRouteData(unittest.TestCase):
    """Test cases for route data functions."""
    
    @patch('requests.get')
    def test_get_route_data_detailed_success(self, mock_get):
        """Test successful route data retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'OK',
            'routes': [{
                'overview_polyline': {'points': 'test_points'},
                'legs': [{'steps': ['step1', 'step2']}]
            }]
        }
        mock_get.return_value = mock_response
        
        with patch('polyline.decode', return_value=[(1.0, 2.0), (3.0, 4.0)]):
            waypoints, steps = get_route_data_detailed('origin', 'destination')
            self.assertEqual(len(waypoints), 2)
            self.assertEqual(steps, ['step1', 'step2'])
    
    @patch('requests.get')
    def test_get_route_data_detailed_error(self, mock_get):
        """Test error handling in route data retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'ERROR', 'error_message': 'Invalid request'}
        mock_get.return_value = mock_response
        
        with self.assertRaises(APIError):
            get_route_data_detailed('origin', 'destination')

class TestWeatherAPI(unittest.TestCase):
    """Test cases for weather API functions."""
    
    @patch('requests.get')
    def test_get_weatherAPI_forecast_success(self, mock_get):
        """Test successful weather forecast retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'forecast': {
                'forecastday': [{
                    'hour': [
                        {'time': '2024-01-01 12:00', 'temp_c': 20, 'precip_mm': 0, 'wind_kph': 10, 'condition': {'icon': 'test.png'}}
                    ]
                }]
            }
        }
        mock_get.return_value = mock_response
        
        weather = get_weatherAPI_forecast(1.0, 2.0, datetime(2024, 1, 1, 12, 0))
        self.assertIsNotNone(weather)
        self.assertEqual(weather['temperature'], 20)
    
    def test_extract_weatherAPI_details(self):
        """Test weather data extraction and conversion."""
        test_data = {
            'temp_c': 20,
            'precip_mm': 5,
            'wind_kph': 36,
            'condition': {'icon': '//test.png'}
        }
        
        result = extract_weatherAPI_details(test_data)
        self.assertEqual(result['temperature'], 20)
        self.assertEqual(result['precipitation'], 5)
        self.assertEqual(result['wind_speed'], 10.0)  # 36 kph = 10 m/s
        self.assertEqual(result['icon_url'], 'https://test.png')

class TestCityName(unittest.TestCase):
    """Test cases for city name retrieval."""
    
    @patch('requests.get')
    def test_get_city_name_success(self, mock_get):
        """Test successful city name retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': [{
                'address_components': [
                    {'types': ['postal_town'], 'long_name': 'Test City'}
                ]
            }]
        }
        mock_get.return_value = mock_response
        
        city = get_city_name(1.0, 2.0)
        self.assertEqual(city, 'Test City')
    
    @patch('requests.get')
    def test_get_city_name_not_found(self, mock_get):
        """Test city name retrieval when city is not found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response
        
        city = get_city_name(1.0, 2.0)
        self.assertEqual(city, 'Unknown Location')

class TestWeatherComment(unittest.TestCase):
    """Test cases for weather comment generation."""
    
    @patch('openai.chat.completions.create')
    def test_get_weather_comment_success(self, mock_create):
        """Test successful weather comment generation."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='Test comment'))]
        mock_create.return_value = mock_response
        
        comment = get_weather_comment([{'temperature': 20}])
        self.assertEqual(comment, 'Test comment')

class TestFindWeatherAlongRoute(unittest.TestCase):
    """Test cases for finding weather along a route."""
    
    @patch('tripweather.get_route_data_detailed')
    @patch('tripweather.get_route_data')
    @patch('tripweather.get_city_name')
    @patch('tripweather.get_weatherAPI_forecast')
    def test_find_weather_along_route_success(self, mock_forecast, mock_city, mock_route, mock_route_detailed):
        """Test successful weather data retrieval along a route."""
        # Setup mocks
        mock_route_detailed.return_value = ([(1.0, 2.0), (3.0, 4.0)], [])
        mock_route.return_value = [{'duration': {'value': 3600}}]
        mock_city.return_value = 'Test City'
        mock_forecast.return_value = {
            'temperature': 20,
            'precipitation': 0,
            'wind_speed': 10,
            'icon_url': 'test.png'
        }
        
        start_time = datetime(2024, 1, 1, 12, 0)
        weather_data = find_weather_along_route('origin', 'destination', start_time)
        
        self.assertEqual(len(weather_data), 2)
        self.assertEqual(weather_data[0]['City'], 'Test City')
        self.assertEqual(weather_data[0]['Temperature'], 20)

if __name__ == '__main__':
    unittest.main() 