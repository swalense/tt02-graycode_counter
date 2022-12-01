import logging
import unittest

from amaranth import *
from amaranth.asserts import Fell, Rose

from hdl.luna.test.utils import sync_test_case, LunaGatewareTestCase


class SPIInputChunked(Elaboratable):

    def __init__(self, width: int, init: int = 0):

        # Inputs
        self.cs = Signal()
        self.sck = Signal()
        self.sdi = Signal()

        # Outputs
        self.busy = Signal()
        self.strobe = Signal()
        self.data = Signal(width, reset=init)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("SPI buffer width: {} bits".format(width))

    def elaborate(self, platform) -> Module:

        m = Module()

        # Count exact number of bit received to avoid strobe when it is not that expected,
        # or remained 0 because CS just went low and up
        i = Signal(range(self.data.width + 1))

        m.d.sync += self.strobe.eq(0)

        with m.If(Fell(self.cs)):
            m.d.sync += [
                i.eq(0),
                self.busy.eq(1)
            ]

        with m.Elif(self.busy):

            with m.If(Rose(self.cs)):
                m.d.sync += [
                    self.strobe.eq(i == self.data.width),
                    self.busy.eq(0),
                ]

            with m.Elif(Rose(self.sck)):
                m.d.sync += [
                    self.data.eq(Cat(self.sdi, self.data[0:len(self.data)])),
                    i.eq(i + 1)
                ]

        return m


#######################################################################################################################


class SPIInputTestSuite(LunaGatewareTestCase):

    WIDTH = 16

    DELAY = 4

    def setUp(self):
        super().setUp()

    def do_wait(self):

        for _ in range(self.DELAY):
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

    def instantiate_dut(self):
        return SPIInputChunked(self.WIDTH)

    def send(self, val: int):

        # TODO: do it in another clock domain instead and avoid clock aligned transitions

        yield from self.do_cs_low()

        v = val
        for i in reversed(range(self.WIDTH)):
            yield self.dut.sdi.eq((v >> i) & 1)
            yield from self.do_clock_tick()

        yield self.dut.sck.eq(0)
        yield

        yield self.dut.cs.eq(1)
        yield

        yield
        strobe = yield self.dut.strobe
        self.assertTrue(strobe, "strobe is not asserted")

        data = yield self.dut.data
        self.assertEqual(data, val, "expected {}, got {}".format(val, data))

        yield
        strobe = yield self.dut.strobe
        self.assertFalse(strobe, "strobe is still asserted")

    @sync_test_case
    def test(self):
        yield from self.send(0x19C5)


if __name__ == "__main__":
    logging.root.setLevel(logging.DEBUG)
    unittest.main()
