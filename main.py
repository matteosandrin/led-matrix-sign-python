import random
import config
if config.EMULATE_RGB_MATRIX:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
else:
    import RPi.GPIO as GPIO
import argparse
import providers.mbta as mbta
import providers.mta as mta
import queue
import threading
import time
from common import SignMode, UIMessageType, RenderMessageType, ClockType, Rect
from common.broadcaster import StatusBroadcaster
from datetime import datetime
from display import Display
from pprint import pprint
from providers.music import Spotify, SpotifyResponse
from providers.widget import WidgetManager, ClockWidget, WeatherWidget
from server import Server

# Constants
BUTTON_PIN = 18
REFRESH_RATE = 0.1  # seconds
DEFAULT_SIGN_MODE = SignMode.MBTA

# Global queues
ui_queue = queue.Queue(maxsize=16)
provider_queue = queue.Queue(maxsize=32)
render_queue = queue.Queue(maxsize=32)

mode_broadcaster = StatusBroadcaster()

mbta_client = mbta.MBTA(api_key=config.MBTA_API_KEY)
mta_client = mta.MTA(config.MTA_API_KEY)


def parse_args():
    parser = argparse.ArgumentParser(
        description='LED Matrix Display Controller')
    parser.add_argument(
        '--mode', type=str, choices=[mode.name for mode in SignMode],
        help='Set the default sign mode')
    return parser.parse_args()


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING,
                          callback=button_callback,
                          bouncetime=300)


def button_callback(channel):
    ui_queue.put({"type": UIMessageType.MODE_SHIFT})


def ui_task():
    while True:
        try:
            message = ui_queue.get(timeout=REFRESH_RATE)

            if message["type"] == UIMessageType.MODE_SHIFT:
                # Cycle through modes
                modes = list(SignMode)
                current_mode = mode_broadcaster.get_status()
                current_index = modes.index(current_mode)
                next_index = (current_index + 1) % len(modes)
                # clear the display
                render_queue.put({
                    "type": RenderMessageType.CLEAR,
                })
                mode_broadcaster.set_status(modes[next_index])
                print(f"Mode changed to: {modes[next_index]}")
            elif message["type"] == UIMessageType.MODE_CHANGE:
                # Direct mode change
                new_mode = message.get("mode")
                if new_mode in SignMode:
                    # clear the display
                    render_queue.put({
                        "type": RenderMessageType.CLEAR
                    })
                    mode_broadcaster.set_status(new_mode)
                    print(f"Mode changed to: {new_mode}")
            elif message["type"] == UIMessageType.MBTA_CHANGE_STATION:
                # Direct station change
                new_station = message.get("station")
                if mbta.station_by_id(new_station) is not None:
                    mbta_client.set_station(new_station)
                    print(f"Station changed to: {new_station}")
                    render_queue.put({
                        "type": RenderMessageType.TEXT,
                        "content": mbta.train_station_to_str(new_station)
                    })
            elif message["type"] == UIMessageType.MBTA_TEST_BANNER:
                render_queue.put({
                    "type": RenderMessageType.CLEAR
                })
                render_queue.put({
                    "type": RenderMessageType.MBTA_BANNER,
                    "content": ["Alewife train", "is now arriving."]
                })
            elif message["type"] == UIMessageType.MTA_CHANGE_STATION:
                new_station = message.get("station")
                mta_client.set_current_station(new_station)
                print(f"Station changed to: {new_station}")
                render_queue.put({
                    "type": RenderMessageType.TEXT,
                    "content": mta.train_station_to_str(new_station)
                })
            elif message["type"] == UIMessageType.TEST:
                new_message = message.get("content")
                render_queue.put({
                    "type": RenderMessageType.TEXT,
                    "content": new_message
                })
            elif message["type"] == UIMessageType.MTA_ALERT:
                render_queue.put({
                    "type": RenderMessageType.MTA_ALERT,
                    "content": message.get("content")
                })

        except queue.Empty:
            time.sleep(REFRESH_RATE)
            continue


def render_task():
    display = Display(render_queue)
    while True:
        try:
            message = render_queue.get(timeout=REFRESH_RATE)
            display.render(message)
        except queue.Empty:
            continue


def web_server_task():
    server = Server(ui_queue, mode_broadcaster,
                    mbta_client.station_broadcaster, mta_client.station_broadcaster)
    server.web_server_task()


def clock_provider_task():
    while True:
        current_mode = mode_broadcaster.get_status()
        if current_mode == SignMode.CLOCK:
            render_queue.put({
                "type": RenderMessageType.CLOCK,
                "content": {
                    "type": ClockType.MTA,
                    "time": datetime.now()
                }
            })
        time.sleep(REFRESH_RATE)


