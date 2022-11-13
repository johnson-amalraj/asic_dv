// ====================================================
/*
Project:     transactor
Engg Name:   johnson amalraj
File name:   master.sv
Description: this is the master file for transactor model
TODO :       Need to add the template
*/
// ====================================================

`include "includes/defines.sv"
`include "master_bfm.sv"

class master;
  
  fsm_state master_state;   // Variable for master_fsm
  fsm_state p_master_state; // Variable for past master_fsm

  virtual   intf mst_vif;   // Virtual interface handle
    
  bit       clk_en_b;       // Variable for clk_en_b
  int       trans_cnt;      // Variable for transactions count

    // --------------------------
    // Constructor
    // --------------------------
    function new (virtual intf master_vif);
      // Getting the interface
      this.mst_vif = master_vif;
    endfunction
    
    // --------------------------
    // start_sim
    // --------------------------
    task start_sim();
      $display("--------- [MASTER] start_sim ---------");
      fork // start_sim fork_join
        begin // clk_gen
          clk_gen();
        end // clk_gen
        begin // master_bfm
          master_bfm();
        end // master_bfm
      join // start_sim fork_join
    endtask // start_sim

    // --------------------------
    // task for clk_gen 
    // --------------------------
    task clk_gen();
      bit m_clk_b; // Variable for clock bit change

      m_clk_b = `LOW;
      forever begin // start clk_gen
        if (clk_en_b == `HIGH) begin // start clk_gen if clk_en_b as 1
          $display("--------- [MASTER] clk gen started ---------");
          #10ns;
          mst_vif.clk = m_clk_b;
          m_clk_b     = m_clk_b+1;
        end // if check for clk_en_b 
      end // clk_gen forever loop 
    endtask // clk_gen task

endclass
