Region class for use with SystemVerilog

INTRODUCTION:

The OpenVera region is not supported in SystemVerilog, so this class
is provided as a substitute.  Compile this class along with the rest
of the testbench.


INITIALIZATION:

The following code creates a single region:

    int regionID;
    regionID = alloc(REGION, 0, 1);

The equivalent code in SystemVerilog is:

    Region regionID;
    regionID = new();  // No name given

A name can be passed to new() for use in the display task.


USAGE:

Use a region to reserve a value, blocking if in use:

    region_enter(WAIT, regionID, value);  // Vera
and
    regionID.region_enter(Region::WAIT, value);   // SystemVerilog


Use a region to reserve a value, checking status:

    status = region_enter(NO_WAIT, regionID, value);  // Vera
and
    regionID.region_enter(Region::NO_WAIT, value);   // SystemVerilog


Leave a region:
:q

   region_exit(regionID, value);   // Vera
and
   regionID.region_exit(value);    // SystemVerilog


Display the currently reserved value:

   regionID.display();   // Only in SystemVerilog
