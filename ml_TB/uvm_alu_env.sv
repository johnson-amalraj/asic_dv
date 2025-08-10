`include "uvm_macros.svh"
import uvm_pkg::*;

// Transaction
class alu_txn extends uvm_sequence_item;
  rand logic [1:0] op;
  rand logic [7:0] a, b;
  `uvm_object_utils(alu_txn)
  function new(string name = "alu_txn"); super.new(name); endfunction
endclass

// Driver (applies stimulus to DUT via virtual interface)
class alu_driver extends uvm_driver #(alu_txn);
  virtual interface alu_if;
  function new(string name = "alu_driver"); super.new(name); endfunction
  task run_phase(uvm_phase phase);
    alu_txn tr;
    forever begin
      seq_item_port.get_next_item(tr);
      // apply
      @(posedge alu_if.clk);
      alu_if.op <= tr.op;
      alu_if.a <= tr.a;
      alu_if.b <= tr.b;
      @(posedge alu_if.clk);
      seq_item_port.item_done();
    end
  endtask
endclass

// Sequence that uses ML agent via file-based IPC
class alu_ml_sequence extends uvm_sequence #(alu_txn);
  `uvm_object_utils(alu_ml_sequence)
  function new(string name = "alu_ml_sequence"); super.new(name); endfunction
  task body();
    alu_txn tr;
    integer i;
    for (i=0;i<100;i++) begin
      tr = alu_txn::type_id::create("tr");
      // write coverage snapshot (mock) and call python ml_agent
      // In a real env, you'd export real coverage data
      $fwrite($fopen("/tmp/coverage.json","w"), "{\"uncovered_bins\": [\"add_zero\",\"sub_neg\"]}");
      $system("python3 ml_agent.py /tmp/coverage.json /tmp/next_stim.json");
      // read produced stimulus
      string line; int fd;
      fd = $fopen("/tmp/next_stim.json","r");
      if (fd) begin
        line = "";
        line = $fgets(line, fd);
        $fclose(fd);
        // parse naive: expect format op,a,b
        int op_i; int a_i; int b_i;
        if ($sscanf(line, "%d,%d,%d", op_i, a_i, b_i) == 3) begin
          tr.op = op_i; tr.a = a_i; tr.b = b_i;
        end else begin
          // fallback random
          void'($urandom_range(3));
          tr.op = $urandom_range(3);
          tr.a = $urandom_range(255);
          tr.b = $urandom_range(255);
        end
      end
      start_item(tr);
      finish_item(tr);
    end
  endtask
endclass

// Top-level test (instantiation and config omitted for brevity)
class alu_test extends uvm_test;
  `uvm_component_utils(alu_test)
  function new(string name = "alu_test", uvm_component parent = null);
    super.new(name, parent);
  endfunction
  task run_phase(uvm_phase phase);
    alu_ml_sequence seq;
    seq = alu_ml_sequence::type_id::create("seq");
    seq.start(null);
  endtask
endclass