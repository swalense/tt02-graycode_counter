import logging
import unittest

from amaranth import *

from hdl.gray_code_decoder import GrayCodeDecoder
from hdl.counter import Counter
from hdl.pwm_signal import PWMSignal
from hdl.gearbox import Gearbox
from hdl.uart_output import UARTOutput
from hdl.spi_input import SPIInputChunked

import hdl.config as config
import hdl.util as util

from hdl.test_common import TestCase, test_case


class Device(Elaboratable):

    def __init__(self):

        width = config.COUNTER_WIDTH
        assert width <= 8

        self._decoder = GrayCodeDecoder()
        self._pwm_signal = PWMSignal(width=width)
        self._gearbox = Gearbox(self._decoder)
        self._serial_out = UARTOutput(width=width, word_len=config.UART_WORD_LEN, idle_cycles=config.UART_IDLE_CYCLES)
        self._internal_counter = Counter(width=width)

        # Inputs
        self.channels = self._decoder.channels
        self.cs = Signal()
        self.sck = Signal()
        self.sdi = Signal()

        # Outputs
        self.counter = Signal(width)
        self.direction = self._decoder.direction
        self.pwm = self._pwm_signal.signal
        self.serial_tx = self._serial_out.tx

        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def calculate_parameters_value(
            wrap: bool, debounce: bool, gearbox: bool,
            x1_value: int,
            gearbox_timer_cycles: int,
            init_value: int,
            max_value: int):

        assert config.SPI_WORD_LEN >= 5

        return int(gearbox) |\
               (int(wrap) << 1) |\
               (int(debounce) << 2) |\
               (x1_value << 3) |\
               (gearbox_timer_cycles << config.SPI_WORD_LEN) |\
               (init_value << (config.SPI_WORD_LEN * 2)) |\
               (max_value << (config.SPI_WORD_LEN * 3))

    def elaborate(self, platform) -> Module:

        m = Module()

        m.submodules.decoder = self._decoder
        m.submodules.pwm = self._pwm_signal
        m.submodules.gearbox = self._gearbox
        m.submodules.serial_out = self._serial_out
        m.submodules.counter = self._internal_counter

        # SPI interface and configuration parameters

        # These parameters are part of the same config byte
        combined_params = Cat(
            self._gearbox.enable,
            self._internal_counter.wrap,
            self._decoder.debounce,
            self._decoder.x1_value)

        assert self._gearbox.timer_cycles.width == 8
        params = Cat(
            combined_params,
            Signal(config.SPI_WORD_LEN - combined_params.shape().width),
            self._gearbox.timer_cycles,
            self._internal_counter.init_value,
            Signal(config.SPI_WORD_LEN - self._internal_counter.init_value.width),
            self._internal_counter.max_value)

        gbp_sec, gbp_cycles = Gearbox.get_timer_period(*config.GEARBOX_DEFAULT_ENCODER)
        self.logger.info("period: {:.2f} ms, {} cycles".format(gbp_sec * 1e3, gbp_cycles))

        # Parameters are assigned from the SPI buffer "combinationally" below,
        # we need to init the buffer instead of the individual parameters
        spi_init = self.calculate_parameters_value(
            debounce=config.DECODER_DEFAULT_DEBOUNCE,
            wrap=config.DECODER_DEFAULT_WRAP,
            x1_value=0,
            gearbox=config.GEARBOX_DEFAULT_ENABLED,
            gearbox_timer_cycles=gbp_cycles,
            max_value=config.COUNTER_DEFAULT_MAX_VALUE,
            init_value=config.COUNTER_DEFAULT_VALUE)

        self.logger.info("initial parameter values: 0x{:X}".format(spi_init))

        spi = SPIInputChunked(
            width=util.bits_multiple(params.shape().width, multiple_of=config.SPI_WORD_LEN), init=spi_init)
        m.submodules.spi = spi

        m.d.comb += [
            spi.cs.eq(self.cs),
            spi.sck.eq(self.sck),
            spi.sdi.eq(self.sdi),

            params.eq(spi.data)
        ]

        # Counter
        m.d.comb += [
            self._internal_counter.inc.eq(self._decoder.direction),
            self._internal_counter.strobe.eq(~spi.busy & self._gearbox.strobe),
            self._internal_counter.reset.eq(spi.strobe),

            self.counter.eq(self._internal_counter.value)
        ]

        # PWM
        m.d.comb += [
            self._pwm_signal.duty.eq(self._internal_counter.value),
            self._pwm_signal.max_duty.eq(self._internal_counter.max_value),
        ]

        # UART
        m.d.comb += [
            self._serial_out.word.eq(self._internal_counter.value),
            self._serial_out.strobe.eq(self._internal_counter.updating_strobe)
        ]

        return m


#######################################################################################################################


class DeviceTestSuite(TestCase):

    COUNTER_WIDTH = config.COUNTER_WIDTH

    HOLD_CYCLES = 4

    def instantiate_dut(self):
        return Device()

    def update_channels(self, sequence: [int], repeat: int = 1):

        counter = []

        for s in sequence * repeat:
            yield self.dut.channels.eq(s)
            for _ in range(self.HOLD_CYCLES):
                yield
                v = yield self.dut.counter
                if not len(counter) or counter[-1] != v:
                    counter.append(v)

        return counter

    # FIXME: this needs to be reorganised

    WIDTH = 32

    def do_wait(self):

        for _ in range(4):
            yield

    def do_cs_low(self):

        yield self.dut.cs.eq(1)
        yield
        yield
        yield self.dut.cs.eq(0)
        yield
        yield

    def do_clock_tick(self):

        yield self.dut.sck.eq(0)
        yield from self.do_wait()
        yield self.dut.sck.eq(1)
        yield from self.do_wait()

    def send(self, val: int):

        # TODO: do it in another clock domain instead and avoid clock aligned transitions

        self.logger.info("SPI: send 0x{:X}".format(val))

        yield from self.do_cs_low()

        v = val
        for _ in range(self.WIDTH):
            yield self.dut.sdi.eq((v >> (self.WIDTH - 1)) & 1)
            yield from self.do_clock_tick()
            v <<= 1

        yield self.dut.cs.eq(1)
        yield

        for _ in range(10):
            yield

        yield from self.update_channels([2, 0, 1, 3], repeat=10)

    @test_case
    def test_parameters(self):

        yield from self.send(Device.calculate_parameters_value(
            debounce=True, wrap=False, gearbox=True, x1_value=0, gearbox_timer_cycles=137, max_value=110, init_value=17))


if __name__ == "__main__":
    logging.root.setLevel(logging.DEBUG)
    unittest.main()
