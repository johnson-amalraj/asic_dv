import cocotb
from cocotb.triggers import RisingEdge, Timer
import ml_agent
import json

@cocotb.test()
async def test_alu_ml(dut):
    # reset
    dut.rst_n <= 0
    dut.clk <= 0
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.rst_n <= 1

    # simple clock generator
    cocotb.start_soon(clock_gen(dut.clk))

    for i in range(50):
        # create fake coverage
        cov = {"uncovered_bins": ["add_zero"] if i%7==0 else []}
        with open('/tmp/coverage.json','w') as f:
            json.dump(cov, f)
        # ask ml_agent for next stimulus
        import subprocess
        subprocess.run(["python3","ml_agent.py","/tmp/coverage.json","/tmp/next_stim.json"] )
        with open('/tmp/next_stim.json') as f:
            line = f.readline().strip()
        op,a,b = [int(x) for x in line.split(',')]
        dut.op <= op
        dut.a <= a
        dut.b <= b
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        # sample output
        y = int(dut.y)
        # optional: basic check
        if op == 0:
            assert y == ((a + b) & 0xFF)

async def clock_gen(clk):
    while True:
        clk <= 0
        await Timer(5, 'ns')
        clk <= 1
        await Timer(5, 'ns')