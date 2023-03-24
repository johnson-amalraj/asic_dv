module top;

  // Declare signals
  logic clk;
  logic reset_n;
  logic data_in;
  logic data_out;

  // Instantiate the DUT
  my_module dut (
    .clk(clk),
    .reset_n(reset_n),
    .data_in(data_in),
    .data_out(data_out)
  );

  // Instantiate the interface
  my_if my_interface (
    .clk(clk),
    .reset_n(reset_n),
    .data_in(data_in),
    .data_out(data_out)
  );

  initial begin
    // Initialize signals
    clk = 1'b0;
    reset_n = 1'b1;
    data_in = 1'b0;

    // Toggle the clock
    forever #5 clk = ~clk;
  end

endmodule


// In this example, we declare four signals: clk, reset_n, data_in, and data_out. We then instantiate the DUT (design under test) module called my_module and connect its inputs and outputs to the signals. We also instantiate an interface called my_if and connect its inputs and outputs to the same signals.

// In the initial block, we initialize the signals and start toggling the clock signal every 5 time units using an infinite loop (forever). The ~ operator toggles the signal from 0 to 1 and vice versa.

// Note that this is just a simple example and in a real-world design, the top-level module would contain many more components and interfaces.
