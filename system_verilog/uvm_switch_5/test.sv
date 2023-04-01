////////////////////////////////////////////////
////s~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~s////
////s           www.testbench.in           s////
////s                                      s////
////s              UVM Tutorial            s////
////s                                      s////
////s            gopi@testbench.in          s////
////s~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~s////
//////////////////////////////////////////////// 
class test1 extends uvm_test;

    `uvm_component_utils(test1)

     Environment t_env ;

    function new (string name="test1", uvm_component parent=null);
        super.new (name, parent);
        t_env = new("t_env",this);
    endfunction : new 

    virtual task run ();
       #3000ns;
       global_stop_request();
    endtask : run 

endclass : test1


