import random
import socket
import config
import argparse
import providers.mbta as mbta
import providers.mta as mta
import queue
import threading
import time
import os
import logging
from common import SignMode, UIMessageType, ClockType, get_next_mode
from common.broadcaster import StatusBroadcaster
from common.button import Button
from datetime import datetime
from display import Display
from pprint import pprint
from providers.music import Spotify
from providers.music.types import SpotifyResponse
from providers.widget import WidgetManager, ClockWidget, WeatherWidget
from providers.game_of_life import GameOfLife, GameOfLifePatterns
from server import Server
from display.types import RenderMessage, Rect

# Constants
BUTTON_PIN = 25
REFRESH_RATE = 0.1  # seconds
DEFAULT_SIGN_MODE = SignMode.MBTA

# Global queues
ui_queue = queue.Queue(maxsize=16)
render_queue = queue.Queue(maxsize=32)

mode_broadcaster = StatusBroadcaster()

system_threads = []
user_threads = []

mbta_client = mbta.MBTA(config.MBTA_API_KEY)
mta_client = mta.MTA(config.MTA_API_KEY)

logger = logging.getLogger("led-matrix-sign")

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt="%Y-%m-%dT%H:%M:%S%z")
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if not config.EMULATE_RGB_MATRIX:
        try:
            from systemd import journal
            journal_handler = journal.JournalHandler()
            journal_handler.setFormatter(formatter)
            logger.addHandler(journal_handler)
        except ImportError:
            logging.warning("Could not import systemd journal handler - logging to console only")


def parse_args():
    parser = argparse.ArgumentParser(
        description='LED Matrix Display Controller')
    parser.add_argument(
        '--mode', type=str, choices=[mode.name for mode in SignMode],
        help='Set the default sign mode')
    parser.add_argument(
        '--mta-fake-data', action='store_true',
        help='Use fake MTA data')
    return parser.parse_args()


def ui_task():
    while True:
        try:
            message = ui_queue.get(timeout=REFRESH_RATE)

            if message["type"] == UIMessageType.MODE_SHIFT:
                next_mode = get_next_mode(mode_broadcaster.get_status())
                render_queue.put(RenderMessage.Clear())
                mode_broadcaster.set_status(next_mode)
                logger.info(f"Mode changed to: {next_mode}")
            elif message["type"] == UIMessageType.MODE_CHANGE:
                # Direct mode change
                new_mode = message.get("mode")
                if new_mode in SignMode:
                    render_queue.put(RenderMessage.Clear())
                    mode_broadcaster.set_status(new_mode)
                    logger.info(f"Mode changed to: {new_mode}")
            elif message["type"] == UIMessageType.MBTA_CHANGE_STATION:
                new_station = message.get("station")
                if mbta.station_by_id(new_station) is not None:
                    mbta_client.set_station(new_station)
                    logger.info(f"Station changed to: {new_station}")
                    render_queue.put(RenderMessage.Clear())
                    render_queue.put(RenderMessage.Text(text=mbta.train_station_to_str(new_station)))
            elif message["type"] == UIMessageType.MBTA_TEST_BANNER:
                render_queue.put(RenderMessage.Clear())
                render_queue.put(RenderMessage.MBTABanner(lines=["Alewife train", "is now arriving."]))
            elif message["type"] == UIMessageType.MTA_CHANGE_STATION:
                new_station = message.get("station")
                mta_client.set_current_station(new_station)
                logger.info(f"Station changed to: {new_station}")
                render_queue.put(RenderMessage.Clear())
                render_queue.put(
                    RenderMessage.MTAStationBanner(
                        station_name=mta.train_station_to_str(new_station),
                        routes=mta.sort_routes(
                            mta.station_by_id(new_station).routes)))
            elif message["type"] == UIMessageType.TEST:
                new_message = message.get("content")
                if new_message == "mta_all_images":
                    render_queue.put(RenderMessage.MTATestImages())
                else:
                    render_queue.put(RenderMessage.Text(text=new_message if new_message is not None else ""))
            elif message["type"] == UIMessageType.MTA_ALERT:
                render_queue.put(RenderMessage.MTAAlert(text=message.get("content")))
            elif message["type"] == UIMessageType.SHUTDOWN:
                mode_broadcaster.set_status(SignMode.TEST)
                if not config.EMULATE_RGB_MATRIX:
                    logger.info("Shutting down")
                    render_queue.put(RenderMessage.Clear())
                    render_queue.put(RenderMessage.Text(text="Shutting down..."))
                    time.sleep(1)
                    os.system("sudo shutdown -h now")
                else:
                    logger.info("Not shutting down (emulated)")

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
            render_queue.put(RenderMessage.Clock(
                clock_type=ClockType.MTA,
                time=datetime.now()
            ))
        time.sleep(REFRESH_RATE)


