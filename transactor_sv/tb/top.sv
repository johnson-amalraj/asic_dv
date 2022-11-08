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

`include "interface.sv" // include the interface file
`include "../test_lib/asic_basic_test.sv" // include the basic test

module ja_top; 

  // Declartion of variables 
  bit clk;   // Variable for clk
  bit rst_n; // Variable for rst_n

    // Block for reset release
    initial begin // intial value assign
      clk   = 0;
      rst_n = 1;
      #(10ns) // wait for 10ns to release the rst_n
      rst_n = 0;
    end

    // Block for Clock genertion
    always begin // always block for clock gen 
      if (rst_n == 0) begin // if loop for rst_n assert check
        #(5ns) // delay in ns for clock frequency 
        clk = !clk; // toggle clock
      end // if loop rst_n asserted
    end // always loop

    // Connecting master interface
    intf master_intf
    (
      .clk     (clk),
      .rst_n   (rst_n),
      .sel     (sel),
      .en      (en),
      .addr    (addr),
      .wr_data (wr_data),
      .rd_data (rd_data),
      .wr_en   (wr_en),
    );

    // Connecting slave interface
    intf slave_intf 
    (
      .clk     (clk),
      .rst_n   (rst_n),
      .sel     (sel),
      .en      (en),
      .addr    (addr),
      .wr_data (wr_data),
      .rd_data (rd_data),
      .wr_en   (wr_en),
    );

    // Testcase instance, interface handle is passed to test as an argument
    test test_u1(master_intf, slave_intf);

    // Enabling the wave dump
    initial begin 
      $dumpfile("dump.vcd"); $dumpvars;
    end

endmodule