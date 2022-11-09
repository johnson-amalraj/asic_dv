// ====================================================
/*
Project:     transactor
Engg Name:   johnson amalraj
File name:   checker.sv
Description: this is the checker file for transactor model
TODO :       Need to add the template
*/
// ====================================================
`include "includes/defines.sv"

class checker;

  virtual   intf chk_vif; // Virtual interface handle

  bit       clk_en;       // Variable for clk_en
  int       trans_cnt;    // Variable for transactions count

    // Constructor
    function new (virtual intf checker_vif);

      // Getting the interface
      this.chk_vif = checker_vif;

    endfunction

    // start_sim
    task start_sim();

      $display("--------- [CHECKER] start_sim ---------");

      fork // start_sim fork_join

        // begin // clk_gen
        // end // clk_gen

        // begin // master_bfm
        // end // master_bfm

      join // start_sim fork_join

    endtask // start_sim

endclass