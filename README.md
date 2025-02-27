# LED Matrix Sign

[![](img/led-matrix-sign.jpg)](img/led-matrix-sign.jpg)

## Setup

Install Python dependencies.

```bash
pip install -r requirements.txt
```

Install the Adafruit RGB Matrix library.

```bash
curl https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/refs/heads/main/rgb-matrix.sh > rgb-matrix.sh
sudo bash rgb-matrix.sh
```

Turn off the Raspberry Pi's integrated audio card.

```bash
sudo nano /boot/firmware/config.txt # set "dtparam=audio=off"
sudo nano /etc/modprobe.d/alsa-blacklist.conf # add "blacklist snd_bcm2835"
```

## Run

Sudo is required in order to access hardware registers. Performance will be much
worse without it.

```bash
sudo python3 main.py
```

## Run at system startup

First, edit the `led-matrix-sign.service` file to set the correct path to the
Python script. Then, run the following commands:

```bash
sudo cp led-matrix-sign.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/led-matrix-sign.service
sudo systemctl daemon-reload
sudo systemctl enable led-matrix-sign.service
sudo systemctl start led-matrix-sign.service
# to check logs
sudo journalctl -u led-matrix-sign.service
```

# Shutdown button

Long press the shutdown button for 3 seconds to power off the Raspberry Pi. In
order to setup this functionality, the `daemon` user needs to be allowed to
shutdown the system without root privileges. To accomplish this, run the
following command:

```bash
sudo visudo -f /etc/sudoers.d/shutdown
```

Add the following line to the file:

```
daemon ALL=(ALL) NOPASSWD: /sbin/shutdown
```
