`timescale 1ns/1ps
module arbiter_tb;
  parameter integer WIDTH = 4;
  parameter integer SEED = 1;
  reg clk = 0;
  reg rst_n = 0;
  reg [WIDTH-1:0] request = 0;
  reg accept = 0;
  wire [WIDTH-1:0] grant;
  integer failures = 0;
  integer accepted_count;
  integer start_accepted;
  integer i;
  integer random_state;
  reg [WIDTH-1:0] held_grant;
  string test_name;
  string selected_test;

`ifdef MUTANT
  fixed_priority_mutant #(.WIDTH(WIDTH)) dut (.*);
`else
  round_robin_arbiter #(.WIDTH(WIDTH)) dut (.*);
`endif

  always #5 clk = ~clk;

  task check;
    input condition;
    input string message;
    begin
      if (condition !== 1'b1) begin
        failures = failures + 1;
        $display("ASSERT_FAIL test=%s width=%0d seed=%0d message=%s", test_name, WIDTH, SEED, message);
      end
    end
  endtask

  task tick;
    reg accepted_pre_edge;
    begin
      accepted_pre_edge = accept && (|grant);
      @(posedge clk); #1;
      if (accepted_pre_edge) accepted_count = accepted_count + 1;
    end
  endtask

  task apply_reset;
    begin
      rst_n = 0; request = 0; accept = 0;
      tick; tick;
      rst_n = 1; #1;
      accepted_count = 0;
    end
  endtask

  task test_reset;
    begin
      test_name = "reset";
      apply_reset();
      request = {WIDTH{1'b1}}; accept = 0; #1;
      check(grant[0] && $onehot(grant), "reset must restore requester 0 as next priority");
    end
  endtask

  task test_mutual_exclusion_and_eligibility;
    integer n;
    begin
      test_name = "mutual_exclusion_eligible";
      apply_reset();
      random_state = SEED;
      for (n = 0; n < 80; n = n + 1) begin
        request = $random(random_state);
        accept = $random(random_state) & 1;
        #1;
        check($onehot0(grant), "grant must be one-hot or zero");
        check((grant & ~request) == 0, "grant must target an active request");
        check((request == 0) == (grant == 0), "grant exists exactly when an eligible request exists");
        tick;
      end
    end
  endtask

  task test_rotation;
    integer expected;
    begin
      test_name = "rotation";
      apply_reset();
      request = {WIDTH{1'b1}}; accept = 1;
      for (expected = 0; expected < WIDTH * 2; expected = expected + 1) begin
        #1;
        check(grant[expected % WIDTH], "accepted grants must rotate through all requesters");
        tick;
      end
    end
  endtask

  task test_stalled_downstream;
    begin
      test_name = "stalled_downstream";
      apply_reset();
      request = {WIDTH{1'b1}}; accept = 0; #1;
      held_grant = grant;
      repeat (WIDTH + 3) begin
        tick;
        check(grant == held_grant, "priority must not advance without acceptance");
      end
      accept = 1; tick; accept = 0; #1;
      if (WIDTH > 1) check(grant != held_grant, "priority must advance after an accepted grant");
    end
  endtask

  task test_persistent_requester_bound;
    integer target;
    integer accepted_before;
    integer seen;
    integer steps;
    begin
      test_name = "persistent_requester_bound";
      apply_reset();
      target = WIDTH - 1;
      request = {WIDTH{1'b1}}; accept = 1;
      accepted_before = accepted_count;
      seen = 0;
      steps = 0;
      while (!seen && steps < WIDTH) begin
        #1;
        if (grant[target]) seen = 1;
        tick;
        steps = steps + 1;
      end
      check(seen, "STARVATION: persistent requester missed bound of WIDTH accepted grants");
      check((accepted_count - accepted_before) <= WIDTH, "fairness bound is measured in accepted grants");
    end
  endtask

  initial begin
    if (!$value$plusargs("TEST=%s", selected_test)) selected_test = "all";
    if (selected_test != "all" && selected_test != "reset" &&
        selected_test != "mutual_exclusion_eligible" && selected_test != "rotation" &&
        selected_test != "stalled_downstream" && selected_test != "persistent_requester_bound") begin
      $display("TEST_RESULT FAIL test=%s width=%0d seed=%0d failures=1", selected_test, WIDTH, SEED);
      $fatal(1, "unknown test name");
    end
    if (selected_test == "all" || selected_test == "reset") test_reset();
    if (selected_test == "all" || selected_test == "mutual_exclusion_eligible") test_mutual_exclusion_and_eligibility();
    if (selected_test == "all" || selected_test == "rotation") test_rotation();
    if (selected_test == "all" || selected_test == "stalled_downstream") test_stalled_downstream();
    if (selected_test == "all" || selected_test == "persistent_requester_bound") test_persistent_requester_bound();
    if (failures == 0) begin
      $display("TEST_RESULT PASS test=%s width=%0d seed=%0d accepted=%0d", selected_test, WIDTH, SEED, accepted_count);
      $finish;
    end
    $display("TEST_RESULT FAIL test=%s width=%0d seed=%0d failures=%0d", selected_test, WIDTH, SEED, failures);
    $fatal(1, "verification failed");
  end
endmodule
