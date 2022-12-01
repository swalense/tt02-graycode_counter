import os

from amaranth import *
from amaranth.back import verilog

from hdl.device import Device

import hdl.config as config


class Top(Elaboratable):

    def __init__(self):

        self.io_in = Signal(8)
        self.io_out = Signal(8)

    def elaborate(self, platform) -> Module:

        m = Module()

        cd_sync = ClockDomain("sync")
        m.domains += cd_sync

        dev = Device()
        m.submodules.dev = dev

        # Inputs

        inputs = Cat(
            dev.channels,
            dev.force_x2,
            dev.cs,
            dev.sck,
            dev.sdi,
        )

        input_pins = self.io_in[2:8]

        assert inputs.shape() == input_pins.shape(), "inconsistent input shape"

        m.d.comb += [
            ClockSignal("sync").eq(self.io_in[0]),
            ResetSignal("sync").eq(self.io_in[1]),
            inputs.eq(input_pins)
        ]

        # Outputs

        outputs = Cat(
            dev.serial_tx,
            dev.pwm,
            dev.direction,
            dev.counter[0:config.OUTPUT_WIDTH]
        )

        assert outputs.shape() == self.io_out.shape(), "inconsistent output shape"

        m.d.comb += self.io_out.eq(outputs)

        return m


if __name__ == "__main__":

    # Based on https://github.com/adamgreig/tinytapeout-prn

    top_name = os.environ.get("TOP", "top")

    module = Top()

    v = verilog.convert(
        module, name=top_name, ports=[module.io_out, module.io_in],
        emit_src=False, strip_internal_attrs=True)
    print(v)
