//-------------------------------------------------------------------------
//				
//-------------------------------------------------------------------------
// mux_tb_top or testbench top, this is the top most file, in which DUT(Design Under Test) and Verification environment are connected. 
//-------------------------------------------------------------------------

// including interfcae and testcase files
`include "interface.sv"

//-------------------------[NOTE]---------------------------------
// Particular testcase can be run by uncommenting, and commenting the rest
`include "basic_test.sv"
//----------------------------------------------------------------

module mux_tb_top;
  
  //clock and reset signal declaration
  bit clk;
  bit reset;
  
  //clock generation
  always #1 clk = ~clk;
  
  //reset Generation
  initial begin
    reset = 1;
    #5;
    reset = 0;
  end
  
  //creatinng instance of interface, inorder to connect DUT and testcase
  mux_intf intf(clk,reset);
  
  //Testcase instance, interface handle is passed to test as an argument
  test t1(intf);
  
  //DUT instance, interface signals are connected to the DUT ports
  mux MUX (
    .clk   (intf.clk),
    .reset (intf.reset),
    .a     (intf.a),
    .b     (intf.b),
    .sel   (intf.sel),
    .y     (intf.y)
   );
  
  //enabling the wave dump
  initial begin 
    $dumpfile("dump.vcd");

    // Dump variables to waveform dump file
    $dumpvars();
  end
endmodule
