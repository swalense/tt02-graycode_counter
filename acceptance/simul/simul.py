import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

CLOCK_FREQ = 20e6
CLOCK_PERIOD_NS = int(1e9 / CLOCK_FREQ)


def start_clock(dut):
    dut._log.debug("start clock")

    clock = Clock(dut.xclk, CLOCK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())

    # simul_clock = Clock(dut.user_io_in[0], int(1e6 / 2400), units="us")
    # cocotb.start_soon(simul_clock.start())


async def set_in_default(dut):

    dut.sel.value = 0x01
    dut.user_io_in.value = 0

    dut.set_clk_div.value = 0
    await ClockCycles(dut.xclk, 4)
    dut.set_clk_div.value = 1

    dut.reset.value = 1
    await ClockCycles(dut.xclk, 1)
    dut.reset.value = 0
    await ClockCycles(dut.xclk, 8)

    await ClockCycles(dut.xclk, 8)

    dut.user_io_in.value = 0x02
    await Timer(1, units="ms")

    dut.user_io_in.value = 0x0C

    await ClockCycles(dut.xclk, 8)


async def do_init(dut):

    start_clock(dut)
    await set_in_default(dut)


@cocotb.test(skip=False)
async def test_spi(dut):

    await do_init(dut)

    dut.user_io_in[5].value = 1
    await Timer(380, units="us")

    dut.user_io_in[5].value = 0
    await Timer(820, units="us")
    dut.user_io_in[5].value = 1

    await Timer(520, units="us")

    dut.user_io_in[5].value = 0
    await Timer(370, units="us")
    dut.user_io_in[5].value = 1

    await Timer(1000, units="us")
