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
    $display("\t addr  = %0h",addr);
    if(wr_en) $display("\t wr_en = %0h\t wdata = %0h",wr_en,wdata);
    if(rd_en) $display("\t rd_en = %0h",rd_en);
    $display("-----------------------------------------");
  endfunction
  
endclass
