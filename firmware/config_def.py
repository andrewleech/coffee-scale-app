# Copy this file to config.py and edit to change any pinouts.

from machine import Pin

try:
    from config_def import *
except ImportError:
    pass

SCREEN_I2C_SDA = 21  # GPIO
SCREEN_I2C_SCL = 22  # GPIO

HX711_GAIN = 64
HX711_0_SPI_ID = 1  # SPI interface to use
HX711_0_DOUT = 12   # Connected to DOUT pin on HX711
HX711_0_CLK = 13    # Connected to SCK pin on HX711
HX711_0_SSCK = 14   # Dummy pin on ESP, not connected

BUTTON_PIN = 0

VSENSE_PIN = 34