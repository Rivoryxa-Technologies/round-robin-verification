`timescale 1ns/1ps
module round_robin_arbiter #(
  parameter integer WIDTH = 4,
  parameter integer PTR_W = (WIDTH <= 1) ? 1 : $clog2(WIDTH)
) (
  input  wire                 clk,
  input  wire                 rst_n,
  input  wire [WIDTH-1:0]     request,
  input  wire                 accept,
  output reg  [WIDTH-1:0]     grant
);
  reg [PTR_W-1:0] next_priority;
  integer offset;
  integer index;
  reg found;

  initial begin
    if (WIDTH < 1) $error("WIDTH must be at least 1");
  end

  always @* begin
    grant = {WIDTH{1'b0}};
    found = 1'b0;
    for (offset = 0; offset < WIDTH; offset = offset + 1) begin
      index = next_priority + offset;
      if (index >= WIDTH) index = index - WIDTH;
      if (!found && request[index]) begin
        grant[index] = 1'b1;
        found = 1'b1;
      end
    end
  end

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      next_priority <= {PTR_W{1'b0}};
    end else if (accept && (|grant)) begin
      if (index_of_grant(grant) == WIDTH - 1)
        next_priority <= {PTR_W{1'b0}};
      else
        next_priority <= index_of_grant(grant) + 1'b1;
    end
  end

  function integer index_of_grant;
    input [WIDTH-1:0] value;
    integer i;
    begin
      index_of_grant = 0;
      for (i = 0; i < WIDTH; i = i + 1)
        if (value[i]) index_of_grant = i;
    end
  endfunction
endmodule
