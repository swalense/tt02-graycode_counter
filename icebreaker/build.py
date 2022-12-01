import logging
import argparse
import os.path
import re

from amaranth_boards.icebreaker import ICEBreakerPlatform

from icebreaker.icebreaker_device import ICEBreakerDevice

BUILD_NAME = "top"
BUILD_DIR = "build"

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--program", action="store_true", required=False,
                        help="program the ICEBreaker after building the device")

    args = parser.parse_args()

    p = ICEBreakerPlatform()
    p.build(ICEBreakerDevice(),
            name=BUILD_NAME,
            build_dir=BUILD_DIR,
            do_program=args.program,
            synth_opts="",
            nextpnr_opts="",
            debug_verilog=True)

    device_utilization = "|".join(_ + "\\:" for _ in [
        "ICESTORM_LC",
        "ICESTORM_RAM",
        "SB_IO",
        "SB_GB",
        # "ICESTORM_PLL",
        # "SB_WARMBOOT",
        # "ICESTORM_DSP",
        # "ICESTORM_HFOSC",
        "ICESTORM_LFOSC",
        # "SB_I2C",
        # "SB_SPI",
        # "IO_I3C",
        # "SB_LEDDA_IP",
        # "SB_RGBA_DRV",
        # "ICESTORM_SPRAM"
    ])

    logger = logging.getLogger("> ")
    logger.info("-----------------------------------------------")
    with open(os.path.join(BUILD_DIR, BUILD_NAME + ".tim"), 'r') as f:
        for line in f:
            if re.search("Max frequency for clock|" + device_utilization, line) and line.find("solved") == -1:
                logger.info(line.replace("\n", ""))

        f.close()
