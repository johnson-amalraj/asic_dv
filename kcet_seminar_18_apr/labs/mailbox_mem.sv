// -------------------------------------------------
// File name   : mailbox_mem.sv
// Target      : Implementation of a Mailbox by Allocating Memory
// Description : mailbox_memory is an array of mailbox_entry_t structures, which represents the mailbox.
//               num_entries keeps track of the number of entries currently in the mailbox.
//               add_to_mailbox() function adds data to the mailbox if space is available.
//               get_from_mailbox() function retrieves data from the mailbox if available.
//               You can instantiate this module in your testbench to simulate mailbox operations. 
//               Additionally, you can enhance this implementation by adding features like blocking/non-blocking operations, error handling, and more robust memory management, depending on your requirements.
// Date        : 07-Apr-2024
// Developer   : Johnson Amalraj
// Github Link : https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/mailbox_mem.sv
// -------------------------------------------------
// TODO Need fix

//-------------------------------------
// Design Under Test
//-------------------------------------
module mailbox;
  // Define mailbox size
  parameter MAILBOX_SIZE = 10;

  // Variable to track the number of entries in the mailbox
  int num_entries = 0;

  // Define mailbox data structure
  typedef struct {
    int data;
    bit valid;
  } mailbox_entry_t;

  // Declare memory for mailbox
  mailbox_entry_t mailbox_memory[];

  // Function to initialize the mailbox
  function void init_mailbox();
    mailbox_memory = new[MAILBOX_SIZE];
  endfunction

  // Function to add data to the mailbox
  function void add_to_mailbox(int data);
    if (num_entries < MAILBOX_SIZE) begin
      mailbox_memory[num_entries].data = data;
      mailbox_memory[num_entries].valid = 1;
      num_entries++;
    end
    else begin
      $display("Mailbox is full. Cannot add data.");
    end
  endfunction

  // Function to retrieve data from the mailbox
  function int get_from_mailbox();
    int data;

    if (num_entries > 0) begin
      data = mailbox_memory[0].data;
      // Shift remaining entries in the mailbox
      for (int i = 0; i < num_entries - 1; i++) begin
        mailbox_memory[i] = mailbox_memory[i+1];
      end
      num_entries--;
    end
    else begin
      $display("Mailbox is empty. No data to retrieve.");
      data = 0; // Default value
    end
        return data;
    endfunction

endmodule

//-------------------------------------
// Testbench
//-------------------------------------
module mailbox_tb;
  // Instantiate mailbox
  mailbox dut;

  // Define parameters
  parameter int DATA_1 = 10;
  parameter int DATA_2 = 20;
  parameter int DATA_3 = 30;

    // Initialize mailbox and add data
    initial begin
      dut.init_mailbox();

      // Add data to mailbox
      dut.add_to_mailbox(DATA_1);
      dut.add_to_mailbox(DATA_2);
      dut.add_to_mailbox(DATA_3);

      // Retrieve data from mailbox
      $display("Data retrieved from mailbox: %d", dut.get_from_mailbox());
      $display("Data retrieved from mailbox: %d", dut.get_from_mailbox());
      $display("Data retrieved from mailbox: %d", dut.get_from_mailbox());

      // Attempt to retrieve data from empty mailbox
      $display("Data retrieved from mailbox: %d", dut.get_from_mailbox());
    end
endmodule

module mailbox;
    // Define mailbox size
    parameter MAILBOX_SIZE = 10;

    // Define mailbox data structure
    typedef struct {
        int data;
        bit valid;
    } mailbox_entry_t;

    // Declare memory for mailbox
    mailbox_entry_t mailbox_memory[];

    // Variable to track the number of entries in the mailbox
    int num_entries = 0;

    // Function to initialize the mailbox
    function void init_mailbox();
        mailbox_memory = new[MAILBOX_SIZE];
    endfunction

    // Function to add data to the mailbox
    function void add_to_mailbox(int data);
        if (num_entries < MAILBOX_SIZE) begin
            mailbox_memory[num_entries].data = data;
            mailbox_memory[num_entries].valid = 1;
            num_entries++;
        end
        else begin
            $display("Mailbox is full. Cannot add data.");
        end
    endfunction

    // Function to retrieve data from the mailbox
    function int get_from_mailbox();
        int data;
        if (num_entries > 0) begin
            data = mailbox_memory[0].data;
            // Shift remaining entries in the mailbox
            for (int i = 0; i < num_entries - 1; i++) begin
                mailbox_memory[i] = mailbox_memory[i+1];
            end
            num_entries--;
        end
        else begin
            $display("Mailbox is empty. No data to retrieve.");
            data = 0; // Default value
        end
        return data;
    endfunction

endmodule

module testbench;
    // Instantiate mailbox
    mailbox dut;

    // Define parameters
    parameter int DATA_1 = 10;
    parameter int DATA_2 = 20;
    parameter int DATA_3 = 30;

    // Initialize mailbox and add data
    initial begin
        dut = new;
        dut.init_mailbox();

        // Add data to mailbox
        dut.add_to_mailbox(DATA_1);
        dut.add_to_mailbox(DATA_2);
        dut.add_to_mailbox(DATA_3);

        // Retrieve data from mailbox
        $display("Data retrieved from mailbox: %d", dut.get_from_mailbox());
        $display("Data retrieved from mailbox: %d", dut.get_from_mailbox());
        $display("Data retrieved from mailbox: %d", dut.get_from_mailbox());

        // Attempt to retrieve data from empty mailbox
        $display("Data retrieved from mailbox: %d", dut.get_from_mailbox());
    end
endmodule
