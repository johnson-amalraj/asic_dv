// ====================================================
/*
Project:     transactor
Engg Name:   johnson amalraj
File name:   test.sv
Description: this is the test file for transactor model
TODO :       Need to connect the top and testbench
*/
// ====================================================
`include "environment.sv"
program test
(
  intf mst_intf,
  intf slv_intf,
);
  
    // Declaring environment instance
    environment env;
  
    initial begin
      // Creating environment
      env = new(mst_intf, slv_intf);
      
      // Setting the repeat count of generator as 10, means to generate 10 packets
      // env.gen.repeat_count = 10;
      
      // Calling run of env, it interns calls generator and driver main tasks.
      env.run();
    end

endprogram