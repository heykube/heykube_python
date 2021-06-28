# HEYKUBE Python Library

Read the Docs: 
https://heykube-python.readthedocs.io/en/latest/index.html

If you need HEYKUBE HW
http://www.heykube.com

## Installing on the Raspberry Pi

```
# Installation
git clone https://github.com/heykube/heykube_python.git

# Optional - install a virtual library
pip3 install virtualenv
virtualenv -p /usr/bin/python3 heykube_env
source heykube_env/bin/activate

# Install the libray
cd heykube_python
pip3 install -e . 
```

In order to BTLE scan to work without sudo, you need to run the following:

```
# clean up BTLE scan with sudo
sudo setcap 'cap_net_raw,cap_net_admin+eip' /usr/bin/hcitool

# Check that it works
sudo getcap /usr/bin/hcitool
/usr/bin/hcitool = cap_net_admin,cap_net_raw+eip
```

## Using the Library

### Run the Command line interface (CLI)
```
cd heykube_python/scripts
./heykube_cli.py
```

### Use the examples
```
cd heykube_python/examples
./patterns_skill.py
```

## Problems with BTLE 
Sometimes the BTLE can stay connected, and HEYKUBE cannot find it

```
# Lists the connected devices
hcitool conn

# example
pi@raspberrypi:~/heykube_python $ hcitool conn
Connections:
        < LE FC:AE:7C:F7:28:F1 handle 64 state 1 lm MASTER

# Running this command disconnects the device (64 is the index after handle)
hcitool ledc 64

# Sometimes you need to reset 
sudo hciconfig hci0 reset
```

