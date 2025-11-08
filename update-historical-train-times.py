import pickle
import csv
import logging
import os
import requests
from typing import Any, Dict, List
from main import setup_logging
from providers.mta.types import HistoricalTrainTime, DayType
from providers.mta.mta import get_stop_ids, stations

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
GFTS_URL = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"
GFTS_FILE = f"{CURRENT_DIR}/providers/mta/gtfs_subway.zip"


def downolad_gfts_train_times() -> None:
    logger.info(f"Downloading GTFS zip file to {GFTS_FILE}")
    response = requests.get(GFTS_URL)
    with open(GFTS_FILE, "wb") as f:
        f.write(response.content)
    logger.info(f"Unzipping GTFS zip file to {CURRENT_DIR}/providers/mta/gtfs")
    os.system(f"unzip {GFTS_FILE} -d {CURRENT_DIR}/providers/mta/gtfs")


def convert_historical_train_times() -> Dict[str, List[HistoricalTrainTime]]:
    logger.info("Converting historical train times")

    stop_times = csv.DictReader(
        open(f"{CURRENT_DIR}/providers/mta/gtfs/stop_times.txt"))
    trips = csv.DictReader(open(f"{CURRENT_DIR}/providers/mta/gtfs/trips.txt"))

    result: Dict[str, List[HistoricalTrainTime]] = {}

    stop_times_by_id: Dict[str, List[Any]] = {}
    for stop_time in stop_times:
        stop_id = stop_time["stop_id"][:-1].strip()
        if stop_id not in stop_times_by_id:
            stop_times_by_id[stop_id] = []
        stop_times_by_id[stop_id].append(stop_time)

    trips_by_id: Dict[str, Any] = {}
    for trip in trips:
        trips_by_id[trip["trip_id"]] = trip

    for i, station in enumerate(stations):
        logger.info(f" * {i+1} {station.stop_id} {station.stop_name}")
        stop_ids = get_stop_ids(station)
        for stop_id in stop_ids:
            result[stop_id] = []
            if stop_id not in stop_times_by_id:
                continue
            for stop_time in stop_times_by_id[stop_id]:
                trip = trips_by_id[stop_time["trip_id"]]
                day_type = DayType.WEEKDAY
                if trip["service_id"] == "Saturday":
                    day_type = DayType.SATURDAY
                elif trip["service_id"] == "Sunday":
                    day_type = DayType.SUNDAY
                h, m, s = stop_time["departure_time"].split(":")
                departure_seconds = int(h) * 3600 + int(m) * 60 + int(s)
                train_time = HistoricalTrainTime(
                    route_id=trip["route_id"],
                    direction_id=trip["direction_id"],
                    long_name=trip["trip_headsign"],
                    departure_time=departure_seconds,
                    trip_id=stop_time["trip_id"],
                    day_type=day_type,
                )
                result[stop_id].append(train_time)
    return result


def remove_gtfs_files() -> None:
    logger.info("Removing GTFS files")
    os.system(f"rm -v {GFTS_FILE}")
    os.system(f"rm -vr {CURRENT_DIR}/providers/mta/gtfs")


if __name__ == "__main__":
    setup_logging()
    downolad_gfts_train_times()
    train_times = convert_historical_train_times()
    pickle_file_path = f'{CURRENT_DIR}/providers/mta/historical_train_times.pickle'
    with open(pickle_file_path, 'wb') as f:
        logger.info(f"Writing data to pickle {pickle_file_path}")
        pickle.dump(train_times, f)
    remove_gtfs_files()
