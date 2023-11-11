# Use below comamdn to run script
# python3 runme.py -tb tb -rtl rtl -out run

import sys

# Get command-line arguments
args = sys.argv[1:]

# Initialize variables to store values
rtl_file = None
tb_file = None
out_file = None

# Process arguments
while args:
    arg = args.pop(0)  # Get and remove the first argument

    if arg == '-in_rtl':
        if args:  # Check if there is a value following '-in_rtl'
            rtl_file = args.pop(0)
        else:
            print("Error: Missing value for -in_rtl")

    elif arg == '-in_tb':
        if args:  # Check if there is a value following '-in_tb'
            tb_file = args.pop(0)
        else:
            print("Error: Missing value for -in_tb")

    elif arg == '-out':
        if args:  # Check if there is a value following '-out'
            out_file = args.pop(0)
        else:
            print("Error: Missing value for -out")

# Print or use the captured values
print(f"-in_rtl value: {rtl_file}")
print(f"-in_tb value: {tb_file}")
print(f"-out value: {out_file}")

# iverilog -g2012 -o run.sim tb.sv rtl.sv
# vvp run.sim
iverilog -g2012 -o {out_file}.sim {tb_file}.sv {rtl_file}.sv
vvp {out_file}.sim