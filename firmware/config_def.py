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


SCREEN_I2C_SDA = Pin(31)
SCREEN_I2C_SCL = Pin(29)

HX711_GAIN = 64

HX711_CONF = [
    dotdict(
        SPI_ID = 2,  # SPI interface to use
        DOUT = 22,   # Connected to DOUT pin on HX711
        CLK = 24,    # Connected to SCK pin on HX711
        SSCK = 20,   # Dummy pin on chip, not connected
    ),
    dotdict(
        SPI_ID = 3,  # SPI interface to use
        DOUT = 45,   # Connected to DOUT pin on HX711
        CLK = 42,    # Connected to SCK pin on HX711
        SSCK = 15,   # Dummy pin on ESP, not connected
    ),
]



BUTTON_PIN = Pin(16)

VSENSE_PIN = Pin(2)