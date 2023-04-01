class my_env extends uvm_env;

  // Declare the agent handle
  mst_agnt mst;
  slv_agnt slv;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // Build the environment components
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);

    // Create the agent and set its name
    mst_agnt = mst_agnt::type_id::create("master_agnt", this);
    mst_agnt.set_agent_name("master_agent");

    // Create the agent and set its name
    slv_agnt = slv_agnt::type_id::create("slave_agnt", this);
    slv_agnt.set_agent_name("slave_agent");
  endfunction

  // Run the environment
  task run_phase(uvm_phase phase);
    super.run_phase(phase);

    // Start the agent and run its sequence
    mst_agnt.set_sequence_config("mst_seq", 1, 1);
    mst_agnt.set_sequencer_config(my_sequencer::type_id::get(), "master_sequencer", "mst_seq");
    mst_agnt.set_active();

    // Wait for the sequence to complete
    fork
      @mst_agnt.ap.ack;
      $display("Sequence complete");
    join_none
  endtask

endclass

// In this example, we define a simple environment that contains an agent. We create the agent in the build_phase method and set its name. In the run_phase method, we start the agent and run its sequence. We use the set_sequence_config() and set_sequencer_config() methods to configure the sequence and sequencer for the agent. We then wait for the sequence to complete using a fork-join block and display a message when it's done.
