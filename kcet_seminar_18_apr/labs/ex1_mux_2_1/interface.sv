//-------------------------------------------------------------------------
//						
//-------------------------------------------------------------------------
interface mux_intf (input logic clk, reset);
  
  // declaring the signals
  logic a;
  logic b;
  logic sel;
  logic y;
  
  // driver clocking block
  clocking driver_cb @(posedge clk);
    default input #1 output #1;
    output a;
    output b;
    output sel;
    input  y;  
  endclocking
  
  // monitor clocking block
  clocking monitor_cb @(posedge clk);
    default input #1 output #1;
    input a;
    input b;
    input sel;
    input y;
  endclocking
  
  // driver modport
  modport DRIVER  (clocking driver_cb,input clk, reset);
  
  // monitor modport  
  modport MONITOR (clocking monitor_cb,input clk, reset);
  
endinterface
