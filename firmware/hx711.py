import time
import uasyncio
import micropython
from machine import Pin
from filtering import KalmanFilter


class HX711:
    def __init__(self, dout, pd_sck, gain=128):

        self.pSCK = Pin(pd_sck, mode=Pin.OUT)
        self.pOUT = Pin(dout, mode=Pin.IN, pull=Pin.PULL_DOWN)

        self.power_up()

        self.GAIN = 0
        self.OFFSET = 0
        self.SCALE = 1

        self.kf = KalmanFilter(0.08, q=0.09)

        self.set_gain(gain)

        self.updated = uasyncio.Event()
        uasyncio.create_task(self._background())

    async def _background(self):
        print("Starting to monitor HX711 in background")
        failures = 0
        while True:
            try:
                self.kf.update_estimate(await self.read())
                self.updated.set()
                failures = 0
            except:
                failures += 1

    def set_gain(self, gain):
        if gain == 128:
            self.GAIN = 1
        elif gain == 64:
            self.GAIN = 3
        elif gain == 32:
            self.GAIN = 2
        else:
            raise ValueError("Unknown gain value")

    def is_ready(self):
        return self.pOUT() == 0

    async def read(self):
        # wait for the device being ready
        timeout = time.ticks_ms()
        while self.pOUT() == 1:
            await uasyncio.sleep_ms(5)
            if time.ticks_diff(time.ticks_ms(), timeout) > 500:
                raise OSError("Sensor does not respond")

        # shift in data, and gain & channel info
        result = 0
        for i in reversed(range(24 + self.GAIN)):
            self.pSCK(True)
            self.pSCK(False)
            result |= (self.pOUT() << i)

        # shift back the extra bits
        result >>= self.GAIN

        # check sign
        if result > 0x7FFFFF:
            result -= 0x1000000

        return result

    # async def read_filtered(self, times=1):
    #     for _ in range(times):
    #         self.kf.update_estimate(await self.read())
    #     return self.kf.last_estimate

    # async def get_value(self, times=3):
    #     return await self.read_filtered(times) - self.OFFSET

    async def read_filtered(self, times=1):
        for _ in range(times):
            self.updated.clear()
            await self.updated.wait()
        return self.kf.last_estimate

    async def get_value(self, times=3):

        return (await self.read_filtered(times)) - self.OFFSET

    async def get_units(self, times=1):
        return await self.get_value(times) / self.SCALE

    async def tare(self, times=15):
        self.kf.last_estimate = 0.0
        sum = await self.read_filtered(times)
        self.set_offset(sum)

    def set_scale(self, scale):
        self.SCALE = scale

    def set_offset(self, offset):
        self.OFFSET = offset

    def power_down(self):
        self.pSCK.value(False)
        self.pSCK.value(True)

    def power_up(self):
        self.pSCK.value(False)
