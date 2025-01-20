from flask import Flask, render_template
from mbta import TrainStation, MBTA
from common import SignMode

app = Flask(__name__)


@app.route('/')
def index():
    stations = [MBTA.train_station_to_str(station) for station in TrainStation]
    sign_modes = [mode.name for mode in SignMode]
    return render_template('index.html', stations=stations, sign_modes=sign_modes)

# @app.route('/mode/<mode>')
# def set_mode(mode):
#     global current_mode
#     try:
#         current_mode = SignMode[mode.upper()]
#         return f'Mode set to {mode}'
#     except KeyError:
#         return f'Invalid mode: {mode}', 400


def web_server_task():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    print("Web server started")
