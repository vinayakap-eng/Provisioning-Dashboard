import io
import unittest
from pathlib import Path
from django.conf import settings

def run_all_tests():
    """
    Runs all unittest tests in the multi_devices/tests directory.
    Returns: dict with total, passed, failures, errors, and output.
    """
    tests_dir = Path(settings.BASE_DIR) / 'multi_devices' / 'tests'
    loader = unittest.TestLoader()
    suite = loader.discover(str(tests_dir))

    # Capture output
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)

    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors

    return {
        'total': total,
        'passed': passed,
        'failures': failures,
        'errors': errors,
        'output': stream.getvalue()
    }
