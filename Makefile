SERVICE_NAME = led-matrix-sign.service

start:
	sudo systemctl start $(SERVICE_NAME)

stop:
	sudo systemctl stop $(SERVICE_NAME)

restart:
	sudo systemctl restart $(SERVICE_NAME)

update:
	make stop
	git pull origin master
	make start

logs:
	journalctl -u $(SERVICE_NAME) -f -b --output=cat -xe

update-font-images:
	python3 update-font-images.py

.PHONY: start stop restart update logs fonts-img
