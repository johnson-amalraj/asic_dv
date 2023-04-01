class my_env extends uvm_env;

  // Declare the agent handle
  my_agent my_agent1;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // Build the environment components
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);

    // Create the agent and set its name
    my_agent1 = my_agent::type_id::create("my_agent1", this);
    my_agent1.set_agent_name("my_agent1");
  endfunction

  // Run the environment
  task run_phase(uvm_phase phase);
    super.run_phase(phase);

    // Start the agent and run its sequence
    my_agent1.set_sequence_config("my_seq", 1, 1);
    my_agent1.set_sequencer_config(my_sequencer::type_id::get(), "my_sequencer", "my_seq");
    my_agent1.set_active();

    // Wait for the sequence to complete
    fork
      @my_agent1.ap.ack;
      $display("Sequence complete");
    join_none
  endtask

endclass

// In this example, we define a simple environment that contains an agent. We create the agent in the build_phase method and set its name. In the run_phase method, we start the agent and run its sequence. We use the set_sequence_config() and set_sequencer_config() methods to configure the sequence and sequencer for the agent. We then wait for the sequence to complete using a fork-join block and display a message when it's done.
