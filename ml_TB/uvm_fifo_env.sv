// Similar structure as ALU: a simple sequence writes coverage, calls ml_agent, and applies wr/rd
// For brevity the full classes are omitted here; adapt `alu_ml_sequence` to produce wr_en/rd_en/din sequences

// Suggested sequence logic:
// - produce a mix of writes and reads based on ml_agent output
// - ensure to check full/empty from DUT and avoid illegal transactions

// (If you want the full FIFO UVM code, I can expand it —

// uvm_fifo_env.sv
`include "uvm_macros.svh"
import uvm_pkg::*;

// Interface to DUT
interface fifo_if(input bit clk);
  logic rst_n;
  logic wr_en, rd_en;
  logic [7:0] din;
  logic [7:0] dout;
  logic full, empty;
endinterface

// Transaction
class fifo_txn extends uvm_sequence_item;
  rand bit wr; // 1 => write, 0 => read
  rand logic [7:0] data;
  `uvm_object_utils(fifo_txn)
  function new(string name = "fifo_txn"); super.new(name); endfunction
endclass

// Driver
class fifo_driver extends uvm_driver #(fifo_txn);
  virtual fifo_if vif;
  `uvm_component_utils(fifo_driver)
  function new(string name = "fifo_driver", uvm_component parent = null);
    super.new(name,parent);
  endfunction
  function void build_phase(uvm_phase phase);
    if (!uvm_config_db#(virtual fifo_if)::get(this, "", "vif", vif)) begin
      `uvm_fatal("NOVIF","Virtual interface not set")
    end
  endfunction
  task run_phase(uvm_phase phase);
    fifo_txn tr;
    forever begin
      seq_item_port.get_next_item(tr);
      // apply
      @(posedge vif.clk);
      vif.wr_en <= 0; vif.rd_en <= 0;
      if (tr.wr) begin
        if (!vif.full) begin
          vif.din <= tr.data;
          vif.wr_en <= 1;
        end
      end else begin
        if (!vif.empty) begin
          vif.rd_en <= 1;
        end
      end
      @(posedge vif.clk);
      // deassert
      vif.wr_en <= 0; vif.rd_en <= 0;
      seq_item_port.item_done();
    end
  endtask
endclass

// Monitor
class fifo_monitor extends uvm_monitor;
  virtual fifo_if vif;
  uvm_analysis_port#(fifo_txn) ap;
  `uvm_component_utils(fifo_monitor)
  function new(string name = "fifo_monitor", uvm_component parent = null);
    super.new(name,parent);
    ap = new("ap", this);
  endfunction
  function void build_phase(uvm_phase phase);
    if (!uvm_config_db#(virtual fifo_if)::get(this, "", "vif", vif)) begin
      `uvm_fatal("NOVIF","Virtual interface not set")
    end
  endfunction
  task run_phase(uvm_phase phase);
    fifo_txn tr;
    forever begin
      @(posedge vif.clk);
      // Observe write
      if (vif.wr_en) begin
        tr = fifo_txn::type_id::create("tr");
        tr.wr = 1;
        tr.data = vif.din;
        ap.write(tr);
      end
      // Observe read
      if (vif.rd_en) begin
        tr = fifo_txn::type_id::create("tr");
        tr.wr = 0;
        tr.data = vif.dout; // sampled
        ap.write(tr);
      end
    end
  endtask
endclass

// Scoreboard
class fifo_scoreboard extends uvm_component;
  uvm_analysis_imp#(fifo_txn, fifo_scoreboard) imp;
  queue fifo_q;
  `uvm_component_utils(fifo_scoreboard)
  function new(string name = "fifo_scoreboard", uvm_component parent = null);
    super.new(name,parent);
    imp = new("imp", this);
    fifo_q = new();
  endfunction
  virtual task write(fifo_txn t);
    // analysis imp callback
    if (t.wr) begin
      fifo_q.push_back(t.data);
    end else begin
      logic [7:0] expected;
      if (fifo_q.size() == 0) begin
        `uvm_error("SB","Read observed but expected queue empty")
      end else begin
        expected = fifo_q.pop_front();
        if (expected !== t.data) begin
          `uvm_error("SB","Data mismatch: expected %0h got %0h", expected, t.data)
        end
      end
    end
  endtask
endclass

// Agent
class fifo_agent extends uvm_agent;
  fifo_driver drv;
  fifo_monitor mon;
  uvm_sequencer#(fifo_txn) seqr;
  `uvm_component_utils(fifo_agent)
  function new(string name = "fifo_agent", uvm_component parent = null);
    super.new(name,parent);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    seqr = uvm_sequencer#(fifo_txn)::type_id::create("seqr", this);
    drv = fifo_driver::type_id::create("drv", this);
    mon = fifo_monitor::type_id::create("mon", this);
  endfunction
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    drv.seq_item_port.connect(seqr.seq_item_export);
  endfunction
endclass

// Environment
class fifo_env extends uvm_env;
  fifo_agent agent;
  fifo_scoreboard sb;
  `uvm_component_utils(fifo_env)
  function new(string name = "fifo_env", uvm_component parent = null);
    super.new(name,parent);
  endfunction
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    agent = fifo_agent::type_id::create("agent", this);
    sb = fifo_scoreboard::type_id::create("sb", this);
  endfunction
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    // connect monitor analysis port to scoreboard
    agent.mon.ap.connect(sb.imp.analysis_export);
  endfunction
endclass

// Sequence that uses ML agent via file-based IPC (similar to alu)
class fifo_ml_sequence extends uvm_sequence#(fifo_txn);
  `uvm_object_utils(fifo_ml_sequence)
  function new(string name = "fifo_ml_sequence"); super.new(name); endfunction
  task body();
    fifo_txn tr;
    integer i;
    for (i=0;i<200;i++) begin
      tr = fifo_txn::type_id::create("tr");
      // write coverage snapshot (mock) and call python ml_agent
      $fwrite($fopen("/tmp/coverage_fifo.json","w"), "{\"uncovered_bins\": [\"fifo_full\"]}");
      $system("python3 ml_agent.py /tmp/coverage_fifo.json /tmp/next_fifo_stim.json");
      string line; int fd;
      fd = $fopen("/tmp/next_fifo_stim.json","r");
      if (fd) begin
        line = "";
        line = $fgets(line, fd);
        $fclose(fd);
        int op_i; int data_i;
        if ($sscanf(line, "%d,%d", op_i, data_i) >= 1) begin
          tr.wr = op_i % 2; tr.data = data_i & 8'hFF;
        end else begin
          tr.wr = $urandom_range(1);
          tr.data = $urandom_range(255);
        end
      end
      start_item(tr);
      finish_item(tr);
    end
  endtask
endclass

// Top-level test
class fifo_test extends uvm_test;
  `uvm_component_utils(fifo_test)
  function new(string name = "fifo_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    fifo_ml_sequence seq;
    seq = fifo_ml_sequence::type_id::create("seq");
    seq.start(null);
  endtask
endclass