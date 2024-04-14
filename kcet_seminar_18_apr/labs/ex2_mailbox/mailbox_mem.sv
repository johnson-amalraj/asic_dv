// -------------------------------------------------
// File name   : mailbox_mem.sv
// Target      : Implementation of a Mailbox by Allocating Memory
// Date        : 07-Apr-2024
// Developer   : Johnson Amalraj
// Github Link : https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/mailbox_mem.sv
// EDA Link    : https://www.edaplayground.com/x/YjRS
// -------------------------------------------------
// Can use the same program from the mux_2_1

//-------------------------------------
// Design Under Test
//-------------------------------------
// NO DUT required

//-------------------------------------
// Testbench
//-------------------------------------
module mailbox;

  // Define mailbox parameters
  parameter int MAX_MESSAGES = 10;

  // Define mailbox message type
  typedef struct {
      logic [7:0] data;
      // Add any other message fields here
  } message_t;

  // Define mailbox class
  class mailbox_class;
    // Declare mailbox properties
    message_t messages[$];
    int num_messages;

    // Constructor
    function new();
      num_messages = 0;
    endfunction

    // Method to send a message
    function void send(message_t msg);
      if (num_messages < MAX_MESSAGES) begin
        messages.push_back(msg);
        num_messages++;
        $display("Message sent: %h", msg.data);
      end else begin
        $display("Mailbox is full. Message not sent.");
      end
    endfunction

    // Method to receive a message
    function message_t receive();
      message_t msg;
      if (num_messages > 0) begin
        msg = messages.pop_front();
        num_messages--;
        $display("Message received: %h", msg.data);
      end else begin
        $display("Mailbox is empty. No message to receive.");
      end
      return msg;
    endfunction
  endclass

  // Testbench
  initial begin
    // Instantiate mailbox
    mailbox_class mbox = new();

    // Send messages
    for (int i = 0; i < 12; i++) begin
      message_t msg;
      msg.data = $random;
      mbox.send(msg);
    end

    // Receive messages
    for (int i = 0; i < 12; i++) begin
      mbox.receive();
    end
  end
endmodule
