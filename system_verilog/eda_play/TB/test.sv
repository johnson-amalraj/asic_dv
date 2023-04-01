module top_test();

  // Instantiate the testbench environment
  my_env env = new();

  // Instantiate the DUT
  my_dut dut = new();

  // Create the test sequence and connect it to the environment
  my_test_sequence test_seq = new();
  test_seq.env = env;

  // Configure the simulation parameters
  initial begin
    $timeformat(-9, 2, " ns", 10);
    $timescale(1ns/1ps);
    $display("Starting simulation...");
    run_test();
  end

endmodule


