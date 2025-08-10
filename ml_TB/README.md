Requirements:
- Python3
- cocotb installed (pip install cocotb)
- A simulator supported by cocotb (e.g., Verilator). For UVM use a vendor simulator (VCS/ Questa) or any simulator that supports UVM.

Quick run (cocotb examples):
1. Place `alu.sv`, `ml_agent.py`, and `cocotb_test_alu.py` in a folder.
2. Run with your cocotb + simulator flow. Example with Verilator (simplified):
   - use a Makefile wrapper from cocotb examples or follow cocotb docs (https://docs.cocotb.org)

UVM notes:
- The UVM examples assume you can call `python3 ml_agent.py` from $system during simulation. Many simulators allow this (VCS/Questa). If using a restricted environment, replace the $system call with another IPC method.

Security / sandbox note:
- The file-based IPC is for demonstration only. In production, use sockets, DPI, or simulator-supported co-simulation interfaces.


Run steps:
	1.	Install tools:
	•	sudo apt install verilator (or your platform’s package manager)
	•	pip install cocotb
	2.	Put fifo.sv, ml_agent.py, cocotb_test_fifo.py, and this Makefile in the same directory.
	3.	Run make. Cocotb’s build system will compile with Verilator and run the Python test module cocotb_test_fifo.

Notes:
	•	The cocotb test uses the file-IPC to call ml_agent.py (as in earlier examples). That keeps parity with the UVM example while being simple to run.
	•	If you prefer sockets (faster) I can replace the file-based IPC with a small TCP client/server pair.