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
  // mailbox gen2driv; // Creating mailbox handle
    
  bit       clk_en;         // Variable for clk_en
  int       trans_cnt;      // Variable for transactions count

    // Constructor
    function new (virtual intf master_vif);

      // Getting the interface
      this.mst_vif = master_vif;

      // //getting the mailbox handle from  environment 
      // this.gen2driv = gen2driv;
    endfunction
    
    // start_sim
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

    // task for clk_gen 
    task clk_gen();
      bit m_clk_b; // Variable for clock bit change

      m_clk_b = 1'b0;

      while (mst_vif.clk_en) begin // start clk_gen while clk_en

        $display("--------- [MASTER] clk gen started ---------");
        #10ns;
        mst_vif.clk = m_clk_b;
        m_clk_b     = m_clk_b+1;

      end // clk_gen while loop 

    endtask // clk_gen task

endclass