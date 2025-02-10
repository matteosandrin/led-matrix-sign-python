import os
from pprint import pprint
from underground import SubwayFeed

ROUTE = 'A'
feed = SubwayFeed.get(ROUTE)

pprint(feed.extract_stop_dict())

