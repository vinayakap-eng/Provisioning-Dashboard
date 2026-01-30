import io
import unittest
import logging
from pathlib import Path
from django.conf import settings
import importlib.util

logger = logging.getLogger(__name__)

def get_available_tests():
    """
    Returns list of available test modules (TC-1 through TC-8).
    Returns: list of dicts with {module_name, display_name, file_path}
    """
    try:
        tests_dir = Path(settings.BASE_DIR) / 'multi_devices' / 'tests'
        if not tests_dir.exists():
            return []
        
        test_files = sorted([f for f in tests_dir.glob('test_tc*.py')])
        tests_list = []
        
        for test_file in test_files:
            module_name = test_file.stem  # e.g., 'test_tc1'
            tc_num = module_name.replace('test_tc', 'TC-')
            tests_list.append({
                'module_name': module_name,
                'display_name': f'{tc_num}: {module_name}',
                'file_path': str(test_file)
            })
        
        logger.info(f"Found {len(tests_list)} test modules")
        return tests_list
    except Exception as e:
        logger.exception(f"Error getting available tests: {e}")
        return []

def run_single_test(module_name):
    """
    Runs a single test module by name (e.g., 'test_tc1').
    Returns: dict with total, passed, failures, errors, and output.
    """
    try:
        tests_dir = Path(settings.BASE_DIR) / 'multi_devices' / 'tests'
        test_file = tests_dir / f'{module_name}.py'
        
        if not test_file.exists():
            return {
                'total': 0,
                'passed': 0,
                'failures': 0,
                'errors': 1,
                'output': f"Test module not found: {module_name}"
            }
        
        # Load and run the specific test module
        loader = unittest.TestLoader()
        # Use the full module path from the tests directory
        suite = loader.loadTestsFromName(f'multi_devices.tests.{module_name}')
        
        # Capture output
        stream = io.StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=2)
        result = runner.run(suite)

        total = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        passed = total - failures - errors
        
        logger.info(f"Test {module_name}: {total} total, {passed} passed, {failures} failed, {errors} errors")

        return {
            'total': total,
            'passed': passed,
            'failures': failures,
            'errors': errors,
            'output': stream.getvalue()
        }
    except Exception as e:
        logger.exception(f"Error running test {module_name}: {e}")
        return {
            'total': 0,
            'passed': 0,
            'failures': 0,
            'errors': 1,
            'output': f"Exception running test {module_name}: {str(e)}"
        }

def run_all_tests():
    """
    Runs all unittest tests in the multi_devices/tests directory.
    Returns: dict with total, passed, failures, errors, and output.
    """
    try:
        tests_dir = Path(settings.BASE_DIR) / 'multi_devices' / 'tests'
        logger.info(f"Discovering tests in: {tests_dir}")
        
        if not tests_dir.exists():
            logger.error(f"Tests directory not found: {tests_dir}")
            return {
                'total': 0,
                'passed': 0,
                'failures': 0,
                'errors': 1,
                'output': f"Tests directory not found: {tests_dir}"
            }
        
        loader = unittest.TestLoader()
        suite = loader.discover(str(tests_dir))
        
        test_count = suite.countTestCases()
        logger.info(f"Discovered {test_count} tests")

        # Capture output
        stream = io.StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=2)
        result = runner.run(suite)

        total = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        passed = total - failures - errors
        
        logger.info(f"Test results: {total} total, {passed} passed, {failures} failed, {errors} errors")

        return {
            'total': total,
            'passed': passed,
            'failures': failures,
            'errors': errors,
            'output': stream.getvalue()
        }
    except Exception as e:
        logger.exception(f"Error running tests: {e}")
        return {
            'total': 0,
            'passed': 0,
            'failures': 0,
            'errors': 1,
            'output': f"Exception during test discovery: {str(e)}\n\n{repr(e)}"
        }
