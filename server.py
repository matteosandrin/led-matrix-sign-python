from queue import Queue
from flask import Flask, render_template, request
from mbta import MBTATrainStations, MBTA
from mta import mta_stations_by_route, mta_train_station_to_str
from broadcaster import StatusBroadcaster
from common import SignMode, UIMessageType
import config
import subprocess
import os.path


class Server:
    def __init__(
            self, ui_queue: Queue, mode_broadcaster: StatusBroadcaster,
            station_broadcaster: StatusBroadcaster, mta_station_broadcaster: StatusBroadcaster):
        self.app = Flask(__name__)
        self.ui_queue = ui_queue
        self.mode_broadcaster = mode_broadcaster
        self.station_broadcaster = station_broadcaster
        self.mta_station_broadcaster = mta_station_broadcaster
        # Register routes
        self.app.route('/')(self.index)
        self.app.route('/set/mode')(self.set_mode_route)
        self.app.route('/set/station')(self.set_station_route)
        self.app.route('/set/test')(self.set_test_message_route)
        self.app.route('/trigger/banner')(self.trigger_banner_route)
        self.app.route('/set/mta-station')(self.set_mta_station_route)

    def index(self):
        current_mode = self.mode_broadcaster.get_status()
        sign_modes = [mode.name for mode in SignMode]
        params = {
            "SignMode": SignMode,
            "current_mode": current_mode,
            "EMULATE_RGB_MATRIX": config.EMULATE_RGB_MATRIX,
        }
        if current_mode == SignMode.MBTA:
            current_station = self.station_broadcaster.get_status()
            current_station_index = list(MBTATrainStations).index(current_station)
            stations = [MBTA.train_station_to_str(
                station) for station in MBTATrainStations]
            params["mbta_stations"] = stations
            params["mbta_current_station"] = current_station_index
            params["mbta_current_station_label"] = MBTA.train_station_to_str(
                current_station)
        if current_mode == SignMode.MTA:
            stations_by_route = mta_stations_by_route()
            current_station = self.mta_station_broadcaster.get_status()
            params["mta_stations_by_route"] = stations_by_route
            params["mta_current_station_label"] = mta_train_station_to_str(
                current_station)
        return render_template('index.html', **params)

    def set_mode_route(self):
        value = request.args.get('id')
        if value is None:
            return render_template('result.html', message='Mode not provided')
        try:
            mode = list(SignMode)[int(value)]
            self.set_mode(mode)
            return f'Mode set to {mode.name}', 200
        except Exception as e:
            return f'Invalid mode: {value}', 400

    def set_station_route(self):
        value = request.args.get('id')
        if value is None:
            return f'Station not provided', 400
        try:
            station = list(MBTATrainStations)[int(value)]
            self.set_station(station)
            return f'Station set to {station}', 200
        except Exception as e:
            return f'Invalid station: {value}', 400

    def set_mta_station_route(self):
        value = request.args.get('id')
        if value is None:
            return f'Station not provided', 400
        try:
            self.set_mta_station(value)
            return f'Station set to {value}', 200
        except Exception as e:
            return f'Invalid station: {value}', 400

    def trigger_banner_route(self):
        self.ui_queue.put({
            "type": UIMessageType.MBTA_TEST_BANNER,
            "content": ["Alewife train", "is now arriving."]
        })
        return 'Banner triggered', 200

    def set_test_message_route(self):
        value = request.args.get('msg')
        if value is None:
            return 'Message not provided', 400
        self.set_test_message(value)
        return f'Message set to {value}', 200

    def web_server_task(self):
        self.app.run(host='0.0.0.0', port=5000,
                     debug=False, use_reloader=False)

    def set_mode(self, mode: SignMode):
        self.ui_queue.put({"type": UIMessageType.MODE_CHANGE, "mode": mode})

    def set_station(self, station: MBTATrainStations):
        self.ui_queue.put(
            {"type": UIMessageType.MBTA_CHANGE_STATION, "station": station})

    def set_mta_station(self, station: str):
        self.ui_queue.put(
            {"type": UIMessageType.MTA_CHANGE_STATION, "station": station})

    def set_test_message(self, message: str):
        self.ui_queue.put({"type": UIMessageType.TEST, "content": message})
