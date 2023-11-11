brew install icarus-verilog
brew install --cask gtkwave

iverilog -g2012 -o sim tb.sv rtl.sv
vvp sim
gtkwave .vcd &