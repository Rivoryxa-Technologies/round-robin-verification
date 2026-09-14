.PHONY: test runner-tests clean

test: runner-tests
	python3 tools/run.py

runner-tests:
	cd tools && python3 -m unittest -v test_runner.py

clean:
	rm -rf artifacts
