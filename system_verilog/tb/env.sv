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
  
  // Declaration of variables
  master  master_o;     // Instance for Master
  slave   slave_o;      // Instance for slave
  checker checker_o;    // Instance for slave

  virtual intf master_vif; // Virtual interface for master
  virtual intf slave_vif;  // Virtual interface for slave 

  // mailbox gen2driv;     // Mailbox handle's
  // event   gen_ended;    // Event for synchronization between generator and test
  
    // Constructor
    function new(virtual intf mst_vif, virtual intf slv_intf);
      // Get the interface from test
      this.master_vif = master_vif;
      this.slave_vif  = slave_vif;
      
      // // creating the mailbox (Same handle will be shared across generator and driver)
      // gen2driv = new();
      
      // creating generator and driver
      // gen = new(gen2driv,gen_ended);
      master_o = new(master_vif);
      slave_o  = new(slave_vif);
    endfunction

    task pre_test();
      master_o.reset();
    endtask
  
    task test();
      fork 
        begin
          // gen.main();
          master_o.main();
        end
        begin
          slave_o.main();
        end
      join_any
    endtask
  
    task post_test();
      // wait(gen_ended.triggered);
      // wait(gen.repeat_count == driv.no_transactions);
    endtask  
  
    // run task
    task run;
      pre_test();
      test();
      post_test();
      $finish;
    endtask
  
endclass