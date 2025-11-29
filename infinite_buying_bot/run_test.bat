@echo off
python test_accelerated_e2e.py > test_output.log 2>&1
type test_output.log
