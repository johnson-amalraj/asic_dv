// -------------------------------------------------
// File name   : scoreboard.sv
// Target      : Implementation of Scoreboard for a Simple DUT
// Description : A scoreboard is typically used in verification environments to compare the expected outputs from a DUT (Design Under Test) against the actual outputs. 
//               Below is an example implementation of a scoreboard for a simple DUT in SystemVerilog along with a testbench to demonstrate its usage:
// Date        : 07-Apr-2024
// Developer   : Johnson Amalraj
// Github Link : https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/scoreboard.sv
// -------------------------------------------------

//-------------------------------------
// Design Under Test
//-------------------------------------
module DUT (
  input [7:0] a,
  input [7:0] b,
  output reg [7:0] sum
);

    // Adder logic
    always @(a, b)
      sum <= a + b;

endmodule

//-------------------------------------
// Testbench 
//------------------------------------
module Scoreboard;
  reg [7:0] a, b;   // Inputs to DUT
  reg [7:0] expected_sum;
  wire [7:0] actual_sum;

    // Instantiate DUT
    DUT dut_instance (
        .a(a),
        .b(b),
        .sum(actual_sum)
    );

    // Generate test vectors
    initial begin
      // Test case 1
      a = 8;
      b = 4;
      expected_sum = 12;
      #10;  // Wait for some time to let DUT calculate the sum
      if (actual_sum != expected_sum)
        $display("Test case 1 failed: Expected sum = %d, Actual sum = %d", expected_sum, actual_sum);
      else
        $display("Test case 1 passed");

      // Test case 2
      a = 10;
      b = 20;
      expected_sum = 30;
      #10;
      if (actual_sum != expected_sum)
        $display("Test case 2 failed: Expected sum = %d, Actual sum = %d", expected_sum, actual_sum);
      else
        $display("Test case 2 passed");
        
    end
  
    // Waveform generation
    initial begin
      // Open waveform dump file
      $dumpfile("waveform.vcd");
        
      // Dump variables to waveform dump file
      $dumpvars(0, DUT);
    end

endmodule
