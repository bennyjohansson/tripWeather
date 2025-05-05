import pytest
import os

@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables before each test."""
    os.environ['GOOGLE_API_KEY'] = 'test_google_key'
    os.environ['WEATHERAPI_API_KEY'] = 'test_weather_key'
    os.environ['OPENAI_API_KEY'] = 'test_openai_key'
    yield
    # Clean up after tests
    os.environ.pop('GOOGLE_API_KEY', None)
    os.environ.pop('WEATHERAPI_API_KEY', None)
    os.environ.pop('OPENAI_API_KEY', None) 