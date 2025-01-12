from flask import Flask, render_template, request
from datetime import datetime
from tripweather import find_weather_along_route, get_weather_comment  # Ensure these functions are correctly imported

app = Flask(__name__)
# app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF protection for testing

@app.route('/', methods=['GET', 'POST'])
def index():
    weather_data = []
    ai_comment = ""
    if request.method == 'POST':
        origin = request.form['origin']
        destination = request.form['destination']
        starttime = request.form['starttime']
        start_time = datetime.strptime(starttime, '%Y-%m-%dT%H:%M')
        
        weather_data = find_weather_along_route(origin, destination, start_time)
        if weather_data:
            ai_comment = get_weather_comment(weather_data)
    
    return render_template('index.html', weather_data=weather_data, ai_comment=ai_comment)

if __name__ == '__main__':
    app.run(debug=True)