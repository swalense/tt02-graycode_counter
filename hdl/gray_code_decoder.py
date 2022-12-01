import logging
import unittest

from amaranth import *

from hdl.test_common import TestCase, test_case


class GrayCodeDecoder(Elaboratable):

    def __init__(self, default_debounce: bool = False):

        # Inputs

        self.channels = Signal(2)
        self.debounce = Signal(reset=int(default_debounce))
        self.x1_value = Signal(2)
        self.force_x2 = Signal()

        # Outputs

        self.direction = Signal()
        self.strobe_x4 = Signal()
        self.strobe_x2 = Signal()
        self.strobe_x1 = Signal()

    def elaborate(self, platform) -> Module:

        m = Module()

        prev_channels = Signal(self.channels.shape(), reset_less=True)

        dir = Signal()
        m.d.comb += dir.eq(self.channels[0] ^ prev_channels[1])

        m.d.comb += [
            self.strobe_x2.eq(self.strobe_x4 & ((self.channels == self.x1_value) | (self.channels == ~self.x1_value))),
            self.strobe_x1.eq(Mux(self.force_x2, self.strobe_x2, (self.strobe_x4 & (self.channels == self.x1_value))))
        ]

        m.d.sync += self.strobe_x4.eq(0)

        with m.If(self.channels != prev_channels):
            m.d.sync += [

                prev_channels.eq(self.channels),
                self.direction.eq(dir),

                # For debouncing we just discard the first change of direction
                self.strobe_x4.eq((dir == self.direction) | ~self.debounce)
            ]

        with m.If(ResetSignal("sync")):
            m.d.sync += prev_channels.eq(self.channels)

        return m


#######################################################################################################################


class GrayCodeDecoderTestSuite(TestCase):

    SEQUENCE_INC = [1, 3, 2, 0]

    DELAY = 4

    def instantiate_dut(self):
        return GrayCodeDecoder()

    @test_case
    def test(self):

        for s in self.SEQUENCE_INC * 2:

            yield self.dut.x1_value.eq(0b11)

            yield self.dut.channels.eq(s)
            for _ in range(self.DELAY):
                yield



        # FIXME: test is incomplete
        self.logger.warning("no test is implemented")


if __name__ == "__main__":
    unittest.main()
