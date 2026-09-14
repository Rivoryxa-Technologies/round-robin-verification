# Contributing

Thank you for improving this educational example.

Keep changes small and make each verification claim observable. If behavior or
assumptions change, update the README and add a test that distinguishes the new
behavior from a plausible bug. Deliberate mutants should be clearly named and
must fail for the intended assertion rather than merely return a nonzero code.

Before submitting a change, run:

```sh
make test
```

Include the generated `summary.json` result in your report, but do not commit
the `artifacts/` directory. Use clear commit messages and certify that your
contribution may be distributed under the MIT License.
