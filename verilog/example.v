module example(
    input wire clk,
    input wire rst,
    input wire in,
    output reg out
);

reg rand_reg;
 always @ * begin
     out = ~in;
 end

initial begin
    dumpfile(example.vsd);
    dumpvars(0,example);
end

endmodule