def mbta_provider_task():
    while True:
        if mode_broadcaster.get_status() == SignMode.MBTA:
            status, predictions = mbta_client.get_predictions_both_directions()
            render_queue.put({
                "type": RenderMessageType.MBTA,
                "content": [status, predictions]
            })
            print(status)
            print(predictions)
            if status == mbta.PredictionStatus.OK:
                arr_prediction = mbta_client.find_prediction_with_arriving_banner(
                    predictions)
                if arr_prediction is not None:
                    print("showing arriving banner")
                    render_queue.put(
                        {"type": RenderMessageType.MBTA_BANNER,
                         "content": mbta_client.get_arriving_banner(
                             arr_prediction)})
                    # in total this banner is displayed for 3+5 seconds
                    time.sleep(3)
                mbta_client.update_latest_predictions(predictions, [0, 1])
            time.sleep(5)
        else:
            time.sleep(REFRESH_RATE)


def mta_provider_task():
    last_alert_time = time.time()
    alert_messages = mta.AlertMessages()
    while True:
        if mode_broadcaster.get_status() == SignMode.MTA:
            station = mta_client.get_current_station()
            if station is not None:
                predictions = []
                if not config.MTA_FAKE_DATA:
                    predictions = mta_client.get_predictions(station)
                else:
                    predictions = mta_client.get_fake_predictions()
                pprint(predictions[:2])
                render_queue.put({
                    "type": RenderMessageType.MTA,
                    "content": predictions
                })
                if time.time() - last_alert_time > 60 * 5:
                    last_alert_time = time.time()
                    render_queue.put({
                        "type": RenderMessageType.MTA_ALERT,
                        "content": alert_messages.next()
                    })
            time.sleep(5)
        else:
            last_alert_time = time.time()
            time.sleep(REFRESH_RATE)


def music_provider_task():
    spotify = Spotify(config.SPOTIFY_CLIENT_ID,
                      config.SPOTIFY_CLIENT_SECRET, config.SPOTIFY_REFRESH_TOKEN)
    spotify.setup()
    while True:
        if mode_broadcaster.get_status() == SignMode.MUSIC:
            status, currently_playing = spotify.get_currently_playing()
            print(status)
            print(currently_playing)
            if status == SpotifyResponse.OK_NEW_SONG:
                img_status, img = spotify.get_album_cover(currently_playing)
                if img_status == SpotifyResponse.OK:
                    currently_playing.cover.data = img
                    print(
                        f"Album cover fetched for {currently_playing.title} by {currently_playing.artist}")
                spotify.update_current_song(currently_playing)
            elif status == SpotifyResponse.OK:
                pass
            elif status == SpotifyResponse.OK_SHOW_CACHED:
                currently_playing = spotify.get_current_song()
            else:
                spotify.clear_current_song()
            render_queue.put({
                "type": RenderMessageType.MUSIC,
                "content": (status, currently_playing)
            })
            time.sleep(1)
        else:
            if spotify.get_current_song() is not None:
                spotify.clear_current_song()
            time.sleep(REFRESH_RATE)


def widget_provider_task():
    widget_manager = WidgetManager(render_queue)
    widget_manager.add_widget(ClockWidget(
        Rect(40, 8, 80, 16)
    ))
    widget_manager.add_widget(WeatherWidget(
        Rect(0, 0, 32, 32),
        config.IPDATA_API_KEY
    ))

    while True:
        if mode_broadcaster.get_status() == SignMode.WIDGET:
            if not widget_manager.active:
                widget_manager.start()
        else:
            if widget_manager.active:
                widget_manager.stop()
        time.sleep(REFRESH_RATE)


def main():
    args = parse_args()
    initial_mode = DEFAULT_SIGN_MODE
    if hasattr(config, 'DEFAULT_SIGN_MODE'):
        initial_mode = config.DEFAULT_SIGN_MODE
    if args.mode:
        initial_mode = SignMode[args.mode]
    print(f"Initial mode: {initial_mode}")
    mode_broadcaster.set_status(initial_mode)

    if not config.EMULATE_RGB_MATRIX:
        setup_gpio()

    threads = [
        threading.Thread(target=ui_task, daemon=True),
        threading.Thread(target=render_task, daemon=True),
        threading.Thread(target=web_server_task, daemon=True),
        threading.Thread(target=clock_provider_task, daemon=True),
        threading.Thread(target=mbta_provider_task, daemon=True),
        threading.Thread(target=music_provider_task, daemon=True),
        threading.Thread(target=widget_provider_task, daemon=True),
        threading.Thread(target=mta_provider_task, daemon=True)
    ]
    for thread in threads:
        thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if not config.EMULATE_RGB_MATRIX:
            GPIO.cleanup()


if __name__ == "__main__":
    main()
