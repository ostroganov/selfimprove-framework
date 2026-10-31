@echo off
REM Wrapper script for run_iterative.py
REM Usage: run_iterative.bat [arguments...]
REM
REM Examples:
REM   run_iterative.bat                              - Run with defaults (20 iterations, improvement mode)
REM   run_iterative.bat -n 50                        - Run up to 50 iterations
REM   run_iterative.bat --mode happiness             - Run in happiness mode
REM   run_iterative.bat --start-level L5             - Start from L5
REM   run_iterative.bat --force-bootstrap            - Force re-bootstrap L0

python run_iterative.py %*
