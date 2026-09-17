# Round-robin arbiter verification example

This repository is a small, executable example of verifying a parameterized
round-robin arbiter. It focuses on a detail that often gets blurred in simple
testbenches: a grant is an offer, while `grant & accept` is an accepted grant.
The arbitration pointer advances only on that handshake.

## Interface and behavior

`request[i]` means requester `i` is currently eligible. `grant[i]` is a
combinational, one-hot offer to one eligible requester. `accept` is a single
downstream-ready signal applying to the offered grant. An accepted grant occurs
on a rising clock edge when `accept && |grant` is true.

Reset is active-low and asynchronous. It restores requester 0 as the first
priority. When no request is active, no grant is produced. When downstream is
stalled (`accept == 0`), the priority does not rotate; if requests stay stable,
the offered grant stays stable.

The fairness claim has an explicit progress assumption:

> If requester `i` remains asserted, and accepted grants continue to occur,
> requester `i` is offered an accepted grant within at most `WIDTH` accepted
> grants from any arbitration position.

This is deliberately a transaction bound, not a clock-cycle bound. If
downstream never accepts, no finite cycle bound is possible. If a requester
drops its request before service, the persistent-request premise no longer
holds.

## Run the evidence

Install Python 3, Icarus Verilog (`iverilog` and `vvp`), then run:

```sh
make test
```

The default regression runs the correct implementation at widths 1, 2, 3, 4,
and 7 with seeds 1, 17, and 2026. It checks:

- mutual exclusion and request eligibility under randomized stimulus;
- accepted-grant rotation with all requesters active;
- pointer stability during downstream stalls;
- the persistent-request bound measured in accepted grants;
- reset priority.

It also compiles `rtl/fixed_priority_mutant.sv`, a deliberate bug, and runs the
named `persistent_requester_bound` test. The regression passes only when that
mutant produces the expected starvation assertion. An arbitrary nonzero exit,
timeout, compilation failure, or unrelated assertion does not count as useful
failure evidence.

Each run creates `artifacts/<UTC run id>/summary.json` plus separate compile and
simulation logs. The summary records tool versions, platform, elapsed timings,
configuration, seeds, exact outcomes, and SHA-256 hashes of the RTL and
testbench sources. Change the matrix or timeout explicitly when experimenting:

```sh
python3 tools/run.py --widths 2,5,8 --seeds 4,99 --timeout 15
```

## Evidence and limits

The tests demonstrate the listed behaviors for the recorded finite
configurations and stimuli. The fairness scenario uses all requesters as
persistent contenders, which exercises the maximum accepted-grant wait for the
last requester after reset. The source hashes tie each report to the files that
were executed. The deliberate mutant shows that the starvation test can detect
one important class of unfair implementation.

This is simulation evidence, not a formal proof or exhaustive verification.
It does not prove behavior for every width, request trace, simulator, synthesis
tool, or physical implementation. The testbench assumes requests are sampled
as ordinary synchronous interface inputs around rising clock edges. A formal
model could extend this example by expressing one-hot safety and conditional
liveness properties over all traces.

## Repository map

- `rtl/round_robin_arbiter.sv`: synthesizable parameterized implementation
- `rtl/fixed_priority_mutant.sv`: intentionally unfair comparison design
- `tb/arbiter_tb.sv`: self-checking SystemVerilog testbench
- `tools/run.py`: timeout-aware evidence runner
- `tools/test_runner.py`: checks runner outcome classification

Licensed under the MIT License. Contributions are welcome; see
`CONTRIBUTING.md`.

## Recorded result

[Review log and measured results](recorded/2026-09-15/README.md): 15 correct configurations pass and 1 seeded failures are detected. Raw logs, source hashes, timings, and the default RTL synthesis check are included. These are finite educational examples, not client results.

---

## More from Rivoryxa

This repository is one public example. The method it demonstrates is applied to
real OpenHW CORE-V issues in
[core-v-investigation-reports](https://github.com/Rivoryxa-Technologies/core-v-investigation-reports):
sixteen public GitHub issues taken to a disposition, each with its evidence,
proof scope and limits written down.

All examples are listed on the
[Rivoryxa Technologies profile](https://github.com/Rivoryxa-Technologies).
