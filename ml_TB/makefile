# Minimal Makefile to run cocotb tests with Verilator
# Requirements: verilator, cocotb (pip install cocotb), python3

SIM=verilator
TOPLEVEL=simple_fifo
MODULE=cocotb_test_fifo
TOPLEVEL_LANG=verilog
VERILATOR_ARGS=-Wno-fatal

# Ensure cocotb-config exists
ifeq (,$(shell which cocotb-config 2>/dev/null))
$(error cocotb-config not found in PATH; install cocotb and ensure cocotb-config is in PATH)
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: all sim clean
all: sim

clean:
	rm -rf sim_build