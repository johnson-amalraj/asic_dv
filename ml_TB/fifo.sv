module simple_fifo #(
  parameter DEPTH = 8,
  parameter WIDTH = 8
)(
  input logic clk,
  input logic rst_n,
  input logic wr_en,
  input logic rd_en,
  input logic [WIDTH-1:0] din,
  output logic [WIDTH-1:0] dout,
  output logic full,
  output logic empty
);
  logic [$clog2(DEPTH)-1:0] rd_ptr, wr_ptr;
  logic [WIDTH-1:0] mem [0:DEPTH-1];
  logic [$clog2(DEPTH):0] count;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rd_ptr <= '0; wr_ptr <= '0; count <= '0; empty <= 1'b1; full <= 1'b0; dout <= '0;
    end else begin
      if (wr_en && !full) begin
        mem[wr_ptr] <= din;
        wr_ptr <= wr_ptr + 1;
        count <= count + 1;
      end
      if (rd_en && !empty) begin
        dout <= mem[rd_ptr];
        rd_ptr <= rd_ptr + 1;
        count <= count - 1;
      end
      empty <= (count == 0);
      full <= (count == DEPTH);
    end
  end
endmodule