/////////////////////////////////////////////////////////////////////////////////
//                  CONFIDENTIAL AND PROPRIETARY INFORMATION
//             (C) 2004 Synopsys Inc (Unpublished) and Chris Spear
//                             All Rights Reserved
//
// This file can be freely distributed providing this (C) notice remains
/////////////////////////////////////////////////////////////////////////////////

/*
  region.vr - code to mimic the OpenVera region construct.  For use
  in Native Testbench which does support region, as of VCS 7.2,  9/2004
*/

class RegionRecord;
  event e;
  int use_count = 0;
endclass


class Region;
   typedef enum {WAIT, NO_WAIT} WAIT_E;
   
  RegionRecord rr[*];  // Holds event index
  string name;

  // Specify a name for the region, default is none
   function new(string name="");
    this.name = name;
  endfunction

   task region_enter(input WAIT_E wait_e, bit [63:0] index);

    // Has the requested index ever being used?
    if (rr[index] == null) begin
       // Not in use, allocate a new one
       rr[index] = new();
       rr[index].use_count = 1;
       // region_enter = 1;
    end
    else begin
      // index has been allocated, is it in use?
      if (wait_e == WAIT) begin
        rr[index].use_count++;  // Mark it as still in use, even after other thread finishes
        if (rr[index].use_count>1) 
          wait (rr[index].e.triggered);
         // region_enter = 1;
      end
       // NO_WAIT, function value is in-use status
       // else region_enter = (rr[index].use_count == 0);
    end // else: !if(rr[index] == null)
   endtask : region_enter


  task region_exit(int index);
    if (rr[index] == null) begin
       $display("ERROR: %m region_exit does not have an entry for value %0d", index);
       $finish;
    end
    else begin
      if (rr[index].use_count>0) begin
        -> rr[index].e;
        rr[index].use_count--;
      end
      else
        $display("%m region_exit called but value %0d not in use", index);
    end // else: !if(rr[index] == null)
  endtask : region_exit


   task display();
      int i;

      $display("Contents of region %s", name);
      if (rr.first(i))
	foreach (rr[i])
	  $display("\nregion[%0d] use_count=%0d\n", i, rr[i].use_count);
    else $display("\nregion empty");
  endtask : display
endclass : Region
