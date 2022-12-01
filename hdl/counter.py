import logging
import unittest

from amaranth import *

import hdl.util as util

from hdl.test_common import TestCase, test_case


class Counter(Elaboratable):

    def __init__(self, width: int, default_value: int = 0, default_max_value: int = 0):

        assert util.max_for_bits(width) >= default_value

        # Inputs

        self.init_value = Signal(width)
        self.max_value = Signal(width, reset=default_max_value)
        self.wrap = Signal()
        self.inc = Signal()
        self.strobe = Signal()
        self.reset = Signal()

        # Outputs

        self.value = Signal(width, reset=default_value)
        # Value will be updated on next cycle, does not strobe on reset
        self.updating_strobe = Signal()

    def elaborate(self, platform) -> Module:

        m = Module()

        can_update = Signal()
        m.d.comb += can_update.eq(Mux(self.inc, self.value != self.max_value, self.value.any()))

        m.d.comb += self.updating_strobe.eq(self.strobe & (self.wrap | can_update))

        with m.If(self.reset):
            m.d.sync += self.value.eq(self.init_value)

        with m.Elif(self.updating_strobe):
            with m.If(can_update):
                m.d.sync += self.value.eq(self.value + Mux(self.inc, 1, -1))
            with m.Else():
                m.d.sync += self.value.eq(Mux(self.inc, 0, self.max_value))

        return m


#######################################################################################################################


class CounterTestSuite(TestCase):

    COUNTER_WIDTH = 5
    COUNTER_MAX_VALUE = util.max_for_bits(COUNTER_WIDTH)

    def instantiate_dut(self):
        return Counter(width=self.COUNTER_WIDTH)

    def do_strobe(self, repeat: int = 1):
        for _ in range(repeat):
            yield self.dut.strobe.eq(1)
            yield
            yield self.dut.strobe.eq(0)
            yield

    def do_run(self, max_value: int, wrap: bool, inc: bool, repeat: int, expected: int):

        yield self.dut.max_value.eq(max_value)
        yield self.dut.inc.eq(int(inc))
        yield self.dut.wrap.eq(int(wrap))

        yield from self.do_strobe(repeat)
        v = yield self.dut.value

        self.assertEqual(v, expected)

    @test_case
    def test_parameters_nowrap_width(self):
        yield from self.do_run(
            max_value=self.COUNTER_MAX_VALUE, inc=True, wrap=False, repeat=self.COUNTER_MAX_VALUE,
            expected=self.COUNTER_MAX_VALUE)

    @test_case
    def test_parameters_nowrap_over(self):
        yield from self.do_run(
            max_value=self.COUNTER_MAX_VALUE, inc=True, wrap=False, repeat=self.COUNTER_MAX_VALUE + 1,
            expected=self.COUNTER_MAX_VALUE)

    @test_case
    def test_parameters_nowrap_lower(self):
        yield from self.do_run(
            max_value=3, inc=True, wrap=False, repeat=10,
            expected=3)

    @test_case
    def test_parameters_wrap_width(self):
        yield from self.do_run(
            max_value=self.COUNTER_MAX_VALUE, inc=True, wrap=True, repeat=self.COUNTER_MAX_VALUE + 1,
            expected=0)

    @test_case
    def test_parameters_wrap_below(self):
        v = 3
        yield from self.do_run(
            max_value=v, inc=False, wrap=True, repeat=v,
            expected=1)

    @test_case
    def test_parameters_wrap_zero(self):
        v = self.COUNTER_MAX_VALUE - 3
        yield from self.do_run(
            max_value=v, inc=False, wrap=True, repeat=1,
            expected=v)

    @test_case
    def test_parameters_reset(self):
        yield from self.do_run(
            max_value=self.COUNTER_MAX_VALUE, inc=True, wrap=False, repeat=1,
            expected=1)

        yield self.dut.reset.eq(1)
        yield
        yield self.dut.reset.eq(1)
        yield

        v = yield self.dut.value

        self.assertEqual(v, 0)

    # TODO: test init value


if __name__ == "__main__":
    logging.root.setLevel(logging.DEBUG)
    unittest.main()
