from queue import Queue
from flask import Flask, render_template, request
from common import SignMode, UIMessageType
from common.broadcaster import StatusBroadcaster
import config
import subprocess
import os.path
import providers.mta as mta
import providers.mbta as mbta
import random


class Server:
    def __init__(
            self, ui_queue: Queue, mode_broadcaster: StatusBroadcaster,
            station_broadcaster: StatusBroadcaster,
            mta_station_broadcaster: StatusBroadcaster):
        self.app = Flask(__name__)
        self.ui_queue = ui_queue
        self.mode_broadcaster = mode_broadcaster
        self.station_broadcaster = station_broadcaster
        self.mta_station_broadcaster = mta_station_broadcaster
        # Register routes
        self.app.route('/')(self.index)
        self.app.route('/set/mode')(self.set_mode_route)
        self.app.route('/set/mbta-station')(self.set_mbta_station_route)
        self.app.route('/set/mta-station')(self.set_mta_station_route)
        self.app.route('/set/test')(self.set_test_message_route)
        self.app.route('/trigger/mbta-alert')(self.trigger_mbta_alert_route)
        self.app.route('/trigger/mta-alert')(self.trigger_mta_alert_route)
        self.app.route('/trigger/mode-shift')(self.trigger_mode_shift_route)
        self.app.route('/trigger/shutdown')(self.trigger_shutdown_route)

    def index(self):
        current_mode = self.mode_broadcaster.get_status()
        params = {
            "SignMode": SignMode,
            "current_mode": current_mode,
            "EMULATE_RGB_MATRIX": config.EMULATE_RGB_MATRIX,
        }
        if current_mode == SignMode.MBTA:
            stations_by_route = mbta.stations_by_route()
            current_station = self.station_broadcaster.get_status()
            params["mbta_stations_by_route"] = stations_by_route
            params["mbta_current_station_label"] = mbta.train_station_to_str(
                current_station)
        if current_mode == SignMode.MTA:
            stations_by_route = mta.stations_by_route()
            current_station = self.mta_station_broadcaster.get_status()
            params["mta_stations_by_route"] = stations_by_route
            params["mta_current_station_label"] = mta.train_station_to_str(
                current_station)
        return render_template('index.html', **params)

    def set_mode_route(self):
        value = request.args.get('id')
        if value is None:
            return render_template('result.html', message='Mode not provided')
        try:
            mode = list(SignMode)[int(value)]
            self.ui_queue.put({"type": UIMessageType.MODE_CHANGE, "mode": mode})
            return f'Mode set to {mode.name}', 200
        except Exception as e:
            return f'Invalid mode: {value}', 400

    def set_mbta_station_route(self):
        value = request.args.get('id')
        if value is None:
            return f'Station not provided', 400
        try:
            station = mbta.station_by_id(value)
            if station is not None:
                self.ui_queue.put(
                    {"type": UIMessageType.MBTA_CHANGE_STATION, "station": value})
                return f'Station set to {value}', 200
            else:
                raise Exception(f'Invalid station: {value}')
        except Exception as e:
            return f'Invalid station: {value}', 400

    def set_mta_station_route(self):
        value = request.args.get('id')
        if value is None:
            return f'Station not provided', 400
        try:
            self.ui_queue.put(
                {"type": UIMessageType.MTA_CHANGE_STATION, "station": value})
            return f'Station set to {value}', 200
        except Exception as e:
            return f'Invalid station: {value}', 400

    def trigger_mbta_alert_route(self):
        self.ui_queue.put({
            "type": UIMessageType.MBTA_TEST_BANNER,
            "content": ["Alewife train", "is now arriving."]
        })
        return 'Banner triggered', 200

    def set_test_message_route(self):
        value = request.args.get('msg')
        if value is None:
            return 'Message not provided', 400
        self.ui_queue.put({"type": UIMessageType.TEST, "content": message})
        return f'Message set to {value}', 200

    def trigger_mta_alert_route(self):
        self.ui_queue.put({
            "type": UIMessageType.MTA_ALERT,
            "content": mta.AlertMessages.random()
        })
        return 'MTA alert triggered', 200

    def trigger_mode_shift_route(self):
        self.ui_queue.put({"type": UIMessageType.MODE_SHIFT})
        return 'Mode shift triggered', 200

    def trigger_shutdown_route(self):
        self.ui_queue.put({"type": UIMessageType.SHUTDOWN})
        return 'Shutdown triggered', 200

    def web_server_task(self):
        self.app.run(host='0.0.0.0', port=5000,
                     debug=False, use_reloader=False)
