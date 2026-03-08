#!/usr/bin/env python3
"""Test runner - runs all tests with timeout protection per file."""
import subprocess, sys, os, re

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_FILES = [
    'tests/test_program_model.py',
    'tests/test_csv_parser.py',
    'tests/test_translations.py',
    'tests/test_logger.py',
    'tests/test_machine_state.py',
    'tests/test_step_generator.py',
    'tests/test_hardware_factory.py',
    'tests/test_mock_hardware.py',
    'tests/test_safety_system.py',
    'tests/test_infrastructure.py',
    'tests/test_execution_engine.py',
    'tests/test_integration.py',
    'tests/test_unexpected_tool_safety.py',
]

total_passed = total_failed = total_errors = 0
failures = []

for f in TEST_FILES:
    name = f.split('/')[-1].replace('.py', '')
    try:
        proc = subprocess.run(
            [sys.executable, '-m', 'pytest', f, '--tb=line', '--color=no', '-o', 'addopts='],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=60
        )
        out = proc.stdout
        m_p = re.search(r'(\d+) passed', out)
        m_f = re.search(r'(\d+) failed', out)
        p = int(m_p.group(1)) if m_p else 0
        fl = int(m_f.group(1)) if m_f else 0
        total_passed += p; total_failed += fl
        status = 'PASS' if fl == 0 and proc.returncode == 0 else 'FAIL'
        print(f"  {status}  {name}: {p} passed, {fl} failed")
        if fl > 0:
            for line in out.split('\n'):
                if 'FAILED' in line and '::' in line:
                    failures.append(f"    {line.strip()}")
    except subprocess.TimeoutExpired:
        total_errors += 1
        print(f"  TIMEOUT  {name}")
        failures.append(f"    {name}: TIMEOUT")

print(f"\n{'='*50}")
print(f"TOTAL: {total_passed} passed, {total_failed} failed, {total_errors} timeouts")
if failures:
    print("\nDetails:")
    for x in failures: print(x)
print(f"{'='*50}")
sys.exit(0 if total_failed == 0 and total_errors == 0 else 1)
