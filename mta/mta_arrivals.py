import os
import csv
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from underground import SubwayFeed

@dataclass
class Stop:
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float
    parent_station: Optional[str]

@dataclass
class Route:
    route_id: str
    short_name: str
    long_name: str
    desc: str
    color: str

class MTAService:
    def __init__(self):
        self.stops: Dict[str, Stop] = {}
        self.routes: Dict[str, Route] = {}
        self._load_static_data()

    def _load_static_data(self):
        """Load GTFS static data for stops and routes"""
        # Load stops
        with open('gtfs_subway/stops.txt', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['location_type'] == '1':  # Parent stations only
                    self.stops[row['stop_id']] = Stop(
                        stop_id=row['stop_id'],
                        stop_name=row['stop_name'],
                        stop_lat=float(row['stop_lat']),
                        stop_lon=float(row['stop_lon']),
                        parent_station=row['parent_station']
                    )

        # Load routes
        with open('gtfs_subway/routes.txt', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.routes[row['route_id']] = Route(
                    route_id=row['route_id'],
                    short_name=row['route_short_name'],
                    long_name=row['route_long_name'],
                    desc=row['route_desc'],
                    color=row['route_color']
                )

    def get_arrivals(self, station_id: str, route_id: str) -> List[Tuple[str, datetime]]:
        """Get upcoming arrivals for a specific station and route"""
        if station_id not in self.stops:
            raise ValueError(f"Invalid station ID: {station_id}")
        if route_id not in self.routes:
            raise ValueError(f"Invalid route ID: {route_id}")

        # Get the feed for the specified route
        feed = SubwayFeed.get(self.routes[route_id].short_name)
        
        # Extract arrival times for the station
        arrivals = []
        stop_dict = feed.extract_stop_dict()

        # Check both north and south platforms
        platform_ids = [f"{station_id}N", f"{station_id}S"]
        
        for platform_id in platform_ids:
            if platform_id in stop_dict:
                for arrival in stop_dict[platform_id]:
                    direction = "Northbound" if platform_id.endswith('N') else "Southbound"
                    arrivals.append((direction, arrival['arrival']))

        # Sort by arrival time
        return sorted(arrivals, key=lambda x: x[1])

    def find_station_by_name(self, name: str) -> List[Stop]:
        """Find stations by partial name match"""
        name = name.lower()
        return [stop for stop in self.stops.values() 
                if name in stop.stop_name.lower()]

    def find_route_by_name(self, name: str) -> List[Route]:
        """Find routes by name/id"""
        name = name.lower()
        return [route for route in self.routes.values() 
                if name in route.short_name.lower() or name in route.long_name.lower()]

def main():
    mta = MTAService()

    # Example usage
    station_name = input("Enter station name: ")
    route_name = input("Enter route (train line): ")

    # Find matching stations
    stations = mta.find_station_by_name(station_name)
    if not stations:
        print(f"No stations found matching '{station_name}'")
        return

    # Find matching routes
    routes = mta.find_route_by_name(route_name)
    if not routes:
        print(f"No routes found matching '{route_name}'")
        return

    # Print arrivals for each matching station/route combination
    for station in stations:
        print(station)
        for route in routes:
            print(route)
            print(f"\nArrivals for {route.short_name} train at {station.stop_name}:")
            try:
                arrivals = mta.get_arrivals(station.stop_id, route.route_id)
                if not arrivals:
                    print("No upcoming arrivals found")
                else:
                    for direction, time in arrivals:
                        print(f"{direction}: {time.strftime('%I:%M %p')}")
            except Exception as e:
                print(f"Error getting arrivals: {e}")

if __name__ == "__main__":
    main() 