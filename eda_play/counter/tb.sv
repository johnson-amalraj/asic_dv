module counter_tb; // This is TB to test our design
  // wire to connect the design output
  wire [3:0] count_out;
  // reg to connect the design input
  reg clk, reset;
  reg [3:0] count_in;
  
  // connecting the design to our TB
  counter C1(clk, reset, count_in, count_out);
  
  initial begin
    // to see as a waveform
    $dumpfile("sim.vcd");
    $dumpvars(1);
    // initial values
    clk=0; reset=1;
    // setting some delay before start to count
    #5;
    // reset off and starting counter
    reset=0; count_in = 1;
    // counter will run upto 50ns
    #50;
    // then finish the run
    $finish(1);
  end
  
  // Clock generation
  always begin
    #5;
    clk = ~clk;
  end
  
  // using monitor function to see the values in logs
  initial begin
    $monitor ("clk = %b, reset = %b, count_in = %b, count_out = %d", clk, reset, count_in, count_out);
  end
  
endmodule
