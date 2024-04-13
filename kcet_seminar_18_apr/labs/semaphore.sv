// -------------------------------------------------
// File name   : semaphore.sv
// Target      : Implementation and Testing of Semaphore for a Simple DUT
// Description : Semaphore_t is a simple structure representing the semaphore, containing a single bit lock.
//               The acquire() function waits until the semaphore becomes available (i.e., lock is 0) and then sets lock to 1 to acquire the semaphore.
//               The release() function simply sets lock back to 0, indicating that the semaphore is released and available for another process to acquire.
//               The testbench demonstrates the usage of the semaphore by acquiring and releasing it. 
//               You can extend this testbench to simulate more complex scenarios where multiple processes contend for the semaphore or where the semaphore is used to synchronize access to shared resources.
// Date        : 07-Apr-2024
// Developer   : Johnson Amalraj
// Github Link : https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/semaphore.sv
// -------------------------------------------------

//-------------------------------------
// Design Under Test
//-------------------------------------
module Semaphore(
    input logic clk,           // Clock input
    input logic rst,           // Reset input
    input logic released,       // Signal to release the semaphore
    output logic taken         // Output indicating whether the semaphore is taken
);
    typedef enum logic [1:0] {
        IDLE = 2'b00,
        TAKEN = 2'b01,
        BUSY = 2'b11
    } state_t;

    state_t state;              // Semaphore state

    // Sequential logic for semaphore state machine
    always_ff @(posedge clk, posedge rst) begin
        if (rst) 
            state <= IDLE;      // Reset state to IDLE
        else if (released)
            state <= IDLE;      // Release the semaphore
        else if (state == IDLE)
            state <= TAKEN;     // Semaphore is taken
        else if (state == TAKEN)
            state <= BUSY;      // Semaphore is busy
        else
            state <= BUSY;      // Semaphore is busy
    end

    // Output logic
    assign taken = (state != IDLE); // Semaphore is taken if state is not IDLE
endmodule

//-------------------------------------
// Testbench
//-------------------------------------
module Semaphore_Testbench;
    logic clk, rst, released;
    logic taken;

    // Instantiate semaphore module
    Semaphore semaphore_inst (
        .clk(clk),
        .rst(rst),
        .released(released),
        .taken(taken)
    );

    // Clock generation
    always #5 clk = ~clk;

    // Initial stimulus
    initial begin
        clk = 0;
        rst = 1;
        released = 0;
        #10 rst = 0; // Release reset after 10 time units

        // Test case 1: Semaphore should be taken initially
        #20;
        if (!taken)
            $display("Test case 1 failed: Semaphore not taken initially");
        else
            $display("Test case 1 passed");

        // Test case 2: Release semaphore and check if it's released
        released = 1;
        #10 released = 0;
        #20;
        if (taken)
            $display("Test case 2 failed: Semaphore not released");
        else
            $display("Test case 2 passed");

        // Add more test cases as needed
        // ...

        // End simulation
        #10;
        $finish;
    end


    // Waveform generation
    initial begin
      // Open waveform dump file
      $dumpfile("waveform.vcd");
        
      // Dump variables to waveform dump file
      $dumpvars();
    end

endmodule

