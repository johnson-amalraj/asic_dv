// ====================================================
/*
Project:     transactor
Engg Name:   johnson amalraj
File name:   master.sv
Description: this is the master file for transactor model
TODO :       Need to add the template
*/
// ====================================================
class master;
  
  int trnans_cnt; // Variable for transactions count
  virtual intf master_vif; // Virtual interface handle
  // mailbox gen2driv; // Creating mailbox handle
    
    // Constructor
    function new (virtual intf master_vif);
      // Getting the interface
      this.master_vif = master_vif;
      // //getting the mailbox handle from  environment 
      // this.gen2driv = gen2driv;
    endfunction
    
    //Reset task, Reset the Interface signals to default/initial values
    task reset;
      wait(mem_vif.reset);
      $display("--------- [MASTER] Reset Started ---------");
      `DRIV_IF.wr_en <= 0;
      `DRIV_IF.rd_en <= 0;
      `DRIV_IF.addr  <= 0;
      `DRIV_IF.wdata <= 0;        
      wait(!mem_vif.reset);
      $display("--------- [MASTER] Reset Ended---------");
    endtask
    
    //drive the transaction items to interface signals
    task drive;
      forever begin
        transaction trans;
        `DRIV_IF.wr_en <= 0;
        `DRIV_IF.rd_en <= 0;
        gen2driv.get(trans);
        $display("--------- [MASTER-TRANSFER: %0d] ---------",no_transactions);
        @(posedge mem_vif.DRIVER.clk);
          `DRIV_IF.addr <= trans.addr;
        if(trans.wr_en) begin
          `DRIV_IF.wr_en <= trans.wr_en;
          `DRIV_IF.wdata <= trans.wdata;
          $display("\tADDR = %0h \tWDATA = %0h",trans.addr,trans.wdata);
          @(posedge mem_vif.DRIVER.clk);
        end
        if(trans.rd_en) begin
          `DRIV_IF.rd_en <= trans.rd_en;
          @(posedge mem_vif.DRIVER.clk);
          `DRIV_IF.rd_en <= 0;
          @(posedge mem_vif.DRIVER.clk);
          trans.rdata = `DRIV_IF.rdata;
          $display("\tADDR = %0h \tRDATA = %0h",trans.addr,`DRIV_IF.rdata);
        end
        $display("-----------------------------------------");
        no_transactions++;
      end
    endtask
           
  endclass