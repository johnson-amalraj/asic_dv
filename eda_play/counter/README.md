brew install icarus-verilog
brew install --cask gtkwave

iverilog -g2012 -o run.sim tb.sv rtl.sv
vvp run.sim
gtkwave .vcd &