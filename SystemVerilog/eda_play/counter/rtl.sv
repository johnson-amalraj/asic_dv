// Code your design here
module counter(clk, reset, enable, count_in, count_out);
  input clk, reset, enable;
  input [3:0] count_in;
  output [3:0] count_out;
  
  reg [3:0] counter;
  
  initial begin
    counter = 0;
  end
  
  always @ (posedge clk) begin
    if (reset == 1) begin
      counter <= 0;
    end
    else begin
      counter <= count_in + counter;
    end
  end
  
  assign count_out = counter;
  
endmodule
