import logging
import unittest

from amaranth import *

import hdl.util as util
import hdl.config as config

from hdl.test_common import test_case, TestCase


class PWMSignal(Elaboratable):

    """
    PWM signal generator.

    Inputs:
        * duty: duty cycle, with respect to width parameter.
            The output is constantly low for 0, otherwise high for duty+1 cycles.
        * half (active low): duty only reaches half of value corresponding to width.

    Outputs:
        * signal: PWM signal

    """

    def __init__(self, width: int):

        # In
        self.duty = Signal(width)
        self.max_duty = Signal(width)

        # Out
        self.signal = Signal(name="pwm_signal")

    def elaborate(self, platform) -> Module:

        m = Module()

        counter = Signal.like(self.duty)

        m.d.sync += counter.eq(counter + 1)

        with m.If(counter == self.max_duty):
            m.d.sync += [
                self.signal.eq(self.duty != 0),
                counter.eq(0)
            ]

        with m.Elif(counter == self.duty):
            m.d.sync += self.signal.eq(0)

        return m


#######################################################################################################################


class PWMSignalTestSuite(TestCase):

    MAX_DUTY = 27

    CYCLES = 3

    def instantiate_dut(self):
        return PWMSignal(width=util.bits_required(self.MAX_DUTY))

    def run_test(self, duty: int):

        self.logger.info("duty: {} / {}".format(duty, self.MAX_DUTY))

        d = 0 if duty == 0 else duty + 1
        seq = ([1] * d + [0] * (self.MAX_DUTY + 1 - d)) * self.CYCLES

        yield self.dut.max_duty.eq(self.MAX_DUTY)
        yield self.dut.duty.eq(duty)

        # Discard first run as signal switches to 1 during roll over
        for i in range(self.MAX_DUTY + 2):
            yield

        for i in range(self.CYCLES * self.MAX_DUTY):

            v = yield self.dut.signal
            assert v == seq[i], "got {} at cycle {} instead of {}".format(v, i, seq[i])

            yield

    @test_case
    def test_zero(self):
        yield from self.run_test(0)

    @test_case
    def test_one(self):
        yield from self.run_test(1)

    @test_case
    def test_full(self):
        yield from self.run_test(self.MAX_DUTY)

    @test_case
    def test_value_below_half(self):
        yield from self.run_test(11)

    @test_case
    def test_value_above_half(self):
        yield from self.run_test(30)


class PWMSignalTestSuite2(PWMSignalTestSuite):

    MAX_DUTY = 31


class PWMSignalTestSuite3(PWMSignalTestSuite):

    MAX_DUTY = 255


if __name__ == "__main__":
    unittest.main()
