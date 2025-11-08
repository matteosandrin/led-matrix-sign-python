from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SpotifyResponse(Enum):
    OK = "ok"
    ERROR = "error"
    EMPTY = "empty"
    OK_SHOW_CACHED = "ok_show_cached"
    OK_NEW_SONG = "ok_new_song"


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
