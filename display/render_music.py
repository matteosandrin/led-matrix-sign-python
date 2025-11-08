from typing import Any
from PIL import Image
from providers.music.types import SpotifyResponse, Song
from io import BytesIO
from common import Colors, Fonts
from .animation import TextScrollAnimation
from .types import RenderMessage, Rect


def render_music_content(display: Any, message: RenderMessage.Music) -> None:
    status, song = message.status, message.song

    if status in [SpotifyResponse.OK, SpotifyResponse.OK_SHOW_CACHED,
                  SpotifyResponse.OK_NEW_SONG] and song is not None:

        progress_bar_image = _get_progress_bar_image(display, song)
        display.canvas.SetImage(progress_bar_image, 32,
                                display.SCREEN_HEIGHT - progress_bar_image.height)

        if status == SpotifyResponse.OK_NEW_SONG:
            display.animation_manager.remove_animation("song_title")
            display.animation_manager.remove_animation("song_artist")
            title_and_artist_image = _get_title_and_artist_image(display, song)
            display.canvas.SetImage(title_and_artist_image, 32, 0)
            animations = {}
            if display._get_text_length(
                    song.title, Fonts.SILKSCREEN) > title_and_artist_image.width:
                animations["song_title"] = TextScrollAnimation(
                    Rect(32, 0, title_and_artist_image.width, 8), 10,
                    True, True, song.title, Fonts.SILKSCREEN, Colors.WHITE)
            if display._get_text_length(
                    song.artist, Fonts.SILKSCREEN) > title_and_artist_image.width:
                animations["song_artist"] = TextScrollAnimation(
                    Rect(32, 8, title_and_artist_image.width, 8), 10,
                    True, True, song.artist, Fonts.SILKSCREEN, Colors.WHITE)
            display.animation_manager.add_animations(animations)
        if song.cover.data is not None:
            opened_image = Image.open(
                BytesIO(song.cover.data),
                formats=['JPEG'])
            album_art_image = opened_image.resize((32, 32))
            display.canvas.SetImage(album_art_image, 0, 0)
        display.swap_canvas()

    elif status == SpotifyResponse.EMPTY:
        image = Image.new(
            'RGB', (display.SCREEN_WIDTH, display.SCREEN_HEIGHT), Colors.BLACK)
        draw = display._get_draw_context_antialiased(image)
        draw.text((0, 0), "Nothing is playing",
                  font=display.default_font, fill=Colors.SPOTIFY_GREEN)
        display._update_display(image)
    else:
        image = Image.new(
            'RGB', (display.SCREEN_WIDTH, display.SCREEN_HEIGHT), Colors.BLACK)
        draw = display._get_draw_context_antialiased(image)
        draw.text((0, 0), "Error querying the spotify API",
                  font=display.default_font, fill=Colors.SPOTIFY_GREEN)
        display._update_display(image)


def _get_progress_bar_image(display: Any, song: Song) -> Image.Image:
    image = Image.new('RGB', (display.SCREEN_WIDTH - 32, 8), Colors.BLACK)
    draw = display._get_draw_context_antialiased(image)
    # Draw progress bar
    progress_bar_width = display.SCREEN_WIDTH - 32
    progress = song.progress_ms / song.duration_ms
    current_bar_width = int(progress_bar_width * progress)

    # Draw progress bar background
    draw.rectangle(
        [(0, image.height - 2),
            (image.width, image.height)],
        fill=(255, 255, 255))

    # Draw progress bar fill
    if current_bar_width > 0:
        draw.rectangle(
            [(0, image.height - 2),
                (current_bar_width, image.height)],
            fill=Colors.SPOTIFY_GREEN)

    # Draw time progress
    progress_time = _format_elapsed_time(song.progress_ms // 1000, False)
    time_to_end = _format_elapsed_time(
        (song.duration_ms - song.progress_ms) // 1000, True)

    small_font = Fonts.PICOPIXEL
    # Draw progress time (left side)
    draw.text((1, 0), progress_time,
              font=small_font, fill=Colors.SPOTIFY_GREEN)

    # Draw time to end (right side)
    time_to_end_width = draw.textlength(time_to_end, font=small_font)
    draw.text((image.width - time_to_end_width, 0),
              time_to_end, font=small_font, fill=Colors.SPOTIFY_GREEN)
    return image


def _get_title_and_artist_image(display: Any, song: Song) -> Image.Image:
    image = Image.new('RGB', (display.SCREEN_WIDTH - 32, 24), Colors.BLACK)
    draw = display._get_draw_context_antialiased(image)
    draw.text((0, 0), song.title,
              font=Fonts.SILKSCREEN, fill=Colors.WHITE)
    draw.text((0, 8), song.artist,
              font=Fonts.SILKSCREEN, fill=Colors.WHITE)
    return image

def _format_elapsed_time(seconds: int, is_negative: bool) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        return f"{'-' if is_negative else ''}{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{'-' if is_negative else ''}{minutes:02d}:{seconds:02d}"
