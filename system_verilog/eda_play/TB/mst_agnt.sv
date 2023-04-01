class my_agent extends uvm_agent;

  // Declare the interface
  my_interface vif;

  // Declare the sequence and sequencer
  my_sequence my_seq;
  my_sequencer my_sequencer;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // Build the agent components
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);

    // Create the interface and connect it to the DUT
    vif = my_interface::type_id::create("vif", this);
    vif.connect();

    // Create the sequencer and set the default sequence
    my_sequencer = my_sequencer::type_id::create("my_sequencer", this);
    my_seq = my_sequence::type_id::create("my_seq");
    my_seq.randomize(); // Randomize the sequence data
    my_sequencer.set_default_sequence(my_seq);
  endfunction

  // Run the sequence
  task run_phase(uvm_phase phase);
    super.run_phase(phase);
    my_sequencer.start(my_seq, vif.ap);
    my_sequencer.wait_for_sequences();
  endtask

endclass

// In this example, we define a simple agent that contains an interface, a sequence, and a sequencer. We create the interface and connect it to the DUT in the build_phase method, and we set the default sequence in the same method. We then run the sequence in the run_phase method by starting the sequencer and waiting for the sequence to complete.


