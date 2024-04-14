//-------------------------------------------------------------------------
//						
//-------------------------------------------------------------------------
`include "transaction.sv"
`include "generator.sv"
`include "driver.sv"
class environment;
  
  // generator and driver instance
  generator gen;
  driver    driv;
  
  // mailbox handle's
  mailbox gen2driv;
  
  // virtual interface
  virtual mux_intf mux_vif;
  
  // constructor
  function new(virtual mux_intf mux_vif);
    // get the interface from test
    this.mux_vif = mux_vif;
    
    // creating the mailbox (Same handle will be shared across generator and driver)
    gen2driv = new();
    
    // creating generator and driver
    gen  = new(gen2driv);
    driv = new(mux_vif,gen2driv);
  endfunction
  
  //
  task pre_test();
    driv.reset();
  endtask
  
  task test();
    fork 
      gen.main();
      driv.main();
    join_any
    $display("---------JOHNSON--------------------------------");
  endtask
  
  task post_test();
    wait(gen.ended.triggered);
    wait(gen.repeat_count == driv.no_transactions);
  endtask  
  
  // run task
  task run;
    pre_test();
    test();
    post_test();
    $finish;
  endtask
  
endclass


