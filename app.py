from flask import Flask, render_template, request
from datetime import datetime
from tripweather import find_weather_along_route  # Replace with the actual import

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    weather_data = []
    if request.method == 'POST':
        origin = request.form['origin']
        destination = request.form['destination']
        starttime = request.form['starttime']
        start_time = datetime.strptime(starttime, '%Y-%m-%dT%H:%M')
        
        weather_data = find_weather_along_route(origin, destination, start_time)
    
    return render_template('index.html', weather_data=weather_data)

if __name__ == '__main__':
    app.run(debug=True)