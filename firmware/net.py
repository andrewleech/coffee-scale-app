# uncomment to setup WiFi connection
import asyncio
import config
import network
import time


async def do_connect():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('Connecting to network...')
        sta_if.active(True)
        sta_if.connect(config.WIFI_SSID, config.WIFI_PASS)
        timeout = time.ticks_ms() + 5000
        while not sta_if.isconnected():
            if time.ticks_diff(time.ticks_ms(), timeout) > 0:
                print("Failed to connect")
                break
            asyncio.sleep_ms(50)
    print('Network config:', sta_if.ifconfig())

    import webrepl
    webrepl.start()
