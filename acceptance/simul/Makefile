# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES += *.v ../../src/swalense_top.v

# TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
TOPLEVEL = simul

# MODULE is the basename of the Python test file
MODULE = simul

COMPILE_ARGS += -DMPRJ_IO_PADS=38

WAVES = 1
PLUSARGS += -lxt2

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
