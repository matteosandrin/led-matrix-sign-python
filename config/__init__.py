try:
    from .config import *
except ImportError as e:
    print("ERROR: Config file not found. Please create a config/config.py file.")
    print("       Start by copying config/config.example.py to config/config.py")
    print(e)
    exit(1)