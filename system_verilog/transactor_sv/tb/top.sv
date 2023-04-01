// ====================================================
/*
   Project:     transactor
   Engg Name:   johnson amalraj
   File name:   top.sv
   Description: this is the top file for transactor model
   TODO :       Need to dump waves
                Need to define the timescale
*/
// ====================================================

`include "interface.sv" // include the interface file
`include "../test_lib/asic_basic_test.sv" // include the basic test

module ja_top; 

  // Declartion of variables 
  bit sys_clk_en; // Variable for sys_clk_en
  bit sys_clk;    // Variable for clk
  bit rst_n;      // Variable for rst_n

    // ----------------------------
    // Block to initialize the varaibles
    // ----------------------------
    initial begin // intial block 
      sys_clk_en = 0;
      sys_clk    = 0;
      rst_n      = 1;
      #(5ns) // wait for 5ns to enable the sys_clk_en 
      sys_clk_en = 1;
    end // intitial block

    // ----------------------------
    // Block for Clock genertion
    // ----------------------------
    always begin // always block for clock gen 
      if (sys_clk_en == 1) begin // if sys_clk enable
        #(1ns) // delay in ns for clock frequency 
        sys_clk = !sys_clk; // toggle clock
      end // if loop sys_clk enable
    end // always loop

    // ----------------------------
    // Connecting master interface
    // ----------------------------
    intf master_intf
    (
      .sys_clk (sys_clk),
      .clk     (clk),
      .rst_n   (rst_n),
      .sel     (sel),
      .en      (en),
      .addr    (addr),
      .wr_data (wr_data),
      .rd_data (rd_data),
      .wr_en   (wr_en),
    );

    // ----------------------------
    // Connecting slave interface
    // ----------------------------
    intf slave_intf 
    (
      .sys_clk (sys_clk),
      .clk     (clk),
      .rst_n   (rst_n),
      .sel     (sel),
      .en      (en),
      .addr    (addr),
      .wr_data (wr_data),
      .rd_data (rd_data),
      .wr_en   (wr_en),
    );

    // ----------------------------
    // Testcase instance, interface handle is passed to test as an argument
    // ----------------------------
    test test_u1(master_intf, slave_intf);

    // ----------------------------
    // Enabling the wave dump
    // ----------------------------
    initial begin 
      $dumpfile("dump.vcd"); $dumpvars;
    end

endmodule
