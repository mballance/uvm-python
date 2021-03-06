
ifeq ($(TEST), )
    UNIT_ARGS = unit/*.py
else
    UNIT_ARGS = unit.$(TEST)
endif

test: test-simple test-integrated test-unit
	find test/examples -name results.xml -exec cat {} \; > results.log
	bash ci/check_errors.sh

test-simple:
	make -C test/examples/simple

test-integrated:
	make -C test/examples/integrated

test-unit:
	python -m unittest $(UNIT_ARGS)

# Unused at the moment, TODO cleanup and add to 'make test'
test-sim-integration:
	make -C test/sim_integration MODULE=test_uvm_events

lint:   
	flake8 ./uvm --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 ./uvm --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
