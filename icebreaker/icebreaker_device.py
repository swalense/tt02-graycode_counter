from amaranth import *
from amaranth.build import *
from amaranth_boards.icebreaker import ICEBreakerPlatform

from hdl.device import Device

import hdl.config as config

ATTRS_IO = Attrs(IO_STANDARD="SB_LVCMOS")

IC_PMOD = [
    Resource("in", 0,

        # PMOD 1A
        Subsignal("channels", Pins("1 2", dir="i", conn=("pmod", 0)), ATTRS_IO),
        Subsignal("force_x2", Pins("3", dir="i", conn=("pmod", 0)), ATTRS_IO),
        Subsignal("cs", Pins("4", dir="i", conn=("pmod", 0)), ATTRS_IO),
        Subsignal("sck", Pins("7", dir="i", conn=("pmod", 0)), ATTRS_IO),
        Subsignal("sdi", Pins("8", dir="i", conn=("pmod", 0)), ATTRS_IO),
        #Subsignal("", Pins("9 10", dir="i", conn=("pmod", 0)), ATTRS_IO),

        # PMOD 2
        Subsignal("rst", Pins("9", dir="i", conn=("pmod", 2)), ATTRS_IO)
    ),

    Resource("out", 0,

        # PMOD 1B
        Subsignal("counter", Pins("1 2 3 4 7", dir="o", conn=("pmod", 1)), ATTRS_IO),
        Subsignal("direction", Pins("8", dir="o", conn=("pmod", 1)), ATTRS_IO),
        Subsignal("serial", Pins("9", dir="o", conn=("pmod", 1)), ATTRS_IO),
        #Subsignal("", Pins("10", dir="o", conn=("pmod", 1)), ATTRS_IO),

        # PMOD 2 -> break_off_pmod below
        # PWM LED
    ),

    Resource("debug", 0,

        # PMOD 1B
        Subsignal("clk", Pins("10", dir="o", conn=("pmod", 1)), ATTRS_IO)
    )
]


class ICEBreakerDevice(Elaboratable):

    def elaborate(self, platform) -> Module:

        platform.add_resources(IC_PMOD)

        conn_in = platform.request("in")
        conn_out = platform.request("out")

        m = Module()

        # Low frequency clock

        # TODO: oscillator should only be enabled 100us after powering it up
        lf_clk = Signal()
        osc = Instance("SB_LFOSC", i_CLKLFPU=1, i_CLKLFEN=1, o_CLKLF=lf_clk)
        platform.add_clock_constraint(lf_clk, 10e3)
        m.submodules += osc

        m.domains.osc = ClockDomain()
        m.d.comb += ClockSignal("osc").eq(lf_clk)

        # TODO: use a global buffer?
        clk = Signal()
        m.d.osc += clk.eq(~clk)
        platform.add_clock_constraint(clk, 5e3)

        platform.lookup(platform.default_clk).attrs['GLOBAL'] = False
        m.domains.sync = ClockDomain()
        m.d.comb += [
            ClockSignal("sync").eq(clk),
            ResetSignal("sync").eq(conn_in.rst)
        ]

        # Project

        top = Device()
        m.submodules += top

        m.d.comb += [
            top.channels.eq(conn_in.channels),
            top.force_x2.eq(conn_in.force_x2),
            top.cs.eq(conn_in.cs),
            top.sck.eq(conn_in.sck),
            top.sdi.eq(conn_in.sdi),

            conn_out.counter.eq(top.counter),
            conn_out.serial.eq(top.serial_tx)
        ]

        # PWM and gear indicator LEDs of break-off PMOD

        platform.add_resources(ICEBreakerPlatform.break_off_pmod)

        led_r = platform.request("led_r", 1)
        led_g = platform.request("led_g", 1)
        m.d.comb += [
            led_r.eq(top.pwm),
            led_g.eq(~top.pwm)
        ]

        led_r = platform.request("led_r", 0)
        led_g = platform.request("led_g", 0)
        m.d.comb += [
            led_r.eq(top._gearbox.enable & (top._gearbox.gear == 1)),
            led_g.eq(top._gearbox.enable & (top._gearbox.gear == 2))
        ]

        # TODO: remove

        dbg = platform.request("debug")
        m.d.comb += [
            dbg.clk.eq(ClockSignal("sync"))
        ]

        return m
