from common import config, SignMode, UIMessageType, RenderMessageType
if config.EMULATE_RGB_MATRIX:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
else:
    import RPi.GPIO as GPIO
import time
import threading
import queue
from datetime import datetime
from enum import Enum
from typing import Optional, List
from mbta import MBTA, TrainStation, PredictionStatus
from mta import MTA
from display import Display
from server import Server
from broadcaster import StatusBroadcaster
from music import Spotify, SpotifyResponse
from animation import AnimationManager
from widget import WidgetManager, ClockWidget, WeatherWidget
from common import Rect


# Constants
BUTTON_PIN = 18
REFRESH_RATE = 0.1  # seconds
SIGN_MODE_KEY = "sign_mode"
DEFAULT_SIGN_MODE = SignMode.MBTA

# Global queues
ui_queue = queue.Queue(maxsize=16)
provider_queue = queue.Queue(maxsize=32)
render_queue = queue.Queue(maxsize=32)

mode_broadcaster = StatusBroadcaster()
mode_broadcaster.set_status(DEFAULT_SIGN_MODE)

mbta = MBTA(api_key=config.MBTA_API_KEY)


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
                mode_broadcaster.set_status(modes[next_index])
                print(f"Mode changed to: {modes[next_index]}")
                # clear the display
                render_queue.put({
                    "type": RenderMessageType.CLEAR,
                })
            elif message["type"] == UIMessageType.MODE_CHANGE:
                # Direct mode change
                new_mode = message.get("mode")
                if new_mode in SignMode:
                    mode_broadcaster.set_status(new_mode)
                    print(f"Mode changed to: {new_mode}")
                    # clear the display
                    render_queue.put({
                        "type": RenderMessageType.CLEAR
                    })
            elif message["type"] == UIMessageType.MBTA_CHANGE_STATION:
                # Direct station change
                new_station = message.get("station")
                if new_station in TrainStation:
                    mbta.set_station(new_station)
                    print(f"Station changed to: {new_station}")
                    render_queue.put({
                        "type": RenderMessageType.TEXT,
                        "content": MBTA.train_station_to_str(new_station)
                    })
            elif message["type"] == UIMessageType.MBTA_TEST_BANNER:
                render_queue.put({
                    "type": RenderMessageType.CLEAR
                })
                render_queue.put({
                    "type": RenderMessageType.MBTA_BANNER,
                    "content": ["Alewife train" , "is now arriving."]
                });
            elif message["type"] == UIMessageType.TEST:
                new_message = message.get("content")
                render_queue.put({
                    "type": RenderMessageType.TEXT,
                    "content": new_message
                })

        except queue.Empty:
            time.sleep(REFRESH_RATE)
            continue


def render_task():
    display = Display()
    animation_manager = AnimationManager(render_queue)
    display.set_animation_manager(animation_manager)
    while True:
        try:
            message = render_queue.get(timeout=REFRESH_RATE)
            if message.get("type") == RenderMessageType.CLEAR:
                display.clear()
            if message.get("type") == RenderMessageType.SWAP:
                display.swap_canvas()
            if message.get("type") == RenderMessageType.TEXT:
                display.render_text_content(message["content"])
            if message.get("type") == RenderMessageType.MBTA:
                display.render_mbta_content(message["content"])
            if message.get("type") == RenderMessageType.MBTA_BANNER:
                display.render_mbta_banner_content(message["content"])
            if message.get("type") == RenderMessageType.MUSIC:
                display.render_music_content(message["content"])
            if message.get("type") == RenderMessageType.FRAME:
                display.render_frame_content(message["content"])
        except queue.Empty:
            continue


def clock_provider_task():
    while True:
        current_mode = mode_broadcaster.get_status()
        if current_mode == SignMode.CLOCK:
            now = datetime.now()
            time_str = now.strftime("%A, %B %d %Y\n%H:%M:%S")
            render_queue.put({
                "type": RenderMessageType.TEXT,
                "content": time_str
            })
        time.sleep(REFRESH_RATE)


def mbta_provider_task():
    while True:
        if mode_broadcaster.get_status() == SignMode.MBTA:
            status, predictions = mbta.get_predictions_both_directions()
            render_queue.put({
                "type": RenderMessageType.MBTA,
                "content": [status, predictions]
            })
            print(status)
            print(predictions)
            if status == PredictionStatus.OK:
                arr_prediction = mbta.find_prediction_with_arriving_banner(
                    predictions)
                if arr_prediction is not None:
                    print("showing arriving banner")
                    render_queue.put({
                        "type": RenderMessageType.MBTA_BANNER,
                        "content": mbta.get_arriving_banner(arr_prediction)
                    })
                    # in total this banner is displayed for 3+5 seconds
                    time.sleep(3) 
                mbta.update_latest_predictions(predictions, [0, 1])
            time.sleep(5)
        else:
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
                    print(f"Album cover fetched for {currently_playing.title} by {currently_playing.artist}")
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
            time.sleep(REFRESH_RATE)


def web_server_task():
    server = Server(ui_queue, mode_broadcaster, mbta.station_broadcaster)
    server.web_server_task()


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

def mta_provider_task():
    mta = MTA(config.MTA_API_KEY)
    while True:
        if mode_broadcaster.get_status() == SignMode.MTA:
            predictions = mta.get_predictions("121")
            print(predictions)
            time.sleep(5)
        else:
            time.sleep(REFRESH_RATE)


def main():
    # Setup
    if not config.EMULATE_RGB_MATRIX:
        setup_gpio()

    # Start threads
    ui_thread = threading.Thread(target=ui_task, daemon=True)
    render_thread = threading.Thread(target=render_task, daemon=True)
    clock_thread = threading.Thread(target=clock_provider_task, daemon=True)
    mbta_thread = threading.Thread(target=mbta_provider_task, daemon=True)
    music_thread = threading.Thread(target=music_provider_task, daemon=True)
    web_server_thread = threading.Thread(target=web_server_task, daemon=True)
    widget_thread = threading.Thread(target=widget_provider_task, daemon=True)
    mta_thread = threading.Thread(target=mta_provider_task, daemon=True)

    ui_thread.start()
    render_thread.start()
    clock_thread.start()
    mbta_thread.start()
    music_thread.start()
    web_server_thread.start()
    widget_thread.start()
    mta_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if not config.EMULATE_RGB_MATRIX:
            GPIO.cleanup()


if __name__ == "__main__":
    main()
