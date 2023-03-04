// Code your testbench here
// or browse Examples
module counter_tb;
  wire [3:0] count_out;
  reg clk, reset, enable;
  reg [3:0] count_in;
  
  counter C1(clk, reset, enable, count_in, count_out);
  
  initial begin
    $dumpfile("count.vcd");
    $dumpvars(1);
    clk=0; reset=1;
    #5;
    reset=0; count_in = 1;
    #50;
    $finish(1);
  end
  
  always begin
    #5;
    clk = ~clk;
  end
  
  initial begin
    $monitor ("clk = %b, reset = %b, enable = %b, count_in = %b, count_out = %d", clk, reset, enable, count_in, count_out);
  end
  
endmodule
