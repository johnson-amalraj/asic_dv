// ====================================================
/*
Project:     transactor
Engg Name:   johnson amalraj
File name:   top.sv
Description: this is the top file for transactor model
TODO :       Need to intianiate the master and slave
             Need to connect the interface
             Need to dump waves
             Need to define the timescale
            
*/
// ====================================================
module ja_top 
(
  input clk,
  input rst_n
);

master mst 
(
  .clk      (clk),
  .rst_n    (rst),
  .data_in  (data_in),
  .data_out (data_out),
);

slave slv
(
  .clk      (clk),
  .rst_n    (rst),
  .data_in  (data_in),
  .data_out (data_out),
);

initial begin // intial value assign
  clk   = 0;
  rst_n = 1;
  #(10ns) // wait for 10ns to release the rst_n
  rst_n = 0;
end

always begin // always block for clock gen 
  if (rst_n == 0) begin // if loop for rst_n assert check
    #(5ns) // delay in ns for clock frequency 
    clk = !clk; // toggle clock
  end // if loop rst_n asserted
end // always loop

endmodule