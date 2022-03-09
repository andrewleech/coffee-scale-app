"""Main file running on the scales ESP32."""
import gc
import time
import bluetooth
import micropython
import uasyncio as asyncio
from art import BATTERY, DOT, GRAM, LOGO, show_digit, show_sprite
from ble_scales import BLEScales
from filtering import KalmanFilter
from hx711 import HX711
from machine import ADC, I2C, Pin, SPI
from ssd1306 import SSD1306_I2C
try:
    from config import *
except ImportError:
    from config_def import *

print("import finished")
micropython.alloc_emergency_exception_buf(160)

i2c = I2C(
    0,
    scl=Pin(SCREEN_I2C_SCL), 
    sda=Pin(SCREEN_I2C_SDA)
)
print("i2c")
screen = SSD1306_I2C(width=128, height=32, i2c=i2c)
screen.fill(0)
show_sprite(screen, LOGO, 51, 1)
screen.show()
print("screen")

ble = bluetooth.BLE()
print('bt loaded')
scales = BLEScales(ble)
kf = [KalmanFilter(0.03, q=0.1)] * len(HX711_CONF)
button_pin = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
vsense_pin = ADC(Pin(VSENSE_PIN))
try:
    vsense_pin.atten(ADC.ATTN_11DB)
except AttributeError:
    # Only exists on esp32
    pass
bat_percent = 0

hx = []


# def get_weight():
#     return sum([_hx.get_units() for _hx in hx])


async def hx_configure():
    global hx, kf, filtered_weight

    print ("Configuring load cell(s)")
    for i, hx_conf in enumerate(HX711_CONF):
        _hx = HX711(pd_sck=hx_conf.CLK, dout=hx_conf.DOUT, gain=HX711_GAIN, callback=kf[i].update_estimate)
        _hx.set_time_constant(0)
        _hx.set_scale(1544.667)
        hx.append(
            _hx
        )

    await asyncio.gather(*[asyncio.create_task(_hx.tare()) for _hx in hx])

    filtered_weight = 0


def tare_callback(pin):
    global hx, kf
    print("tare")
    asyncio.create_task(asyncio.gather(*[_hx.tare() for _hx in hx]))
    for _kf in kf:
        _kf.last_estimate = 0.0


def adc_to_percent(v_adc):
    if v_adc > 2399:  # 4.1-4.2 = 94-100%
        val = int(0.10169492 * v_adc - 149.966)
        return val if val <= 100 else 100
    if v_adc > 2341:  # 4.0-4.1 = 83-94%
        return int(0.18965517 * v_adc - 360.983)
    if v_adc > 2282:  # 3.9-4.0 = 72-83%
        return int(0.18644068 * v_adc - 353.458)
    if v_adc > 2224:  # 3.8-3.9 = 59-72%
        return int(0.22413793 * v_adc - 439.483)
    if v_adc > 2165:  # 3.7-3.8 = 50-59%
        return int(0.15254237 * v_adc - 280.254)
    if v_adc > 2107:  # 3.6-3.7 = 33-50%
        return int(0.29310345 * v_adc - 584.569)
    if v_adc > 2048:  # 3.5-3.6 = 15-33%
        return int(0.30508475 * v_adc - 609.814)
    if v_adc > 1990:  # 3.4-3.5 = 6-15%
        return int(0.15517241 * v_adc - 302.793)
    if v_adc >= 1931:  # 3.3-3.4 = 0-6%
        return int(0.10169492 * v_adc - 196.373)
    return 0


def check_battery():
    global bat_percent
    battery_sum = 0
    for i in range(10):
        battery_sum += vsense_pin.value()
    bat_percent = adc_to_percent(battery_sum / 10)
    scales.set_battery_level(bat_percent)


def measure():
    weight = sum([_kf.last_estimate for _kf in kf])
    filtered_weight = round(weight / 0.05) * 0.05
    scales.set_weight(filtered_weight, notify=True)


async def main():
    global filtered_weight, scales, button_pin, hx, kf

    await hx_configure()

    # uncomment next 2 lines to get a load cell reading for calibration (in the console/serial)
    # while True:
    #    print(hx.read_average(times=100))

    check_battery()

    print("Running...")
    asyncio.create_task(display_weight())

    button_pin.irq(trigger=Pin.IRQ_FALLING, handler=tare_callback)

    last = 0
    while True:
        await asyncio.sleep_ms(80)
        # start = time.ticks_ms()
        # weight = get_weight()
        # taken = time.ticks_diff(time.ticks_ms(), start)
        # print(f"weight: {taken}")
        # now = time.ticks_ms()
        # if time.ticks_diff(now, last) > 100:
        #     last = now
        measure()
        gc.collect()


async def display_weight():
    global filtered_weight, bat_percent
    while True:
        await asyncio.sleep_ms(80)
        screen.fill(0)
        string = '{:.2f}'.format(filtered_weight)
        if len(string) > 6:
            string = '{:.1f}'.format(filtered_weight)
        if string == '-0.00':
            string = '0.00'
        position = 118
        for char in reversed(string):
            if position < 0:
                break
            if char == '-':
                char = 'MINUS'
            if char == '.':
                position -= 7
                if position < 0:
                    break
                show_sprite(screen, DOT, position, 27)
            else:
                position -= 22
                if position < 0:
                    break
                show_digit(screen, char, position, 1)
        show_sprite(screen, GRAM, 117, 16)
        if bat_percent <= 20:
            show_sprite(screen, BATTERY, 117, 1)
        screen.show()


def run():
    asyncio.run(main())


run()
