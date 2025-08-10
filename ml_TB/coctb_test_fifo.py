import cocotb
from cocotb.triggers import RisingEdge, Timer
import json, subprocess

@cocotb.test()
async def test_fifo_ml(dut):
    cocotb.start_soon(clock_gen(dut.clk))
    dut.rst_n <= 0
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.rst_n <= 1

    for i in range(200):
        # fake coverage
        cov = {"uncovered_bins": []}
        if i%13==0:
            cov['uncovered_bins'].append('fifo_full')
        with open('/tmp/coverage.json','w') as f:
            json.dump(cov, f)
        subprocess.run(["python3","ml_agent.py","/tmp/coverage.json","/tmp/next_stim.json"])
        with open('/tmp/next_stim.json') as f:
            line = f.readline().strip()
        # Interpret ml output as: op,a,b  -> map to wr/rd/din
        op,a,b = [int(x) for x in line.split(',')]
        if op % 2 == 0:
            # write
            dut.wr_en <= 1
            dut.rd_en <= 0
            dut.din <= a & 0xFF
        else:
            dut.wr_en <= 0
            dut.rd_en <= 1
        await RisingEdge(dut.clk)
        dut.wr_en <= 0; dut.rd_en <= 0
        await RisingEdge(dut.clk)

async def clock_gen(clk):
    while True:
        clk <= 0
        await Timer(5, 'ns')
        clk <= 1
        await Timer(5, 'ns')