def mbta_provider_task():
    while True:
        if mode_broadcaster.get_status() == SignMode.MBTA:
            status, predictions = mbta_client.get_predictions_both_directions()
            render_queue.put(RenderMessage.MBTA(
                status=status,
                predictions=predictions
            ))
            logger.info(status)
            logger.info(predictions)
            if status == mbta.PredictionStatus.OK:
                arr_prediction = mbta_client.find_prediction_with_arriving_banner(predictions)
                if arr_prediction is not None:
                    logger.info("showing arriving banner")
                    render_queue.put(RenderMessage.MBTABanner(
                        lines=mbta_client.get_arriving_banner(arr_prediction)
                    ))
                    # in total this banner is displayed for 3+5 seconds
                    time.sleep(3)
                mbta_client.update_latest_predictions(predictions, [0, 1])
            time.sleep(5)
        else:
            time.sleep(REFRESH_RATE)


def mta_provider_task():
    last_alert_time = time.time()
    alert_messages = mta.AlertMessages()
    if config.MTA_FAKE_DATA:
        logger.info("Using MTA historical data")
        mta_client.load_historical_data()
    # show the station banner for 2 seconds initially
    ui_queue.put({
        "type": UIMessageType.MTA_CHANGE_STATION,
        "station": mta_client.get_current_station()
    })
    time.sleep(2)
    while True:
        if mode_broadcaster.get_status() == SignMode.MTA:
            station = mta_client.get_current_station()
            if station is not None:
                predictions = []
                if not config.MTA_FAKE_DATA:
                    predictions = mta_client.get_predictions(station)
                else:
                    predictions = mta_client.get_fake_predictions(station)
                if predictions is not None:
                    if len(predictions) < 2:
                        mta.print_predictions(predictions)
                        render_queue.put(RenderMessage.MTA(predictions=predictions))
                    else:
                        second_train = mta.get_second_train(
                            predictions, mta_client.last_second_train)
                        if second_train is not None:
                            mta.print_predictions([predictions[0], second_train])
                            render_queue.put(RenderMessage.MTA(
                                predictions=[predictions[0], second_train]
                            ))
                            mta_client.last_second_train = second_train
                else:
                    logger.info("No predictions")
                if time.time() - last_alert_time > 60 * 5:
                    last_alert_time = time.time()
                    render_queue.put(RenderMessage.MTAAlert(text=alert_messages.next()))
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
            logger.info(status)
            logger.info(currently_playing)
            if status == SpotifyResponse.OK_NEW_SONG:
                img_status, img = spotify.get_album_cover(currently_playing)
                if img_status == SpotifyResponse.OK:
                    currently_playing.cover.data = img
                    logger.info(
                        f"Album cover fetched for {currently_playing.title} by {currently_playing.artist}")
                spotify.update_current_song(currently_playing)
            elif status == SpotifyResponse.OK:
                pass
            elif status == SpotifyResponse.OK_SHOW_CACHED:
                currently_playing = spotify.get_current_song()
            else:
                spotify.clear_current_song()
            render_queue.put(RenderMessage.Music(
                status=status,
                song=currently_playing
            ))
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


