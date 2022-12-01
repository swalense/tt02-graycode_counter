"""
Simple test case wrapper inspired by that of LUNA (https://github.com/greatscottgadgets/luna)
"""

import logging
import os
import unittest

from functools import wraps

from amaranth.sim import Simulator

import hdl.config as config


def test_case(process_function):
    def run_test(self):

        @wraps(process_function)
        def wrapped_test_case():
            yield from process_function(self)

        self.sim.add_sync_process(wrapped_test_case)

        # Set GENERATE_VCDS=0 to disable VCDs
        if os.getenv("GENERATE_VCDS", default="1") != "0":
            with self.sim.write_vcd("test_{}.vcd".format(self.__class__.__name__)):
                self.sim.run()
        else:
            self.sim.run()

    return run_test


class TestCase(unittest.TestCase):

    def instantiate_dut(self):
        pass

    def setUp(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.dut = self.instantiate_dut()

        self.sim = Simulator(self.dut)
        self.sim.add_clock(1 / config.CLOCK_FREQ)


if __name__ == "__main__":

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.discover(".", pattern="*.py", top_level_dir="."))

    runner = unittest.TextTestRunner()
    runner.run(suite)
