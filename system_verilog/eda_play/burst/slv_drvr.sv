class slv_drvr extends uvm_driver;

  // Declare the interface
  burst_if vif;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // Build the BFM components
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);

    // Get the interface handle from the testbench
    if (!uvm_config_db#(burst_if)::get(this, "", "vif", vif))
      `uvm_fatal("NOVIF", "Virtual interface not found")
  endfunction

  // Drive the DUT signals
  task run_phase(uvm_phase phase);
    super.run_phase(phase);
    forever begin
      my_transaction tx;
      if (seq_item_port.get_next_item(tx)) begin
        vif.ap.data_out <= 0;
        #5;
        vif.ap.data_in <= 1;
        seq_item_port.item_done();
      end
      else
        seq_item_port.wait_for_seq_item();
    end
  endtask

endclass

// In this example, we define a simple BFM that contains an interface and drives the DUT signals. We get the interface handle from the testbench in the build_phase method, and we drive the signals in an infinite loop in the run_phase method. We wait for the next sequence item from the sequencer using the seq_item_port.wait_for_seq_item() method, and we use the seq_item_port.item_done() method to notify the sequencer when the transaction is complete.
