/*
This is design for a counter, it will count+1 every
posedge of clk signal and reset = 0; 
We can configure this to count +1 or +2 by changing
the count_in value 
 */
module counter(clk, reset, count_in, count_out);
  // input signals to the design
  input clk, reset; 
  input [3:0] count_in;
  // output from the design
  output [3:0] count_out;
  
  // reg variable for to store the counter value
  reg [3:0] counter;
  
  // initial block assign as 0, to aviod X propogation
  initial begin
    counter = 0;
  end
  
  // counter logic
  always @ (posedge clk) begin
    // check for reset to start counter
    if (reset == 1) begin 
      counter <= 0;
    end
    else begin
      counter <= count_in + counter;
    end
  end
  // assign reg counter to output of design
  assign count_out = counter;
  
endmodule