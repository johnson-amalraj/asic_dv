Design a Testbench for 2x1 Mux Using Gates
module mux_2x1 (input logic a, b, sel,
                 output logic y);

    assign y = (sel) ? b : a;
    
endmodule

module testbench_mux_2x1;
    // Declare signals for testbench
    logic a, b, sel, y;
    
    // Instantiate the 2x1 mux
    mux_2x1 dut (
        .a(a),
        .b(b),
        .sel(sel),
        .y(y)
    );

    // Stimulus generation
    initial begin
        // Test case 1: sel = 0, a = 1, b = 0
        sel = 0; a = 1; b = 0;
        #10;
        $display("Test Case 1: sel = %b, a = %b, b = %b, y = %b", sel, a, b, y);
        
        // Test case 2: sel = 1, a = 1, b = 0
        sel = 1; a = 1; b = 0;
        #10;
        $display("Test Case 2: sel = %b, a = %b, b = %b, y = %b", sel, a, b, y);
        
        // Test case 3: sel = 0, a = 0, b = 1
        sel = 0; a = 0; b = 1;
        #10;
        $display("Test Case 3: sel = %b, a = %b, b = %b, y = %b", sel, a, b, y);
        
        // Test case 4: sel = 1, a = 0, b = 1
        sel = 1; a = 0; b = 1;
        #10;
        $display("Test Case 4: sel = %b, a = %b, b = %b, y = %b", sel, a, b, y);
        
        // Add more test cases as needed
        
        // End simulation
        $finish;
    end
endmodule

This testbench instantiates the 2x1 mux module and applies different combinations of inputs (a, b, sel) to verify its functionality. Adjust the delays (#10) as needed depending on your simulation time unit. You can add more test cases to further validate the design.
