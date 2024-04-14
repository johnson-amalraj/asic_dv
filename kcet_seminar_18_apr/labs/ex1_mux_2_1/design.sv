//-------------------------------------------------------------------------
//				
//-------------------------------------------------------------------------
module mux #() (
    input  clk,
    input  reset,
    input  a,
    input  b,
    input  sel,
    output y 
  ); 

  // Declare y as a reg
  reg y;
  
    always @(posedge clk) begin 
      if (reset == 0) begin
        y = (sel) ? b : a; // simple logic for 2x1 Mux using Gate
      end
      else begin
        y = 0;
      end
    end
   
endmodule

