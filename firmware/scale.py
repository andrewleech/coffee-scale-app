"""Main file running on the scales ESP32."""
import gc
import time
import network
import bluetooth
import micropython
import uasyncio as asyncio
from art import BATTERY, DOT, GRAM, LOGO, show_digit, show_sprite
from ble_scales import BLEScales
from hx711 import HX711
from machine import ADC, I2C, Pin #, DEEPSLEEP
from ssd1306 import SSD1306_I2C
try:
    from config import *
except ImportError:
    from config_def import *

try:
    from typing import List, Tuple
except:
    pass

import net

print("import finished")
micropython.alloc_emergency_exception_buf(160)

i2c = I2C(
    SCREEN_I2C_ID,
    scl=Pin(SCREEN_I2C_SCL),
    sda=Pin(SCREEN_I2C_SDA)
)
print("i2c")
SCREEN_PWR = Pin(SCREEN_PWR, mode=Pin.OUT)
SCREEN_PWR.value(1)
time.sleep_ms(100)

screen = SSD1306_I2C(width=128, height=32, i2c=i2c)
screen.fill(0)
show_sprite(screen, LOGO, 51, 1)
screen.show()
print("screen")

button_pin = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
vsense_pin = ADC(Pin(VSENSE_PIN))
pcs_button = Pin(PCS_BUTTON_PIN, Pin.IN)
mode_pin = Pin(PING_BUTTON_PIN, Pin.IN)
mode_pin_ignore = False
try:
    vsense_pin.atten(ADC.ATTN_11DB)
except AttributeError:
    # Only exists on esp32
    pass
bat_percent = 0

active = time.ticks_ms()
idle = False
filtered_weight = 0
hx: List[Tuple[HX711, Pin]] = []


# POWER_ON_PIN.irq(trigger=Pin.IRQ_RISING, wake=DEEPSLEEP)

ble = bluetooth.BLE()
print('bt loaded')
scales = BLEScales(ble)


async def hx_configure():
    global hx, kf, filtered_weight

    print ("Configuring load cell(s)")
    for i, hx_conf in enumerate(HX711_CONF):
        if _hx_pwr := hx_conf.get("PWR", None):
            _hx_pwr = Pin(_hx_pwr, mode=Pin.OUT)
            _hx_pwr.value(1)
            time.sleep(0.25)

        _hx = HX711(pd_sck=hx_conf.CLK, dout=hx_conf.DOUT, gain=HX711_GAIN)
        _hx.set_scale(CALIB)
        _hx.tare()
        hx.append(
            (_hx, _hx_pwr)
        )

    filtered_weight = 0
    await tare()


async def tare():
    global active
    active = time.ticks_ms()
    await asyncio.gather(*[_hx.tare() for _hx, _ in hx])


async def get_weight():
    val = 0
    for _hx, _ in hx:
        val += await _hx.get_units()
    return val

def tare_callback(pin):
    global hx, kf
    print("tare")
    asyncio.create_task(tare())


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
        battery_sum += vsense_pin.read_u16()
    bat_percent = adc_to_percent(battery_sum / 10)
    print("bat_percent", bat_percent)
    scales.set_battery_level(bat_percent)


async def measure():
    global filtered_weight, active, scales

    weight = await get_weight()
    # filtered_weight = round(weight / 0.05) * 0.05
    if abs(filtered_weight - weight) > 2:
        active = time.ticks_ms()
    filtered_weight = weight
    scales.set_weight(filtered_weight, notify=True)


async def main():
    global filtered_weight, button_pin, hx, kf, scales, active, idle

    await hx_configure()

    # uncomment next 2 lines to get a load cell reading for calibration (in the console/serial)
    # while True:
    #    print(hx.read_average(times=100))

    check_battery()

    print("Running...")

    button_pin.irq(trigger=Pin.IRQ_FALLING, handler=tare_callback)

    # asyncio.create_task(net.do_connect())

    button_hold = 0
    ping = 0
    # last = 0
    while True:
        gc.collect()
        await asyncio.sleep_ms(40)
        # start = time.ticks_ms()
        # weight = get_weight()
        # taken = time.ticks_diff(time.ticks_ms(), start)
        # print(f"weight: {taken}")
        # now = time.ticks_ms()
        # if time.ticks_diff(now, last) > 100:
        #     last = now

        await measure()

        if not button_pin.value():
            button_hold += 1
        else:
            button_hold = 0

        if button_hold >= 25:
            if button_hold == 25:
                display_ip()
        else:
            display_weight()

        if time.ticks_diff(time.ticks_ms(), active) < 120000:
            if idle:
                idle = False
                print("Not idle")
            ping -= 1
            if ping <= 0:
                ping = 10
                asyncio.create_task(scale_keepalive())
        else:
            if not idle:
                idle = True
                print("Idle")


async def scale_keepalive():
    global mode_pin_ignore
    try:
        mode_pin_ignore = True
        mode_pin.init(mode=Pin.OUT, value=0)
        await asyncio.sleep_ms(10)
        mode_pin.init(mode=Pin.IN)
    finally:
        mode_pin_ignore = False


def display_ip():
    screen.fill(0)
    IP_ADDRESS = network.WLAN(network.STA_IF).ifconfig()[0]
    print(IP_ADDRESS)
    screen.text(IP_ADDRESS, 3, 12)

    screen.show()


def display_weight():
    global filtered_weight, bat_percent
    screen.fill(0)
    # string = '{:.2f}'.format(filtered_weight)
    # if len(string) > 6:
    #     string = '{:.1f}'.format(filtered_weight)
    # if string == '-0.00':
    #     string = '0.00'
    string = '{:.1f}'.format(filtered_weight)
    if string == '-0.0':
        string = '0.0'
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
    try:
        screen.show()
    except OSError:
        print("screen update failed")


def run():
    asyncio.run(main())


run()
