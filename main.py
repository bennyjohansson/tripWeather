

import requests
import polyline
from datetime import datetime, timedelta
import pytz  # To handle time zones

# Replace these with your API keys and user agent
GOOGLE_API_KEY ="AIzaSyDcgsAt28mZ7oH7o7uraizEcqSjqdMAbu0"
YR_USER_AGENT = "YourApp/1.0 (your.email@example.com)"

def get_route_data_detailed(origin, destination):
    """
    Fetch route data from Google Maps Directions API and decode waypoints.
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "key": GOOGLE_API_KEY
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    
    
    if data["status"] != "OK":
        print(f"Error fetching route: {data['status']}")
        return None
    
    # Decode the polyline for detailed waypoints
    polyline_points = data["routes"][0]["overview_polyline"]["points"]
    polyline_detail = data["routes"][0]["overview_polyline"]
    steps = data["routes"][0]["legs"][0]["steps"]
    
    
    
    return polyline.decode(polyline_points), steps  # Return steps along with the waypoints

def get_route_data(origin, destination):
    """
    Fetching the route data from Google Maps Directions API and and jsut returning the steps
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "key": GOOGLE_API_KEY
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    if data["status"] != "OK":
        print(f"Error fetching route: {data['status']}")
        return None
    
    # Decode the polyline for detailed waypoints
    steps = data["routes"][0]["legs"][0]["steps"]
    
    return steps  # Return steps along with the waypoints

def get_city_name(lat, lng):
    # Perform the geocode request to get address details based on latitude and longitude
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={GOOGLE_API_KEY}"
    response = requests.get(geocode_url)
    geocode_result = response.json()

    # Iterate through the geocode result to find the main city (postal_town)
    for component in geocode_result.get('results', []):
        address_components = component.get('address_components', [])
        for addr_component in address_components:
            if 'postal_town' in addr_component.get('types', []):
                return addr_component.get('long_name')
    
    # Fallback: if city not found, return a default string or None
    return "Unknown Location"

from datetime import datetime

def get_weather_data(lat, lng, user_agent, target_time):
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lng}"
    
    headers = {
        "User-Agent": user_agent
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return None  # Handle the error if the response status is not 200
    
    weather_data = response.json()
    # print(weather_data)
    times = weather_data['properties']['timeseries']
    
    # Convert current_time to naive datetime
    target_time = target_time.replace(tzinfo=None)
    
    for time in times:
        api_time = datetime.strptime(time['time'], "%Y-%m-%dT%H:%M:%SZ")
        # print(time)
        
        # Ensure the time block is greater than or equal to current_time
        if api_time >= target_time:
            temperature = time['data']['instant']['details'].get('air_temperature', 0.0)
            wind_speed = time['data']['instant']['details'].get('windspeed', {}).get('mps', 0.0)
            precipitation = time['data']['next_1_hours'].get('details', {}).get('precipitation_amount', 0.0)
            description = time['data']['next_1_hours'].get('summary', "No data")
            time_of_report = time
            
            # Return as a dictionary
            return {
                "temperature": temperature,
                "wind_speed": wind_speed,
                "precipitation": precipitation,
                "description": description
            }
    
    return None  # If no data found

def find_main_cities_with_weather(origin, destination, start_date, start_time="09:00"):
    """
    Find main cities along the route with weather details, including the time.
    - `start_date`: Date when the driver starts (e.g., "2025-01-10").
    - `start_time`: Time when the driver starts (e.g., "08:30").
    """
    # Combine start date and time into a full datetime object
    start_datetime_str = f"{start_date} {start_time}"  # E.g., "2025-01-10 08:30"
    start_datetime = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")
    start_datetime = pytz.UTC.localize(start_datetime)  # Make it timezone-aware in UTC
    
    waypoints, steps = get_route_data_detailed(origin, destination)
    
    
    if not waypoints:
        return
    
    current_time = start_datetime  # Start from the given start time
    waypoint_index = 0  # Pointer for waypoints
    print("Locations and Weather Along the Route:")
    
   
    #Looping over all the waypoints. I want to split the route in 10 parts and get the city and weather at each of the 10 points at the expexted arrival there. 
    # To get the arrival time at next waypoint I use the get_route_data function to get the steps and then get the duration and distance to the next waypoint.
    # I then add the duration to the current time to get the expected arrival time at the next waypoint.
    # I then get the city name and weather at that time.
    
    #getting lat and long of the first waypoint
    lat_start, lng_start = waypoints[0]
    
    for i, (lat, lng) in enumerate(waypoints):
        
        if(i%20==0):
            #Getting the route from the start to the current waypoint using the lat_start and lng_start
            steps = get_route_data(f"{lat_start},{lng_start}", f"{lat},{lng}")
            
            #looping over the steps to get the duration and distance to the next waypoint
            for step in steps:
                duration = step['duration']['value']
                distance = step['distance']['value']
                
                #printing the duration and distance to the next waypoint
                # print(f"Duration: {step['duration']} seconds, Distance: {distance} meters")
                #Adding the duration to the current time to get the expected arrival time at the next waypoint
                current_time = current_time + timedelta(seconds=duration)
                #Getting the city name at the next waypoint

            #Getting the city name at the next waypoint
            city = get_city_name(lat, lng)
            #Getting the weather at the next waypoint
            weather = get_weather_data(lat, lng, YR_USER_AGENT, current_time)
            
            #Printing the city and weather at the next waypoint
            # print(f"{city}: {weather}")
            #printing the time for the waypioint that we show the weather for
            # print(current_time)
            #Creating a dictionary with the city and weather and time for the waypoint
            weather_dict = {"City": city, "Weather": weather, "Time": current_time}
            
            #printing the dictionary
            print(weather_dict)
            
            #Updating the lat and long of the start waypoint
            lat_start, lng_start = lat, lng
                    
                
        

# Example usage
if __name__ == "__main__":
    origin = "Sundsvall, Sweden"
    destination = "Danderyd, Sweden"
    start_date = "2025-01-04"  # Specify the start date here
    start_time = "09:00"  # Specify the start time here
    find_main_cities_with_weather(origin, destination, start_date, start_time)
