import time
import threading
import queue
from datetime import datetime
from enum import Enum
import RPi.GPIO as GPIO
from typing import Optional, List
from mbta import MBTA, TrainStation
from display import Display
from server import Server
from common import SignMode, UIMessageType
from broadcaster import StatusBroadcaster
from music import Spotify, SpotifyResponse
import config


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
            
            elif message["type"] == UIMessageType.MODE_CHANGE:
                # Direct mode change
                new_mode = message.get("mode")
                if new_mode in SignMode:
                    mode_broadcaster.set_status(new_mode)
                    print(f"Mode changed to: {new_mode}")
            
            elif message["type"] == UIMessageType.MBTA_CHANGE_STATION:
                # Direct station change
                new_station = message.get("station")
                if new_station in TrainStation:
                    mbta.set_station(new_station)
                    print(f"Station changed to: {new_station}")
                    render_queue.put({
                        "type": "text",
                        "content": MBTA.train_station_to_str(new_station)
                    })
            
        except queue.Empty:
            time.sleep(REFRESH_RATE)
            continue

def render_task():
    display = Display()
    while True:
        try:
            message = render_queue.get(timeout=REFRESH_RATE)
            if message.get("type") == "text":
                display.render_text_content(message["content"])
            if message.get("type") == "mbta":
                display.render_mbta_content(message["content"])
            if message.get("type") == "music":
                display.render_music_content(message["content"])
        except queue.Empty:
            continue


def clock_provider_task():
    while True:
        current_mode = mode_broadcaster.get_status()
        if current_mode == SignMode.CLOCK:
            now = datetime.now()
            time_str = now.strftime("%A, %B %d %Y\n%H:%M:%S")
            render_queue.put({
                "type": "text",
                "content": time_str
            })
        time.sleep(REFRESH_RATE)


def mbta_provider_task():
    while True:
        if mode_broadcaster.get_status() == SignMode.MBTA:
            result = mbta.get_predictions_both_directions()
            print(result)
            render_queue.put({
                "type": "mbta",
                "content": result
            })
            time.sleep(5)
        else:
            time.sleep(REFRESH_RATE)


def music_provider_task():
    spotify = Spotify()
    spotify.setup()
    while True:
        if mode_broadcaster.get_status() == SignMode.MUSIC:
            status, currently_playing = spotify.get_currently_playing()
            print(f"Music status: {status}")
            print(f"Currently playing: {currently_playing}")
            if status == SpotifyResponse.OK:
                if spotify.is_current_song_new(currently_playing):
                    status, img = spotify.get_album_cover(currently_playing)
                    if status == SpotifyResponse.OK:
                        currently_playing.cover.data = img
                        print(f"Album cover fetched for {currently_playing.title} by {currently_playing.artist}")
                    spotify.update_current_song(currently_playing)
                else:
                    currently_playing.cover.data = spotify.get_current_song().cover.data
            elif status == SpotifyResponse.OK_SHOW_CACHED:
                currently_playing = spotify.get_current_song()
            else:
                spotify.clear_current_song()
            render_queue.put({
                "type": "music",
                "content": (status, currently_playing)
            })
            time.sleep(1)
        else:
            time.sleep(REFRESH_RATE)


def web_server_task():
    server = Server(ui_queue, mode_broadcaster, mbta.station_broadcaster)
    server.web_server_task()


def main():
    # Setup
    setup_gpio()

    # Start threads
    ui_thread = threading.Thread(target=ui_task, daemon=True)
    render_thread = threading.Thread(target=render_task, daemon=True)
    clock_thread = threading.Thread(target=clock_provider_task, daemon=True)
    mbta_thread = threading.Thread(target=mbta_provider_task, daemon=True)
    music_thread = threading.Thread(target=music_provider_task, daemon=True)
    web_server_thread = threading.Thread(target=web_server_task, daemon=True)

    ui_thread.start()
    render_thread.start()
    clock_thread.start()
    mbta_thread.start()
    music_thread.start()
    web_server_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
