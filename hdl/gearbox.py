import logging
import unittest

from amaranth import *

from hdl.gray_code_decoder import GrayCodeDecoder

import hdl.config as config
import hdl.util as util

from hdl.test_common import TestCase, test_case


class Gearbox(Elaboratable):

    TIMER_CYCLES_WIDTH = 8

    # Shift divides threshold to find gear (timer period is calculated accordingly below)
    SHIFT = 3

    # Threshold is increased by X4 transition and decreased by a timer
    THRESHOLD_WIDTH = SHIFT + 2

    def __init__(self, decoder: GrayCodeDecoder, default_timer_cycles: int = util.max_for_bits(TIMER_CYCLES_WIDTH - 1)):

        assert default_timer_cycles <= util.max_for_bits(self.TIMER_CYCLES_WIDTH), "default timer cycles too large"

        self._decoder = decoder

        # Inputs

        self.enable = Signal()
        self.timer_cycles = Signal(self.TIMER_CYCLES_WIDTH, reset=default_timer_cycles)

        # Outputs
        self.strobe = Signal()
        self.gear = Signal(2)

        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def get_timer_period(detents: int, transitions: int, clock: int = config.CLOCK_FREQ):

        # Period is chosen so that gear value 2 would be reached after 1s at constant 1 turn per second
        # Shift is chosen to keep period close to 1 / (D * P) with 24 detents / 24 PPR encoder

        # For
        g = 2   # Gear
        d = 1   # Duration in s
        f = 2 ** Gearbox.SHIFT

        # Solve ((detents * transitions * d) - (d / p)) / f = g for p
        p = 1 / (detents * transitions - g * f / d)

        return p, int(round(p * config.CLOCK_FREQ))

    def elaborate(self, platform) -> Module:

        m = Module()

        threshold = Signal(self.THRESHOLD_WIDTH)

        period = Signal.like(self.timer_cycles)

        m.d.sync += period.eq(period + 1)
        with m.If(period == self.timer_cycles):

            m.d.sync += period.eq(0)

            with m.If(threshold != 0):
                m.d.sync += threshold.eq(threshold - 1)

        with m.If(self._decoder.strobe_x4 & ~threshold.all()):
            m.d.sync += threshold.eq(threshold + 1)

        g = Signal(self.THRESHOLD_WIDTH - self.SHIFT)
        assert g.width == 2

        m.d.comb += [
            g.eq(threshold >> self.SHIFT),
            self.gear.eq(Mux(g[1], 2, g))
        ]

        a = Array([self._decoder.strobe_x1, self._decoder.strobe_x2, self._decoder.strobe_x4])
        m.d.comb += self.strobe.eq(Mux(self.enable, a[self.gear], self._decoder.strobe_x1))

        return m


#######################################################################################################################


class GearboxTestSuite(TestCase):

    SEQUENCE_INC = [1, 3, 2, 0]

    HOLD_CYCLES = 32

    class DUT(Elaboratable):
        def __init__(self):

            self.decoder = GrayCodeDecoder()
            self.gearbox = Gearbox(self.decoder, default_timer_cycles=62)

        def elaborate(self, platform) -> Module:

            m = Module()

            m.submodules.decoder = self.decoder
            m.submodules.gearbox = self.gearbox

            return m

    def instantiate_dut(self):
        return self.DUT()

    @test_case
    def test(self):

        yield self.dut.decoder.debounce.eq(1)

        s = 0
        for i in range(int(config.CLOCK_FREQ)):

            if (i % self.HOLD_CYCLES) == 0:
                yield self.dut.decoder.channels.eq(self.SEQUENCE_INC[s % len(self.SEQUENCE_INC)])
                s += 1

            yield

        # FIXME: test is incomplete
        self.logger.warning("test is not implemented")


if __name__ == "__main__":
    config.DEBUG = True
    unittest.main()
