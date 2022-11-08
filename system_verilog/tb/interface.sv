// ====================================================
/*
Project:     transactor
Engg Name:   johnson amalraj
File name:   interface.sv
Description: this is the interface file for transactor model
TODO :       Need to declare the required interface signals
*/
// ====================================================
interface intf (input logic clk,reset);
  
  logic clk;            // Signal for clk
  logic rst_n;          // Signal for rst_n
  logic sel;            // Signal for sel
  logic en;             // Signal for enable
  logic [16:0] addr;    // Signal for addr
  logic [31:0] wr_data; // Signal for wr_data
  logic [31:0] rd_data; // Signal for rd_data
  logic wr_en;          // Signal for wr_en
  
    // Clocking block for master
    clocking master_cb @(posedge clk);
      default input #1 output #1;
      output sel;
      output en;
      output addr;
      output wr_data;
      output rd_data;
      output wr_en;
    endclocking
  
    // Clocking block for slave
    clocking slave_cb @(posedge clk);
      default input #1 output #1;
      output sel;
      output en;
      output addr;
      output wr_data;
      output rd_data;
      output wr_en;
    endclocking
  
    // Master modport
    modport master (clocking master_cb, input clk, rst_n);
  
    // Slave modport
    modport slave (clocking slave_cb, input clk, rst_n);
  
endinterface