`timescale 1ns/1ps
// Deliberately incorrect teaching mutant: requester 0 always has priority.
module fixed_priority_mutant #(
  parameter integer WIDTH = 4
) (
  input  wire             clk,
  input  wire             rst_n,
  input  wire [WIDTH-1:0] request,
  input  wire             accept,
  output reg  [WIDTH-1:0] grant
);
  integer i;
  reg found;
  always @* begin
    grant = {WIDTH{1'b0}};
    found = 1'b0;
    for (i = 0; i < WIDTH; i = i + 1) begin
      if (!found && request[i]) begin
        grant[i] = 1'b1;
        found = 1'b1;
      end
    end
  end
  wire unused = clk ^ rst_n ^ accept;
endmodule
