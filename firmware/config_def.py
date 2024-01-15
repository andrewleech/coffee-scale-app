# Copy this file to config.py and edit to change any pinouts.
try:
    from config_def import *
except ImportError:
    pass

from machine import Pin

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def __getattr__(self, key):
        return self[key]

WIFI_SSID = "foob"
WIFI_PASS = "bar"


SCREEN_I2C_ID = 0
SCREEN_I2C_SDA = Pin(31)
SCREEN_I2C_SCL = Pin(29)
SCREEN_PWR = Pin(22)

HX711_GAIN = 64

HX711_CONF = [
    dotdict(
        SPI_ID = 2,  # SPI interface to use
        DOUT = 23,   # Connected to DOUT pin on HX711
        CLK = 24,    # Connected to SCK pin on HX711
        SSCK = 20,   # Dummy pin on chip, not connected
        PWR = 17,
    ),
    dotdict(
        SPI_ID = 3,  # SPI interface to use
        DOUT = 45,   # Connected to DOUT pin on HX711
        CLK = 42,    # Connected to SCK pin on HX711
        SSCK = 15,   # Dummy pin on ESP, not connected
        PWR = 18,
    ),
]

CALIB = 1795.662  # determined by measuring something against reference scale


BUTTON_PIN = Pin(16)
VSENSE_PIN = Pin(2)
PCS_BUTTON_PIN = Pin(6)
PING_BUTTON_PIN = MODE_BUTTON_PIN = Pin(27)
