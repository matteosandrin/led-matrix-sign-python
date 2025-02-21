import base64
import json
import time
from typing import Optional, Dict, Any
import requests
from dataclasses import dataclass, field

SPOTIFY_REFRESH_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
SPOTIFY_TOKEN_REFRESH_RATE = 30 * 60 * 1000  # 30 minutes in milliseconds


@dataclass
class AlbumCover:
    url: str = ""
    width: int = 0
    height: int = 0
    data: Optional[bytes] = None


@dataclass
class Song:
    artist: str = ""
    title: str = ""
    duration_ms: int = 0
    progress_ms: int = 0
    timestamp_ms: int = 0
    cover: AlbumCover = field(default_factory=AlbumCover)


class SpotifyResponse:
    OK = "ok"
    ERROR = "error"
    EMPTY = "empty"
    OK_SHOW_CACHED = "ok_show_cached"
    OK_NEW_SONG = "ok_new_song"


class Spotify:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self.access_token = ""
        self.last_refresh_time = 0
        self.current_song = Song()
        self.session = requests.Session()
        self.secrets = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token
        }

    def setup(self):
        self.refresh_token()
        self.clear_current_song()

    def get_refresh_bearer_token(self) -> str:
        bearer = f"{self.secrets['client_id']}:{self.secrets['client_secret']}"
        bearer_bytes = bearer.encode('ascii')
        base64_bytes = base64.b64encode(bearer_bytes)
        return f"Basic {base64_bytes.decode('ascii')}"

    def get_api_bearer_token(self) -> str:
        return f"Bearer {self.access_token}"

    def refresh_token(self) -> str:
        status = self.fetch_refresh_token()
        if status != SpotifyResponse.OK:
            print(f"Failed to refresh spotify token: {status}")
        self.last_refresh_time = int(time.time() * 1000)
        return status

    def fetch_refresh_token(self) -> str:
        headers = {
            "Authorization": self.get_refresh_bearer_token(),
            "content-type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.secrets["refresh_token"]
        }

        try:
            response = self.session.post(
                SPOTIFY_REFRESH_TOKEN_URL, headers=headers, data=data)
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access_token"]
            return SpotifyResponse.OK
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return SpotifyResponse.ERROR

    def get_currently_playing(self) -> tuple[str, Optional[Song]]:
        result = Song()
        result.timestamp_ms = int(time.time() * 1000)

        status = self.fetch_currently_playing()
        if status == SpotifyResponse.EMPTY and self.current_song.timestamp_ms > 0:
            return SpotifyResponse.OK_SHOW_CACHED, self.current_song
        if status != SpotifyResponse.OK:
            return status, None

        data = self.current_data
        if not data:
            return SpotifyResponse.ERROR, None

        result.title = data["item"]["name"]
        result.artist = self.format_artists(data)
        result.duration_ms = data["item"]["duration_ms"]
        result.progress_ms = data["progress_ms"]
        result.cover = self.format_album_cover(data)
        if self.is_current_song_new(result):
            return SpotifyResponse.OK_NEW_SONG, result
        return SpotifyResponse.OK, result

    def format_artists(self, data: Dict[str, Any]) -> str:
        artists = data["item"]["artists"]
        if len(artists) > 1:
            return ", ".join(artist["name"] for artist in artists)
        return artists[0]["name"]

    def format_album_cover(self, data: Dict[str, Any]) -> AlbumCover:
        images = data["item"]["album"]["images"]
        if not images:
            return AlbumCover()

        smallest_img = min(images, key=lambda x: x["width"])
        cover = AlbumCover()
        cover.url = smallest_img["url"]
        cover.width = smallest_img["width"]
        cover.height = smallest_img["height"]
        return cover

    def fetch_currently_playing(self) -> str:
        self.check_refresh_token()

        headers = {"Authorization": self.get_api_bearer_token()}

        try:
            response = self.session.get(
                SPOTIFY_CURRENTLY_PLAYING_URL, headers=headers)
            if response.status_code == 204:
                return SpotifyResponse.EMPTY

            response.raise_for_status()
            self.current_data = response.json()
            return SpotifyResponse.OK
        except Exception as e:
            print(f"Error fetching currently playing: {e}")
            return SpotifyResponse.ERROR

    def get_album_cover(self, currently_playing: Song) -> tuple[str,
                                                                Optional[bytes]]:
        return self.fetch_album_cover(currently_playing.cover.url)

    def fetch_album_cover(self, url: str) -> tuple[str, Optional[bytes]]:
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return SpotifyResponse.OK, response.content
        except Exception as e:
            print(f"Error fetching album cover: {e}")
            return SpotifyResponse.ERROR, None

    def check_refresh_token(self):
        current_time = int(time.time() * 1000)
        if current_time - self.last_refresh_time > SPOTIFY_TOKEN_REFRESH_RATE:
            print("refreshing spotify token after 30min")
            self.refresh_token()

    def update_current_song(self, src: Song):
        self.current_song = src
        self.current_song.progress_ms = 0

    def clear_current_song(self):
        self.current_song = None

    def is_current_song_new(self, cmp: Song) -> bool:
        if self.current_song is None:
            return True
        return (cmp.artist != self.current_song.artist or
                cmp.title != self.current_song.title)

    def get_current_song(self) -> Song:
        return self.current_song
