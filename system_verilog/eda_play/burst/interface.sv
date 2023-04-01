interface burst_if (
  input  logic clk,
  input  logic reset,
  output logic data_out,
  input  logic data_in
);

  logic internal_reg;

  modport master (
    output data_out,
    input  data_in
  );

  modport slave (
    input  data_out,
    output data_in
  );

  always_ff @(posedge clk, negedge reset_n) begin
    if (!reset_n) begin
      internal_reg <= 1'b0;
    end else begin
      internal_reg <= data_in;
    end
  end

  assign data_out = internal_reg;

endinterface

// In this example, we declare an interface called burst_if that has four signals: clk and reset_n as inputs, data_out as an output, and data_in as an input. We also declare an internal register called internal_reg.

// We then define two modports: master and slave. The master modport allows an external module to output data_out and input data_in, while the slave modport allows an external module to input data_out and output data_in.

// Finally, we define an always_ff block that is triggered on the positive edge of clk and the negative edge of reset_n. Inside the always_ff block, we check the value of reset_n. If it's low, we set internal_reg to 0. Otherwise, we set it to the value of data_in. We then assign data_out to internal_reg.
