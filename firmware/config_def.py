# Copy this file to config.py and edit to change any pinouts.
try:
    from config_def import *
except ImportError:
    pass

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def __getattr__(self, key):
        return self[key]



SCREEN_I2C_SDA = 21
SCREEN_I2C_SCL = 22

HX711_GAIN = 64

HX711_CONF = [
    dotdict(
        SPI_ID = 2,  # SPI interface to use
        DOUT = 32,   # Connected to DOUT pin on HX711
        CLK = 33,    # Connected to SCK pin on HX711
        SSCK = 25,   # Dummy pin on ESP, not connected
    ),
    dotdict(
        SPI_ID = 1,  # SPI interface to use
        DOUT = 12,   # Connected to DOUT pin on HX711
        CLK = 13,    # Connected to SCK pin on HX711
        SSCK = 14,   # Dummy pin on ESP, not connected
    ),
]



BUTTON_PIN = 0

VSENSE_PIN = 34