class my_test_sequence extends uvm_sequence;

  // Declare the sequence items
  my_sequence_item item1;
  my_sequence_item item2;

  // Constructor
  function new(string name = "my_test_sequence");
    super.new(name);
  endfunction

  // Main sequence body
  task body();
    // Create and send the first transaction
    item1 = new();
    item1.address = 0x100;
    item1.data = 0x55;
    start_item(item1);
    finish_item(item1);

    // Create and send the second transaction
    item2 = new();
    item2.address = 0x200;
    item2.data = 0xAA;
    start_item(item2);
    finish_item(item2);
  endtask

endclass

