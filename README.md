# LED Matrix Sign

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
