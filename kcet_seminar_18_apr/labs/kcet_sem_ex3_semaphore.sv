// -------------------------------------------------
// File name   : kcet_sem_ex3_semaphore.sv
// Target      : Implementation and Testing of Semaphore for a Simple DUT
// Description : Semaphore_t is a simple structure representing the semaphore, containing a single bit lock.
//               The acquire() function waits until the semaphore becomes available (i.e., lock is 0) and then sets lock to 1 to acquire the semaphore.
//               The release() function simply sets lock back to 0, indicating that the semaphore is released and available for another process to acquire.
//               The testbench demonstrates the usage of the semaphore by acquiring and releasing it. 
//               You can extend this testbench to simulate more complex scenarios where multiple processes contend for the semaphore or where the semaphore is used to synchronize access to shared resources.
// Date        : 07-Apr-2024
// Developer   : Johnson Amalraj
// Github Link : https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/kcet_sem_ex3_semaphore.sv
// -------------------------------------------------
// TODO Need fix

//-------------------------------------
// Design Under Test
//-------------------------------------
module semaphore;

  // Define semaphore data structure
  typedef struct {
    bit lock;
  } semaphore_t;

  // Declare semaphore variable
  semaphore_t sem;

  // Function to acquire the semaphore
  function void acquire();
    while (sem.lock) begin
      // Wait until the semaphore becomes available
      // Add any additional waiting mechanism here if needed
    end
    sem.lock = 1;
  endfunction

  // Function to release the semaphore
  function void released();
    sem.lock = 0;
  endfunction
endmodule

//-------------------------------------
// Testbench
//-------------------------------------
module testbench;

  // Instantiate semaphore
  semaphore sem_inst;

  // Testbench process to demonstrate semaphore usage
  initial begin
    // Acquire semaphore
    $display("Trying to acquire semaphore...");
    sem_inst.sem.acquire(); // Corrected syntax to access acquire function
    $display("Semaphore acquired.");

    // Add some delay to simulate some processing
    #10;

    // Release semaphore
    $display("Releasing semaphore...");
    sem_inst.sem.released(); // Corrected syntax to access release function
    $display("Semaphore released.");
        
    // End simulation
    $finish;
  end

  // Waveform generation
  initial begin
    // Open waveform dump file
    $dumpfile("waveform.vcd");
        
    // Dump variables to waveform dump file
    $dumpvars(0, sem_inst);
  end
endmodule
