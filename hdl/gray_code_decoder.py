import logging
import unittest

from amaranth import *

from hdl.luna.test.utils import LunaGatewareTestCase, sync_test_case


class GrayCodeDecoder(Elaboratable):

    def __init__(self, default_debounce: bool = False):

        # Inputs
        self.channels = Signal(2)
        self.debounce = Signal(reset=int(default_debounce))
        self.x1_value = Signal(2)

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
            self.strobe_x2.eq(self.strobe_x4 & (self.channels[0] == self.channels[1])),
            self.strobe_x1.eq(self.strobe_x2 & (self.channels[0] == self.x1_value))
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


class GrayCodeDecoderTestSuite(LunaGatewareTestCase):

    def setUp(self):
        super().setUp()
        self.logger = logging.getLogger(self.__class__.__name__)

    def instantiate_dut(self):
        return GrayCodeDecoder()

    @sync_test_case
    def test(self):
        yield

        self.logger.warning("no test is implemented")


if __name__ == "__main__":
    unittest.main()
