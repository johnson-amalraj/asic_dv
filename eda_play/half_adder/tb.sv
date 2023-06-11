// Code your testbench here
// or browse Examples
module ha_tb;
  wire sum, carry;
  reg a,b;
  
  ha h1(a, b, sum, carry);
  
  initial begin
    $dumpfile("add.vcd");
    $dumpvars(1);
    a=0; b=0;
    #5;
    a=0; b=1;
    #5;
    a=1; b=0;
    #5;
    a=1; b=1;
    #5;
  end
  
endmodule
