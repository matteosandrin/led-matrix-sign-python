SERVICE_NAME = led-matrix-display.service

start:
	sudo systemctl start $(SERVICE_NAME)

stop:
	sudo systemctl stop $(SERVICE_NAME)

restart:
	sudo systemctl restart $(SERVICE_NAME)

logs:
	journalctl -u $(SERVICE_NAME) -f

fonts-img:
	python3 fonts-img.py

.PHONY: start stop restart logs fonts-img
