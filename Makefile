# Ensure this ID is unique per-project.
TOP=swalense_top
HDL_DIR=hdl

verilog:
	# Instead of fetching verilog, build it with Amaranth.
	PYTHONPATH=. TOP=$(TOP) python3 $(HDL_DIR)/verilog_convert.py > src/$(TOP).v
# echo "read_verilog $(HDL_DIR)/$(TOP)_hierarchical.v; hierarchy -top $(TOP); proc; flatten; opt_clean -purge; write_verilog src/$(TOP).v" | yosys

src: FORCE
	$(MAKE) -C src

# needs PDK, PDK_ROOT and OPENLANE_ROOT, OPENLANE_IMAGE_NAME set from your environment
harden:
	docker run --rm \
	-v $(OPENLANE_ROOT):/openlane \
	-v $(PDK_ROOT):$(PDK_ROOT) \
	-v $(CURDIR):/work \
	-e PDK_ROOT=$(PDK_ROOT) \
	-e PDK=$(PDK) \
	-u $(shell id -u $(USER)):$(shell id -g $(USER)) \
	$(OPENLANE_IMAGE_NAME) \
	/bin/bash -c "./flow.tcl -verbose 2 -overwrite -design /work/src -run_path /work/runs -tag wokwi"

FORCE:
