from lxml import html
import json
import os
import requests

current_dir = os.path.dirname(os.path.abspath(__file__))

lines = [
    "Red",
    "Orange",
    "Green",
    "Blue",
]

response = requests.get("https://www.mbta.com/stops/subway")
response.raise_for_status()
tree = html.fromstring(response.text)

stations = {}

for line in lines:
    line_div = tree.xpath(f'//div[@id="stops-{line}"]')[0]
    stop_links = line_div.xpath('.//a[contains(@class, "stop-btn")]')
    for stop_link in stop_links:
        stop_id = stop_link.get('href').split('/')[-1]
        stop_name = stop_link.get('data-name')
        if stop_id not in stations:
            stations[stop_id] = {
                "name": stop_name,
                "routes": [],
            }
        stations[stop_id]["routes"].append(line)

stations_list = []
for stop_id, stop in stations.items():
    stations_list.append({
        "stop_id": stop_id,
        "stop_name": stop["name"],
        "routes": sorted(list(set(stop["routes"]))),
    })

with open(os.path.join(current_dir, 'stations.json'), 'w') as f:
    json.dump(stations_list, f, indent=4)
