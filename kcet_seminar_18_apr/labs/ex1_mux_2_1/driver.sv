//-------------------------------------------------------------------------
//						
//-------------------------------------------------------------------------
// gets the packet from generator and drive the transaction paket items into interface (interface is connected to DUT, so the items driven into interface signal will get driven in to DUT) 

`define DRIV_IF mux_vif.DRIVER.driver_cb
class driver;
  
  // used to count the number of transactions
  int no_transactions;
  
  // creating virtual interface handle
  virtual mux_intf mux_vif;
  
  // creating mailbox handle
  mailbox gen2driv;
  
  // constructor
  function new(virtual mux_intf mux_vif,mailbox gen2driv);
    // getting the interface
    this.mux_vif  = mux_vif;
    // getting the mailbox handles from  environment 
    this.gen2driv = gen2driv;
  endfunction
  
  // Reset task, Reset the Interface signals to default/initial values
  task reset;
    wait(mux_vif.reset);
    $display("--------- [DRIVER] Reset Started ---------");
    `DRIV_IF.a   <= 0;
    `DRIV_IF.b   <= 0;
    `DRIV_IF.sel <= 0;
    wait(!mux_vif.reset);
    $display("--------- [DRIVER] Reset Ended ---------");
  endtask
  
  // drivers the transaction items to interface signals
  task main;
    forever begin
      transaction trans;
      `DRIV_IF.a   <= 0;
      `DRIV_IF.b   <= 0;
      `DRIV_IF.y   <= 0;
      `DRIV_IF.sel <= 0;
      gen2driv.get(trans);
      $display("--------- [DRIVER-TRANSFER: %0d] ---------",no_transactions);
      @(posedge mux_vif.DRIVER.clk);
        `DRIV_IF.a <= trans.a;
      if(trans.sel) begin
        `DRIV_IF.a <= trans.a;
        `DRIV_IF.b <= trans.b;
        $display("\t A = %0h \t B = %0h \t SEL = %0h \t Y = %0h",trans.a, trans.b, trans.sel, trans.y);
        @(posedge mux_vif.DRIVER.clk);
      end
      $display("-----------------------------------------");
      no_transactions++;
    end
  endtask
  
endclass
