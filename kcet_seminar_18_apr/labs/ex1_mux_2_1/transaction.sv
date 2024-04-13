//-------------------------------------------------------------------------
//						
//-------------------------------------------------------------------------
class transaction;
  // declaring the transaction items
  rand bit a;
  rand bit b;
  rand bit sel;
  //     bit y;
  
  // constaint, to generate any one among write and read
  constraint valid_sel {
    sel inside {[0:1]};
  }

  // constraint y_definition {
  //   y == (sel ? b : a); // Output y depends on the value of sel
  // }

  constraint a_and_b_different {
    a != b; // Ensure a and b are different
  }

  // postrandomize function, displaying randomized values of items 
  function void post_randomize();
    $display("--------- [Trans] post_randomize ------");
    $display("\t a   = %0b", a);
    $display("\t b   = %0b", b);
    $display("\t sel = %0b", sel);
    // $display("\t y   = %0b", y);
    // if(wr_en) $display("\t wr_en = %0h\t wdata = %0h",wr_en,wdata);
    $display("-----------------------------------------");
  endfunction
  
endclass
