#!/usr/bin/env python3
"""Portable regression runner with retained evidence and exact outcome checks."""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ROOT / "rtl" / "round_robin_arbiter.sv",
    ROOT / "rtl" / "fixed_priority_mutant.sv",
    ROOT / "tb" / "arbiter_tb.sv",
]


def sha256(path):
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def evaluate(returncode, timed_out, output, expected, marker):
    """Return (passed, reason); expected failure requires its named assertion marker."""
    if timed_out:
        return False, "timeout"
    marker_present = marker in output
    result_pass = "TEST_RESULT PASS" in output
    result_fail = "TEST_RESULT FAIL" in output
    assertion_lines = [line for line in output.splitlines() if line.startswith("ASSERT_FAIL")]
    if expected == "pass":
        ok = returncode == 0 and result_pass and not result_fail and not assertion_lines and marker_present
        return ok, "matched expected pass" if ok else "pass signature mismatch"
    ok = (returncode != 0 and result_fail and not result_pass and marker_present and
          len(assertion_lines) == 1 and marker in assertion_lines[0])
    return ok, "matched named expected failure" if ok else "failure signature mismatch"


def invoke(command, timeout, log_path):
    started = time.monotonic()
    timed_out = False
    proc = subprocess.Popen(
        command, cwd=str(ROOT), text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, start_new_session=(os.name == "posix"),
    )
    try:
        output, _ = proc.communicate(timeout=timeout)
        code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        if os.name == "posix":
            os.killpg(proc.pid, 9)
        else:
            proc.kill()
        output, _ = proc.communicate()
        code = None
    duration = time.monotonic() - started
    log_path.write_text(output, encoding="utf-8")
    return code, timed_out, duration, output


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--widths", default="1,2,3,4,7")
    parser.add_argument("--seeds", default="1,17,2026")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts")
    args = parser.parse_args(argv)
    try:
        widths = [int(x) for x in args.widths.split(",") if x]
        seeds = [int(x) for x in args.seeds.split(",") if x]
    except ValueError:
        parser.error("widths and seeds must be comma-separated integers")
    if not widths or any(width < 1 for width in widths):
        parser.error("at least one positive width is required")
    if not seeds:
        parser.error("at least one seed is required")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout must be a finite positive number")
    compiler = shutil.which("iverilog")
    runtime = shutil.which("vvp")
    if not compiler or not runtime:
        missing = [name for name, path in (("iverilog", compiler), ("vvp", runtime)) if not path]
        print("ERROR missing required tool(s): " + ", ".join(missing), file=sys.stderr)
        return 2

    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out_dir = args.artifacts.resolve() / run_id
    out_dir.mkdir(parents=True)
    def tool_version(command):
        try:
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, check=False, timeout=args.timeout)
            lines = result.stdout.splitlines()
            return lines[0] if lines else "unknown"
        except subprocess.TimeoutExpired:
            return "version query timed out"

    compiler_version = tool_version([compiler, "-V"])
    runtime_version = tool_version([runtime, "-V"])
    cases = []

    def run_case(name, width, seed, mutant, test, expected, marker):
        case_dir = out_dir / name
        case_dir.mkdir()
        image = case_dir / "sim.vvp"
        compile_command = [compiler, "-g2012", "-Wall", "-s", "arbiter_tb",
                           "-Parbiter_tb.WIDTH=" + str(width),
                           "-Parbiter_tb.SEED=" + str(seed)]
        if mutant:
            compile_command.append("-DMUTANT")
        compile_command += ["-o", str(image)] + [str(path) for path in SOURCES]
        cc, cto, cd, cout = invoke(compile_command, args.timeout, case_dir / "compile.log")
        record = {"name": name, "width": width, "seed": seed, "mutant": mutant,
                  "test": test, "expected": expected, "compile_seconds": cd,
                  "compile_returncode": cc, "compile_timeout": cto}
        if cc != 0 or cto:
            record.update({"passed": False, "reason": "compile timeout" if cto else "compile failed"})
        else:
            command = [runtime, str(image), "+TEST=" + test]
            rc, to, seconds, output = invoke(command, args.timeout, case_dir / "simulation.log")
            passed, reason = evaluate(rc, to, output, expected, marker)
            record.update({"command": command, "returncode": rc, "timeout": to,
                           "simulation_seconds": seconds, "marker": marker,
                           "passed": passed, "reason": reason})
        cases.append(record)
        print(("PASS " if record["passed"] else "FAIL ") + name + ": " + record["reason"])

    for width in widths:
        for seed in seeds:
            run_case("correct_w{}_s{}".format(width, seed), width, seed, False, "all", "pass", "TEST_RESULT PASS")
    run_case("mutant_starvation_w4_s17", 4, 17, True, "persistent_requester_bound",
             "fail", "ASSERT_FAIL test=persistent_requester_bound width=4 seed=17 message=STARVATION")

    summary = {
        "schema_version": 1,
        "run_id": run_id,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "iverilog_version": compiler_version,
        "vvp_version": runtime_version,
        "timeout_seconds": args.timeout,
        "config": {"widths": widths, "seeds": seeds},
        "source_sha256": {str(path.relative_to(ROOT)): sha256(path)
                          for path in SOURCES + [ROOT / "tools" / "run.py"]},
        "cases": cases,
        "passed": all(case["passed"] for case in cases),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("Evidence: " + str(out_dir / "summary.json"))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
