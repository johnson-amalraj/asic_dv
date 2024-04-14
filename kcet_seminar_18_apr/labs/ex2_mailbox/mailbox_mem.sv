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
module DUT (
  output logic clk,
  inout  logic rst,
  inout  logic write_en,
  inout  logic read_en,
  inout  logic [7:0] data_in,
  input  logic [7:0] data_out
);

    always #5 clk = ~clk;

    // Instantiate the Mailbox module
    Mailbox mailbox_inst (
                          .clk      (clk),
                          .rst      (rst),
                          .write_en (write_en),
                          .data_in  (data_in),
                          .read_en  (read_en),
                          .data_out (data_out),
                          .full     (),
                          .empty    ()
    );

    // Instantiate the Producer module
    Producer producer_inst (
                            .write_en (write_en),
                            .clk      (clk),
                            .rst      (rst),
                            .data_out (data_out)
    );

    // Instantiate the Consumer module
    Consumer consumer_inst (
                            .read_en (read_en),
                            .clk     (clk),
                            .rst     (rst),
                            .data_in (data_in)
    );

endmodule

//-------------------------------------
// Testbench
//-------------------------------------
module Producer (
  output logic       write_en,
  input  logic       clk,
  output logic       rst,
  input  logic [7:0] data_out
);

  logic [7:0] data = 8'hAA; // Sample data

    initial begin
      rst = 1;
      #10;
      rst = 0;
    end

    always_ff @(posedge clk, posedge rst) begin
      if (rst)
        write_en <= 0;
      else
        write_en <= 1; // Enable writing data to mailbox
    end

endmodule

module Consumer (
  output logic       read_en,
  input  logic       clk,
  input  logic       rst,
  output logic [7:0] data_in
);

  logic [7:0] received_data;

    initial begin
      read_en <= 0;
      #40;
      read_en <= 1;
    end

    // always_ff @(posedge clk, posedge rst) begin
    //   if (rst)
    //     clk <= 0;
    //   else
    //     clk <= ~clk; // Generate a clock signal
    // end

    always_ff @(posedge clk) begin
      if (read_en)
        data_in <= received_data; // Read data from mailbox
    end

endmodule

module Mailbox (
  input  logic       clk,
  input  logic       rst,
  input  logic       write_en,
  input  logic [7:0] data_in,
  input  logic       read_en,
  output logic [7:0] data_out,
  output logic       full,
  output logic       empty
);

  localparam MEM_DEPTH = 8;

  logic [7:0] memory [0:MEM_DEPTH-1];
  int         write_ptr = 0;
  int         read_ptr = 0;
  
    always_ff @(posedge clk, posedge rst) begin
      if (rst) begin
        write_ptr <= 0;
        read_ptr  <= 0;
      end
      else begin
        if (write_en && !full) begin
          memory[write_ptr] <= data_in;
          write_ptr         <= (write_ptr + 1) % MEM_DEPTH;
        end
        if (read_en && !empty) begin
          data_out <= memory[read_ptr];
          read_ptr <= (read_ptr + 1) % MEM_DEPTH;
        end
      end
    end
    
    assign full  = ((write_ptr + 1) % MEM_DEPTH == read_ptr);
    assign empty = (write_ptr == read_ptr);

    // Waveform generation
    initial begin
      // Open waveform dump file
      $dumpfile("waveform.vcd");
          
      // Dump variables to waveform dump file
      $dumpvars();
    end
endmodule
