// Top-level testbench module
module top;
  // Instantiate agents
  mst_agnt mst(clk, reset, data_out, data_in);
  slv_agnt slv(clk, reset, data_out, data_in);
  
  // Define clock and reset signals
  reg clk = 0;
  reg reset = 1;
  
  // Connect clock and reset signals to agents
  always #5 clk = ~clk;

  initial begin
    #20 reset = 0;
  end

  // // Connect data signals between agents
  // wire [7:0] data1_out;
  // wire [7:0] data1_in;
  // wire [7:0] data2_out;
  // wire [7:0] data2_in;
  // assign data1_out = a1.data_out;
  // assign data2_in = a1.data_out;
  // assign data2_out = a2.data_out;
  // assign data1_in = a2.data_out;
  
  // Testbench code here
endmodule
