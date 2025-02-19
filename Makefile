SERVICE_NAME = led-matrix-sign.service

start:
	sudo systemctl start $(SERVICE_NAME)

stop:
	sudo systemctl stop $(SERVICE_NAME)

restart:
	sudo systemctl restart $(SERVICE_NAME)

update:
	stop
	git pull origin master
	start

logs:
	journalctl -u $(SERVICE_NAME) -f

fonts-img:
	python3 fonts-img.py

.PHONY: start stop restart update logs fonts-img
