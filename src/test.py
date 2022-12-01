"""
The test cases here mostly verify that the conversion to Verilog is properly done
and that the IO signals are correctly mapped.

The base tests should be performed against the Amaranth implementation.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.handle import HierarchyObject, SimHandle

CLOCK_FREQ = 5e3
CLOCK_PERIOD_US = int(1e6 / CLOCK_FREQ)

HOLD_CYCLES = 2

SEQUENCE_INC = [1, 3, 2, 0]

COUNTER_WIDTH = 8
COUNTER_MAX = 2**COUNTER_WIDTH - 1

SERIAL_WORD_LEN = 8

SPI_WORD_LEN = 32
SPI_DELAY = 4
SPI_BUFFER_PATH = "swalense_top.dev.spi.data"


def start_clock(dut):
    dut._log.debug("start clock")

    clock = Clock(dut.clk, CLOCK_PERIOD_US, units="us")
    cocotb.start_soon(clock.start())


async def set_in_default(dut):

    dut.rst.value = 0
    dut.channels.value = 1
    dut.force_x2.value = 0
    dut.cs.value = 1
    dut.sck.value = 0
    dut.sdi.value = 0

    await ClockCycles(dut.clk, 1)


async def do_switch_channels(dut, sequence: [int], repeat: int = 1):
    dut._log.debug("channels: {} x {}".format(sequence, repeat))

    for s in sequence * repeat:
        dut.channels.value = s
        await ClockCycles(dut.clk, HOLD_CYCLES)

    await ClockCycles(dut.clk, 1)


async def do_reset(dut):
    dut._log.debug("resetting")

    dut.rst.value = 1
    await ClockCycles(dut.clk, 1)

    dut.rst.value = 0
    await ClockCycles(dut.clk, 1)


async def do_init(dut):

    start_clock(dut)
    await set_in_default(dut)
    await do_reset(dut)


@cocotb.test()
async def test_reset(dut):

    start_clock(dut)
    await set_in_default(dut)

    for i in range(2):

        await do_reset(dut)

        assert dut.counter.value == 0
        assert dut.pwm.value == 0

        # Have something in the counter to observe reset on second iteration
        await do_switch_channels(dut, SEQUENCE_INC, 8)
        assert dut.counter.value != 0


@cocotb.test()
async def test_counter_and_direction(dut):

    await do_init(dut)

    await do_switch_channels(dut, SEQUENCE_INC, 2)
    assert dut.counter.value == 2

    assert dut.direction.value == 1


@cocotb.test()
async def test_pwm(dut):

    await do_init(dut)

    assert dut.pwm.value == 0

    # Repeat until reaching max value, and hence 100% duty cycle
    await do_switch_channels(dut, SEQUENCE_INC, 40)
    assert dut.pwm.value == 1


@cocotb.test()
async def test_serial(dut):
    # See if cocotbext-uart can be used

    await do_init(dut)

    assert dut.serial_tx.value == 1
    await do_switch_channels(dut, SEQUENCE_INC, 1)

    v = 0
    for i in range(64):
        v |= dut.serial_tx.value << i
        await ClockCycles(dut.clk, 1)

    # Look for start bit and discard it
    while v & 1:
        v >>= 1
    v >>= 1

    # Check value
    assert v & ((1 << SERIAL_WORD_LEN) - 1)
    # Check stop bit
    assert v >> SERIAL_WORD_LEN


async def do_spi_clock_tick(dut):

    for c in [0, 1]:
        dut.sck.value = c
        for _ in range(SPI_DELAY):
            await ClockCycles(dut.clk, 1)


@cocotb.test()
async def test_spi(dut):
    # See if cocotbext-spi can be used

    await do_init(dut)

    dut.cs.value = 0
    await ClockCycles(dut.clk, 1)

    VALUE = 0x8365121F

    for i in reversed(range(SPI_WORD_LEN)):
        dut.sdi.value = (VALUE >> i) & 1
        await do_spi_clock_tick(dut)

    dut.cs.value = 1
    await ClockCycles(dut.clk, 1)

    for i in range(8):
        await ClockCycles(dut.clk, 1)

    data = dut._id(SPI_BUFFER_PATH, extended=False).value
    assert data == VALUE


@cocotb.test(skip=True)
async def test_force_x2(dut):

    await do_init(dut)
    dut._log.warning("test is missing")
