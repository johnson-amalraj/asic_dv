// ====================================================
/*
Project:     transactor
Engg Name:   johnson amalraj
File name:   slave.sv
Description: this is the slave file for transactor model
TODO :       Need to add the template
*/
// ====================================================

`include "includes/defines.sv"
`include "slave_bfm.sv"

class slave;
  
  fsm_state slave_state;   // Variable for slave_fsm
  fsm_state p_slave_state; // Variable for past slave_fsm

  virtual   intf slv_vif; // Virtual interface handle
  // mailbox gen2driv; // Creating mailbox handle
    
  bit       clk_en;       // Variable for clk_en
  int       trans_cnt;    // Variable for transactions count

    // Constructor
    function new (virtual intf slave_vif);

      // Getting the interface
      this.slv_vif = slave_vif;

      // //getting the mailbox handle from  environment 
      // this.gen2driv = gen2driv;
    endfunction
    
    // start_sim
    task start_sim();

      $display("--------- [SLAVE] start_sim ---------");

      fork // start_sim fork_join

        begin // slave_bfm
          slave_bfm();
        end // slave_bfm

      join // start_sim fork_join

    endtask // start_sim

endclass
