import unittest
from unittest import mock
from pathlib import Path
import sys
import tempfile
import run


class OutcomeEvaluationTests(unittest.TestCase):
    def test_named_expected_failure_is_accepted(self):
        output = "ASSERT_FAIL test=persistent_requester_bound message=STARVATION\nTEST_RESULT FAIL"
        self.assertTrue(run.evaluate(1, False, output, "fail", "message=STARVATION")[0])

    def test_arbitrary_nonzero_is_rejected(self):
        self.assertFalse(run.evaluate(1, False, "segmentation fault", "fail", "STARVATION")[0])

    def test_wrong_failure_marker_is_rejected(self):
        self.assertFalse(run.evaluate(1, False, "ASSERT_FAIL OTHER\nTEST_RESULT FAIL", "fail", "STARVATION")[0])

    def test_pass_with_stray_assertion_is_rejected(self):
        output = "ASSERT_FAIL unexpected\nTEST_RESULT PASS"
        self.assertFalse(run.evaluate(0, False, output, "pass", "TEST_RESULT PASS")[0])

    def test_expected_failure_with_extra_assertion_is_rejected(self):
        output = "ASSERT_FAIL STARVATION\nASSERT_FAIL unrelated\nTEST_RESULT FAIL"
        self.assertFalse(run.evaluate(1, False, output, "fail", "STARVATION")[0])

    def test_timeout_is_rejected_even_with_marker(self):
        self.assertFalse(run.evaluate(1, True, "STARVATION\nTEST_RESULT FAIL", "fail", "STARVATION")[0])

    def test_invoke_enforces_timeout_and_retains_log(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "timeout.log"
            code, timed_out, _, output = run.invoke(
                [sys.executable, "-c", "import time; print('started', flush=True); time.sleep(2)"],
                0.05, log)
            self.assertIsNone(code)
            self.assertTrue(timed_out)
            self.assertIn("started", output)
            self.assertEqual(output, log.read_text())

    def test_missing_tool_returns_configuration_error(self):
        with mock.patch("run.shutil.which", return_value=None):
            self.assertEqual(run.main(["--widths", "2", "--seeds", "1"]), 2)


if __name__ == "__main__":
    unittest.main()
