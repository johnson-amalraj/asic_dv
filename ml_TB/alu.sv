module alu(
  input logic clk,
  input logic rst_n,
  input logic [1:0] op, // 00 add, 01 sub, 10 and, 11 or
  input logic [7:0] a,
  input logic [7:0] b,
  output logic [7:0] y
);
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) y <= 8'h00;
    else begin
      unique case (op)
        2'b00: y <= a + b;
        2'b01: y <= a - b;
        2'b10: y <= a & b;
        2'b11: y <= a | b;
        default: y <= 8'hxx;
      endcase
    end
  end
endmodule