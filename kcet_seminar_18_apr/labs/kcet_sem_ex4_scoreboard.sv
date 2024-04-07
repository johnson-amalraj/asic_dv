// -------------------------------------------------
// File name   : kcet_sem_ex3_semaphore.sv
// Target      : Implementation of Scoreboard for a Simple DUT
// Description : The scoreboard_entry_t structure holds the expected and actual outputs for each test case.
//               The add_scoreboard_entry function is used to add entries to the scoreboard.
//               The check_scoreboard function compares the expected and actual outputs and displays the results.
//               The testbench instantiates both the DUT and the scoreboard.
//               It adds expected outputs to the scoreboard, runs the simulation for some time, and then checks the scoreboard to verify the correctness of the DUT's outputs.
//               You can expand this implementation to support multiple test cases and more complex DUT behaviors as needed
//               A scoreboard is typically used in verification environments to compare the expected outputs from a DUT (Design Under Test) against the actual outputs. 
//               Below is an example implementation of a scoreboard for a simple DUT in SystemVerilog along with a testbench to demonstrate its usage:
// Date        : 07-Apr-2024
// Developer   : Johnson Amalraj
// Github Link : https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/kcet_sem_ex4_scoreboard.sv
// -------------------------------------------------
// TODO Need fix

//-------------------------------------
// Scoreboard 
//-------------------------------------
module scoreboard;

  // Define the scoreboard data structure
  typedef struct {
    int expected_output;
    int actual_output;
  } scoreboard_entry_t;

  // Declare an array to hold scoreboard entries
  scoreboard_entry_t scoreboard_entries[];

  // Function to add an entry to the scoreboard
  function void add_scoreboard_entry(int index, int expected, int actual);
    scoreboard_entries[index].expected_output = expected;
    scoreboard_entries[index].actual_output = actual;
  endfunction

  // Function to check the scoreboard
  function void check_scoreboard();
    $display("Scoreboard Results:");
    for (int i = 0; i < scoreboard_entries.size(); i++) begin
      if (scoreboard_entries[i].expected_output == scoreboard_entries[i].actual_output) begin
        $display("Entry %0d: PASSED (Expected: %0d, Actual: %0d)", i, scoreboard_entries[i].expected_output, scoreboard_entries[i].actual_output);
      end
      else begin
        $display("Entry %0d: FAILED (Expected: %0d, Actual: %0d)", i, scoreboard_entries[i].expected_output, scoreboard_entries[i].actual_output);
      end
    end
  endfunction

endmodule

//-------------------------------------
// Design Under Test
//-------------------------------------
module dut(input logic a, b, output logic y);

  // Define the behavior of the DUT
  always_comb begin
    y = a & b; // Simple AND gate
  end

endmodule

//-------------------------------------
// Testbench
//-------------------------------------
module testbench;

  // Instantiate the scoreboard
  scoreboard sb_inst;

  // Instantiate the DUT
  dut dut_inst(.a(1'b1), .b(1'b1), .y());

  // Drive inputs to the DUT
  initial begin
    // Add expected outputs to the scoreboard
    sb_inst.add_scoreboard_entry(0, 1, 1);

    // Wait for some simulation time
    #10;

    // Check the scoreboard
    sb_inst.check_scoreboard();

    // End simulation
    $finish;
  end

  // Waveform generation
  initial begin
    // Open waveform dump file
    $dumpfile("waveform.vcd");
        
    // Dump variables to waveform dump file
    $dumpvars(0, final_result);
  end

endmodule


