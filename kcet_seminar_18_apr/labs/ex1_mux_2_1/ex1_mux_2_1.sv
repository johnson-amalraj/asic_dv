// -------------------------------------------------
// File name   : mux_2_1.sv
// Target      : Design a Testbench for 2x1 Mux Using Gates
// Date        : 07-Apr-2024
// Developer   : Johnson Amalraj
// Github Link : https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/mux_2_1.sv
// EDA Link    : https://www.edaplayground.com/x/vnnV
//             : https://www.edaplayground.com/x/p4ND
// -------------------------------------------------

//-------------------------------------
// Design Under Test
//-------------------------------------
module mux_2x1 (input logic a, b, sel, output logic y);

  assign y = (sel) ? b : a; // simple logic for 2x1 Mux using Gate
    
endmodule

//-------------------------------------
// Testbench
//-------------------------------------
module testbench_mux_2x1;

  // Declare signals for testbench
  logic a, b, sel, y;
    
  // Instantiate the 2x1 mux
  mux_2x1 dut (
                .a   (a),
                .b   (b),
                .sel (sel),
                .y   (y)
  );

    // Stimulus generation
    initial begin
      // Test case 1: sel = 0, a = 1, b = 0
      sel = 0; a = 1; b = 0;
      #10;
      $display("Test Case 1: sel = %b, a = %b, b = %b, y = %b", sel, a, b, y);
          
      // Test case 2: sel = 1, a = 1, b = 0
      sel = 1; a = 1; b = 0;
      #10;
      $display("Test Case 2: sel = %b, a = %b, b = %b, y = %b", sel, a, b, y);
        
      // Test case 3: sel = 0, a = 0, b = 1
      sel = 0; a = 0; b = 1;
      #10;
      $display("Test Case 3: sel = %b, a = %b, b = %b, y = %b", sel, a, b, y);
          
      // Test case 4: sel = 1, a = 0, b = 1
      sel = 1; a = 0; b = 1;
      #10;
      $display("Test Case 4: sel = %b, a = %b, b = %b, y = %b", sel, a, b, y);
          
      // TODO Add more test cases as needed
          
      // End simulation
      $finish;
    end

    // Waveform generation
    initial begin
      // Open waveform dump file
      $dumpfile("waveform.vcd");
          
      // Dump variables to waveform dump file
      $dumpvars();
    end
endmodule
