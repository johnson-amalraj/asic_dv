// ====================================================
/*
Project:     transactor
Engg Name:   johnson amalraj
File name:   env.sv
Description: this is the env file for transactor model
TODO :       Need to add the initate the master and slave
*/
// ====================================================

`include "master.sv"
`include "slave.sv"
`include "checker.sv"

class environment;
  
  master  master_o;         // Instance for Master
  slave   slave_o;          // Instance for slave
  checker checker_o;        // Instance for checker

  virtual intf master_vif;  // Virtual interface for master
  virtual intf slave_vif;   // Virtual interface for slave 
  virtual intf checker_vif; // Virtual interface for chekcer 

  // mailbox gen2driv;     // Mailbox handle's
  // event   gen_ended;    // Event for synchronization between generator and test
  
    // Constructor
    function new(virtual intf mst_vif, virtual intf slv_intf);
      // Get the interface from test
      this.master_vif  = master_vif;
      this.slave_vif   = slave_vif;
      this.checker_vif = master_vif;
      
      // // creating the mailbox (Same handle will be shared across generator and driver)
      // gen2driv = new();
      
      // creating generator and driver
      // gen = new(gen2driv,gen_ended);

      // Creating the required objects
      master_o  = new(master_vif);
      slave_o   = new(slave_vif);
      checker_o = new(checker_vif);
    endfunction

    // Calling start_sim of all bfm's
    task start_sim();
      $display("--------- [ENV] start_sim ---------");
      fork 
        begin
          master_o.start_sim();
        end
        begin
          slave_o.start_sim();
        end
        begin
          checker_o.start_sim();
        end
      join
    endtask
  
endclass
