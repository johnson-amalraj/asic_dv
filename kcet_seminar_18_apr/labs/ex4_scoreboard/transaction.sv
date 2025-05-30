//-------------------------------------------------------------------------
//						www.verificationguide.com 
//-------------------------------------------------------------------------
class transaction;
  //declaring the transaction items
  rand bit [1:0] addr;
  rand bit       wr_en;
  rand bit       rd_en;
  rand bit [7:0] wdata;
       bit [7:0] rdata;
       bit [1:0] cnt;
  
  //constaint, to generate any one among write and read
  constraint wr_rd_c { wr_en != rd_en; }; 
  
  //postrandomize function, displaying randomized values of items 
  function void post_randomize();
    $display("--------- [Trans] post_randomize ------");
    //$display("\t addr  = %0h",addr);
    if(wr_en) $display("\t addr  = %0h\t wr_en = %0h\t wdata = %0h",addr,wr_en,wdata);
    if(rd_en) $display("\t addr  = %0h\t rd_en = %0h",addr,rd_en);
    $display("-----------------------------------------");
  endfunction
  
  //deep copy method
  function transaction do_copy();
    transaction trans;
    trans = new();
    trans.addr  = this.addr;
    trans.wr_en = this.wr_en;
    trans.rd_en = this.rd_en;
    trans.wdata = this.wdata;
    return trans;
  endfunction
endclass
