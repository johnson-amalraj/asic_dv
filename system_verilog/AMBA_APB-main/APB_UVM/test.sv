import uvm_pkg::*;

class base_test extends uvm_test;
    `uvm_component_utils(base_test)
    
    // Components
    environment env;

    // Variables
    rnd_sequence seq;
    agent_config agnt_cfg;

    // Constructor: new
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction //new()

    function void build_phase(uvm_phase phase);
        agnt_cfg = new("agnt_cfg");
        if(!uvm_config_db#(virtual APB_intf)::get(this, "*", "vif", agnt_cfg.intf))
            `uvm_fatal(get_name(), "vif cannot be found in ConfigDB!")
        
        uvm_config_db#(agent_config)::set(this, "env.agnt.*", "agnt_cfg", agnt_cfg);
        uvm_config_db#(int)::set(null, "seq.*", "no_cases", 100);
        
        seq = new();
        env = environment::type_id::create("env", this);
    endfunction: build_phase

    function void end_of_elaboration_phase(uvm_phase phase);
        super.end_of_elaboration_phase(phase);
        uvm_top.print_topology();
    endfunction: end_of_elaboration_phase
    
    task run_phase(uvm_phase phase);
        phase.raise_objection(this);
        seq.start(env.agnt.seqr);
        #100;
        phase.drop_objection(this);
    endtask: run_phase
    
endclass //base_test extends uvm_test