def game_of_life_provider_task():
    # Initialize Game of Life with screen dimensions
    # Use smaller grid for better visibility on LED matrix
    grid_width = 160  # Slightly smaller than screen width for better cell visibility
    grid_height = 32  # Smaller grid height
    
    game = GameOfLife(grid_width, grid_height, density=0.3)
    
    # Add some interesting patterns occasionally
    last_pattern_time = time.time()
    pattern_interval = 60  # Add new pattern every 60 seconds
    
    while True:
        if mode_broadcaster.get_status() == SignMode.GAME_OF_LIFE:
            # Step the game forward
            changed = game.step()
            
            # Send current state to display
            render_queue.put(RenderMessage.GameOfLife(
                grid=game.get_grid(),
                generation=game.get_generation()
            ))
            
            # Reset if game becomes stable or empty
            if game.is_stable_or_empty():
                logger.info(f"Game of Life: Resetting after {game.get_generation()} generations")
                game.reset()
                # Occasionally add interesting patterns instead of random
                if time.time() - last_pattern_time > pattern_interval:
                    patterns = [
                        GameOfLifePatterns.glider(),
                        GameOfLifePatterns.r_pentomino(),
                        GameOfLifePatterns.toad(),
                        GameOfLifePatterns.beacon()
                    ]
                    pattern = random.choice(patterns)
                    # Add pattern at random location
                    x_offset = random.randint(0, grid_width - 10)
                    y_offset = random.randint(0, grid_height - 10)
                    game.add_pattern(pattern, x_offset, y_offset)
                    last_pattern_time = time.time()
                    logger.info(f"Game of Life: Added pattern at ({x_offset}, {y_offset})")
            
            time.sleep(0.3)  # Update rate for Game of Life (about 3 FPS)
        else:
            time.sleep(REFRESH_RATE)

def wait_for_network_connection():
    logger.info("Waiting for network connection...")
    connected = False
    start_time = time.time()
    timeout = 30
    
    while not connected:
        if time.time() - start_time > timeout:
            logger.error("Network connection timed out.")
            return False
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            connected = True
            logger.info("Network connection established.")
        except (socket.timeout, socket.error):
            logger.warning("Network not available yet, retrying in 5 seconds...")
            time.sleep(1)
    return True

def setup_network():
    render_queue.put(RenderMessage.Text(text="Waiting for network..."))

    if wait_for_network_connection():
        return True
    else:
        render_queue.put(RenderMessage.Text(text="Network connection timed out."))
        return False


def startup_animation():
    # render the startup animation and wait for it to finish
    render_queue.put(RenderMessage.Clear())
    render_queue.put(RenderMessage.MTAStartup())
    time.sleep(4.5)
    render_queue.put(RenderMessage.Clear())


def main():
    setup_logging()
    args = parse_args()
    initial_mode = DEFAULT_SIGN_MODE
    if hasattr(config, 'DEFAULT_SIGN_MODE'):
        initial_mode = config.DEFAULT_SIGN_MODE
    if args.mode:
        initial_mode = SignMode[args.mode]
    if args.mta_fake_data:
        config.MTA_FAKE_DATA = True
    logger.info(f"Initial mode: {initial_mode}")
    mode_broadcaster.set_status(initial_mode)

    button_handler = None
    if not config.EMULATE_RGB_MATRIX:
        button_handler = Button(
            BUTTON_PIN, short_press_callback=lambda: ui_queue.put(
                {"type": UIMessageType.MODE_SHIFT}),
            long_press_callback=lambda: ui_queue.put(
                {"type": UIMessageType.SHUTDOWN}),
            long_press_duration=3.0)

    system_threads = [
        threading.Thread(target=ui_task, daemon=True),
        threading.Thread(target=render_task, daemon=True),
        threading.Thread(target=web_server_task, daemon=True)
    ]
    user_threads = [
        threading.Thread(target=clock_provider_task, daemon=True),
        threading.Thread(target=mbta_provider_task, daemon=True),
        threading.Thread(target=music_provider_task, daemon=True),
        threading.Thread(target=widget_provider_task, daemon=True),
        threading.Thread(target=mta_provider_task, daemon=True),
        threading.Thread(target=game_of_life_provider_task, daemon=True),
    ]
    for thread in system_threads:
        thread.start()
    if not setup_network():
        mode_broadcaster.set_status(SignMode.CLOCK)
    startup_animation()
    for thread in user_threads:
        thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if button_handler is not None:
            button_handler.cleanup()


if __name__ == "__main__":
    main()
