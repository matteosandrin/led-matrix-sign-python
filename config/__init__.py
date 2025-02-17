try:
    from .config import *
except ImportError:
    print("ERROR: Config file not found. Please create a config/config.py file.")
    print("       Start by copying config/config.example.py to config/config.py")
    exit(1)