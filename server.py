from queue import Queue
from flask import Flask, render_template, request
from mbta import TrainStation, MBTA
from common import SignMode, UIMessageType

class Server:
    def __init__(self, ui_queue: Queue):
        self.app = Flask(__name__)
        self.ui_queue = ui_queue
        
        # Register routes
        self.app.route('/')(self.index)
        self.app.route('/set/mode')(self.set_mode_route)
        self.app.route('/set/station')(self.set_station_route)

    def index(self):
        stations = [MBTA.train_station_to_str(station) for station in TrainStation]
        sign_modes = [mode.name for mode in SignMode]
        return render_template('index.html', stations=stations, sign_modes=sign_modes)

    def set_mode_route(self):
        value = request.args.get('id')
        if value is None:
            return render_template('result.html', message='Mode not provided')
        try:
            mode = list(SignMode)[int(value)]
            self.set_mode(mode)
            return render_template('result.html', message=f'Mode set to {mode.name}')
        except Exception as e:
            return render_template('result.html', message=f'Invalid mode: {value}')

    def set_station_route(self):
        value = request.args.get('id')
        if value is None:
            return render_template('result.html', message='Station not provided')
        try:
            station = list(TrainStation)[int(value)]
            self.set_station(station)
            return render_template('result.html', message=f'Station set to {station}')
        except Exception as e:
            return render_template('result.html', message=f'Invalid station: {value}')

    def web_server_task(self):
        self.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

    def set_mode(self, mode: SignMode):
        self.ui_queue.put({"type": UIMessageType.MODE_CHANGE, "mode": mode})

    def set_station(self, station: TrainStation):
        self.ui_queue.put({"type": UIMessageType.MBTA_CHANGE_STATION, "station": station})