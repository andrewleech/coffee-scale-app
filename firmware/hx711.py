import time
import uasyncio
import micropython
from machine import Pin


class HX711:
    def __init__(self, dout, pd_sck, gain=128, callback=None):

        self.pSCK = Pin(pd_sck, mode=Pin.OUT)
        self.pOUT = Pin(dout, mode=Pin.IN, pull=Pin.PULL_DOWN)
        self.callback = callback

        self.power_up()

        self.GAIN = 0
        self.OFFSET = 0
        self.SCALE = 1

        self.time_constant = 0.1
        self.filtered = 0

        self.set_gain(gain)
        
        self._tare_count = 0
        self._tare_buff = 0

        self._last_raw = 0
        self._last_units = 0

        self.pOUT.irq(self._read_irq, trigger=Pin.IRQ_FALLING)
        
        self.scheduled = False

    def _read_irq(self, _=None):
        if not self.scheduled:
            self.scheduled = True
            micropython.schedule(self._read_units, None)

    def _read_raw(self, _=None):
        # Disable interrupt
        # self.pOUT.irq(None, trigger=Pin.IRQ_FALLING)

        print("self.pOUT()", self.pOUT, self.pOUT())

        # shift in data, and gain & channel info
        result = 0
        for i in reversed(range(24 + self.GAIN)):
            # state = disable_irq()
            self.pSCK(True)
            self.pSCK(False)
            print(self.pOUT())
            # enable_irq(state)
            result |= (self.pOUT() << i)

        # shift back the extra bits
        result >>= self.GAIN

        # check sign
        if result > 0x7FFFFF:
            result -= 0x1000000

        # Re-enable interrupt
        # self.pOUT.irq(self._read_irq, trigger=Pin.IRQ_FALLING)

        return result

    def _read_units(self, _=None):
        try:
            time.sleep_ms(10)
            raw = self._read_raw()
            print(raw)

            self._last_raw = raw
            
            units = (raw - self.OFFSET) / self.SCALE
            self._last_units = units


            print(self._tare_count, raw)
            if self._tare_count:
                self._tare_count -= 1
                self._tare_buff += raw
            # elif self.callback:
                # print("callback")
                # self.callback(units)
            self.scheduled = False
        except Exception as ex:
            print(ex)
            

    def set_gain(self, gain):
        if gain == 128:
            self.GAIN = 1
        elif gain == 64:
            self.GAIN = 3
        elif gain == 32:
            self.GAIN = 2
        else:
            raise ValueError("Unknown gain value")

        self.filtered = self.read()
        print('Gain & initial value set', self.filtered)

    def is_ready(self):
        return self.pOUT() == 0

    def read(self):
        # wait for the device being ready
        timeout = time.ticks_ms()
        while self.pOUT() == 1:
            time.sleep_ms(1)
            if time.ticks_diff(time.ticks_ms(), timeout) > 500:
                raise OSError("Sensor does not respond")

        return self._read_raw()

    def read_average(self, times=3):
        if times == 1:
            return self.read()
        sum = 0
        for i in range(times):
            sum += self.read()
        return sum / times

    def read_lowpass(self):
        self.filtered += self.time_constant * (self.read() - self.filtered)
        return self.filtered

    def get_value(self, times=3):
        return self.read_average(times) - self.OFFSET

    def get_units(self, times=3):
        return self.get_value(times) / self.SCALE

    async def tare(self, times=10):
        print("tare", times)
        self._tare_buff = 0
        self._tare_count = times
        while self._tare_count:
            await uasyncio.sleep_ms(50)
        self.set_offset(self._tare_buff / times)

    def set_scale(self, scale):
        self.SCALE = scale

    def set_offset(self, offset):
        self.OFFSET = offset

    def set_time_constant(self, time_constant=None):
        if time_constant is None:
            return self.time_constant
        elif 0 < time_constant < 1.0:
            self.time_constant = time_constant

    def power_down(self):
        self.pSCK.value(False)
        self.pSCK.value(True)

    def power_up(self):
        self.pSCK.value(False)
