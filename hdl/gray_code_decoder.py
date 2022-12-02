import unittest
import numpy as np

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
# TODO: test debounce and direction

class GrayCodeDecoderTestSuite(TestCase):

    SEQUENCE_INC = [1, 3, 2, 0]

    FORCE_X2 = False

    def instantiate_dut(self):
        return GrayCodeDecoder()

    @test_case
    def test(self):

        yield self.dut.force_x2.eq(self.FORCE_X2)

        for x in range(4):
            yield self.dut.x1_value.eq(x)

            result = np.zeros(3)
            for s in self.SEQUENCE_INC:

                yield self.dut.channels.eq(s)
                yield
                yield

                s1 = yield self.dut.strobe_x1
                s2 = yield self.dut.strobe_x2
                s4 = yield self.dut.strobe_x4
                result += [s1, s2, s4]

                assert not s1 or s == x or (self.FORCE_X2 & (s == (~x & 3))), "X1 strobe on incorrect value"
                assert not s2 or s == x or s == (~x & 3), "X2 strobe on incorrect value"

            assert np.array_equal(result, [2 if self.FORCE_X2 else 1, 2, 4]), "unexpected number of strobes for X4"


class GrayCodeDecoderTestSuiteForceX2(GrayCodeDecoderTestSuite):

    FORCE_X2 = True


if __name__ == "__main__":
    unittest.main()
