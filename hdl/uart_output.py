import logging
import unittest

from amaranth import *

import hdl.util as util

from hdl.test_common import TestCase, test_case


class UARTOutput(Elaboratable):

    DEFAULT_WORD_LEN = 8
    DEFAULT_IDLE_CYCLES = 4

    def __init__(self, width: int, word_len: int = DEFAULT_WORD_LEN, idle_cycles: int = DEFAULT_IDLE_CYCLES):

        self.word_len = word_len
        self.idle_cycles = idle_cycles

        # Inputs
        self.word = Signal(width)
        self.strobe = Signal()

        # Outputs
        self.tx = Signal()

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("{}-N-1, {} idle cycles".format(self.word_len, self.idle_cycles))

    def elaborate(self, platform) -> Module:

        m = Module()

        i = Signal(4)
        start = Signal()

        # Data to shift out: start (1 bit), word, stop (1 bit), idle time
        # Reset to 1 for idle state / stop bit
        data = Signal(self.word_len + 2 + self.idle_cycles, reset=1)

        m.d.comb += self.tx.eq(data[0])

        # Continue transmitting once started,
        # we only check for the next start condition upon completion
        with m.If(i != 0):
            m.d.sync += [
                data.eq(data.shift_right(1)),
                i.eq(i - 1)
            ]

        with m.Elif(start):
            m.d.sync += [
                start.eq(0),
                i.eq(data.width - 1),

                # Idle bits (high), stop bit (high), fill, word, start bit (low)
                # Output is LSB of data
                data.eq(Cat(
                    Const(0),
                    self.word,
                    Const(0, unsigned(self.word_len - self.word.width)),
                    Const(util.max_for_bits(1 + self.idle_cycles))))
            ]

        # Start is normally de-asserted above,
        # but it can be overridden within the same cycle if there is another word to transmit
        # Note that the word that will serve to init data is not necessarily the same as that for
        # which the strobe was first asserted; it does not matter, the strobe only notifies of something to send
        with m.If(self.strobe):
            m.d.sync += start.eq(1)

        return m


#######################################################################################################################


class UARTOutputTestSuite(TestCase):

    COUNTER_WIDTH = 7
    WORD_LEN = 8

    def instantiate_dut(self):
        return UARTOutput(width=self.COUNTER_WIDTH, word_len=self.WORD_LEN)

    def push_word(self, word: int):

        # Line must be high initially
        v = yield self.dut.tx
        self.assertEqual(v, 1)

        yield self.dut.word.eq(word)
        yield self.dut.strobe.eq(1)
        yield
        yield self.dut.strobe.eq(0)
        yield

        result = 0

        # We have one extra cycle after strobe that must be 1
        for i in range(self.dut.word_len + UARTOutput.DEFAULT_IDLE_CYCLES + 3):
            v = yield self.dut.tx
            result |= v << i
            yield

        expected = ((1 << UARTOutput.DEFAULT_IDLE_CYCLES) - 1) << (self.dut.word_len + 3) | \
                   (1 << (self.dut.word_len + 2)) |\
                   (word << 2) |\
                   0b01

        self.assertEqual(result, expected)

    @test_case
    def test(self):

        if self.COUNTER_WIDTH == 8:
            yield from self.push_word(0b10100101)
        elif self.COUNTER_WIDTH == 7:
            yield from self.push_word(0b1100101)
        elif self.COUNTER_WIDTH == 6:
            yield from self.push_word(0b110101)

        yield from self.push_word(0b11111)
        yield from self.push_word(0b10001)
        yield from self.push_word(0b11011)
        yield from self.push_word(0b10011)


class UARTOutputTestSuite2(UARTOutputTestSuite):

    COUNTER_WIDTH = 5
    WORD_LEN = 5


class UARTOutputTestSuite3(UARTOutputTestSuite):

    COUNTER_WIDTH = 8
    WORD_LEN = 8


if __name__ == "__main__":
    unittest.main()
