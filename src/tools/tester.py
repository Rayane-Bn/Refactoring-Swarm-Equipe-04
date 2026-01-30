"""
Code Tester Tool
Manages test execution, coverage analysis, and test reporting.
"""

import os
import sys
import unittest
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import time
from io import StringIO


class TestRunner:
    """Executes tests and generates reports."""
    
    def __init__(self, test_dir: str = "tests"):
        """
        Initialize the test runner.
        
        Args:
            test_dir: Directory containing test files
        """
        self.test_dir = Path(test_dir)
        self.results = {
            'tests_run': 0,
            'failures': [],
            'errors': [],
            'successes': [],
            'skipped': [],
            'execution_time': 0,
            'coverage': {}
        }
    
    def discover_tests(self, pattern: str = "test_*.py") -> List[str]:
        """
        Discover all test files in the test directory.
        
        Args:
            pattern: File pattern to match test files
            
        Returns:
            List of test file paths
        """
        if not self.test_dir.exists():
            print(f"⚠️  Test directory not found: {self.test_dir}")
            return []
        
        test_files = list(self.test_dir.rglob(pattern))
        return [str(f) for f in test_files]
    
    def run_unittest(self, test_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Run unit tests using unittest framework.
        
        Args:
            test_file: Specific test file to run (optional)
            
        Returns:
            Test results dictionary
        """
        start_time = time.time()
        
        # Create a test suite
        loader = unittest.TestLoader()
        
        if test_file:
            suite = loader.discover(str(self.test_dir), pattern=Path(test_file).name)
        else:
            suite = loader.discover(str(self.test_dir))
        
        # Run tests with custom result collector
        runner = unittest.TextTestRunner(verbosity=2, stream=StringIO())
        result = runner.run(suite)
        
        # Collect results
        self.results['tests_run'] = result.testsRun
        self.results['execution_time'] = time.time() - start_time
        
        # Process failures
        for test, traceback in result.failures:
            self.results['failures'].append({
                'test': str(test),
                'traceback': traceback
            })
        
        # Process errors
        for test, traceback in result.errors:
            self.results['errors'].append({
                'test': str(test),
                'traceback': traceback
            })
        
        # Process successes
        success_count = (result.testsRun - 
                        len(result.failures) - 
                        len(result.errors) - 
                        len(result.skipped))
        self.results['successes'] = [{'count': success_count}]
        
        # Process skipped
        for test, reason in result.skipped:
            self.results['skipped'].append({
                'test': str(test),
                'reason': reason
            })
        
        return self.results
    
    def run_pytest(self, test_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run tests using pytest if available.
        
        Args:
            test_path: Specific test path to run
            
        Returns:
            Test results dictionary
        """
        try:
            import pytest
        except ImportError:
            print("⚠️  pytest not installed. Install with: pip install pytest")
            return {'error': 'pytest not installed'}
        
        start_time = time.time()
        
        # Build pytest arguments
        args = ['-v', '--tb=short']
        
        if test_path:
            args.append(test_path)
        else:
            args.append(str(self.test_dir))
        
        # Capture output
        output = StringIO()
        
        # Run pytest
        exit_code = pytest.main(args)
        
        self.results['execution_time'] = time.time() - start_time
        self.results['pytest_exit_code'] = exit_code
        
        # Parse exit code
        if exit_code == 0:
            self.results['status'] = 'all_passed'
        elif exit_code == 1:
            self.results['status'] = 'tests_failed'
        elif exit_code == 2:
            self.results['status'] = 'interrupted'
        elif exit_code == 3:
            self.results['status'] = 'internal_error'
        elif exit_code == 4:
            self.results['status'] = 'usage_error'
        elif exit_code == 5:
            self.results['status'] = 'no_tests_collected'
        
        return self.results
    
    def run_coverage(self, test_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run tests with coverage analysis.
        
        Args:
            test_path: Specific test path to run
            
        Returns:
            Coverage results dictionary
        """
        try:
            import coverage
        except ImportError:
            print("⚠️  coverage not installed. Install with: pip install coverage")
            return {'error': 'coverage not installed'}
        
        # Create coverage object
        cov = coverage.Coverage()
        cov.start()
        
        # Run tests
        if test_path:
            self.run_unittest(test_path)
        else:
            self.run_unittest()
        
        # Stop coverage and save
        cov.stop()
        cov.save()
        
        # Generate coverage report
        total = cov.report()
        
        # Get detailed coverage data
        coverage_data = {}
        for filename in cov.get_data().measured_files():
            analysis = cov.analysis(filename)
            coverage_data[filename] = {
                'executed_lines': len(analysis[1]),
                'missing_lines': len(analysis[2]),
                'excluded_lines': len(analysis[3]) if len(analysis) > 3 else 0
            }
        
        self.results['coverage'] = {
            'total_percentage': total,
            'files': coverage_data
        }
        
        return self.results['coverage']
    
    def create_test_file(self, module_name: str, class_name: Optional[str] = None) -> str:
        """
        Create a template test file.
        
        Args:
            module_name: Name of the module to test
            class_name: Name of the class to test (optional)
            
        Returns:
            Path to the created test file
        """
        test_filename = f"test_{module_name}.py"
        test_path = self.test_dir / test_filename
        
        # Create tests directory if it doesn't exist
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate test template
        template = f'''"""
Tests for {module_name} module
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.{module_name} import *


class Test{class_name or module_name.title()}(unittest.TestCase):
    """Test cases for {class_name or module_name}."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def tearDown(self):
        """Clean up after tests."""
        pass
    
    def test_example(self):
        """Example test case."""
        self.assertTrue(True)
        
    # Add more test methods here


if __name__ == '__main__':
    unittest.main()
'''
        
        with open(test_path, 'w') as f:
            f.write(template)
        
        print(f"✅ Created test file: {test_path}")
        return str(test_path)
    
    def generate_report(self) -> str:
        """
        Generate a human-readable test report.
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("TEST EXECUTION REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Summary
        report.append("📊 SUMMARY:")
        report.append(f"  Tests run: {self.results['tests_run']}")
        report.append(f"  Execution time: {self.results['execution_time']:.2f}s")
        
        success_count = (self.results['tests_run'] - 
                        len(self.results['failures']) - 
                        len(self.results['errors']))
        
        report.append(f"  ✅ Passed: {success_count}")
        report.append(f"  ❌ Failed: {len(self.results['failures'])}")
        report.append(f"  🔥 Errors: {len(self.results['errors'])}")
        report.append(f"  ⏭️  Skipped: {len(self.results['skipped'])}")
        report.append("")
        
        # Failures
        if self.results['failures']:
            report.append("❌ FAILURES:")
            for failure in self.results['failures']:
                report.append(f"  - {failure['test']}")
                report.append(f"    {failure['traceback'][:200]}...")
            report.append("")
        
        # Errors
        if self.results['errors']:
            report.append("🔥 ERRORS:")
            for error in self.results['errors']:
                report.append(f"  - {error['test']}")
                report.append(f"    {error['traceback'][:200]}...")
            report.append("")
        
        # Coverage
        if self.results['coverage']:
            report.append("📈 COVERAGE:")
            cov = self.results['coverage']
            if 'total_percentage' in cov:
                report.append(f"  Total: {cov['total_percentage']:.1f}%")
            report.append("")
        
        # Status
        if success_count == self.results['tests_run'] and self.results['tests_run'] > 0:
            report.append("✅ ALL TESTS PASSED!")
        elif self.results['tests_run'] == 0:
            report.append("⚠️  NO TESTS FOUND")
        else:
            report.append("❌ SOME TESTS FAILED")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def save_results(self, output_file: str = "test_results.json"):
        """
        Save test results to a JSON file.
        
        Args:
            output_file: Path to output file
        """
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"💾 Results saved to: {output_file}")


def run_tests(test_dir: str = "tests", 
              test_file: Optional[str] = None,
              coverage: bool = False,
              verbose: bool = True) -> Dict[str, Any]:
    """
    Convenience function to run tests.
    
    Args:
        test_dir: Directory containing tests
        test_file: Specific test file to run
        coverage: Whether to run with coverage analysis
        verbose: Whether to print the report
        
    Returns:
        Test results dictionary
    """
    runner = TestRunner(test_dir)
    
    if coverage:
        results = runner.run_coverage(test_file)
    else:
        results = runner.run_unittest(test_file)
    
    if verbose:
        print(runner.generate_report())
    
    return results


# Test the tester if run directly
if __name__ == "__main__":
    import sys
    
    print("\n🧪 Test Runner Demo\n")
    
    # Check if tests directory exists
    test_dir = Path("tests")
    if not test_dir.exists():
        print("⚠️  No 'tests' directory found. Creating example...")
        runner = TestRunner()
        runner.create_test_file("example", "Example")
        print("\n📝 Example test file created. Run your tests with:")
        print("   python src/tools/tester.py")
    else:
        # Run tests
        runner = TestRunner()
        runner.run_unittest()
        print(runner.generate_report())