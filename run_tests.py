#!/usr/bin/env python3
"""
Comprehensive test runner for RAG system.
Provides different test execution modes and reporting options.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any


class TestRunner:
    """Main test runner for the RAG system."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.project_root = Path(__file__).parent
        self.test_dir = self.project_root / "tests"
        self.reports_dir = self.project_root / "test_reports"
        
        # Ensure reports directory exists
        self.reports_dir.mkdir(exist_ok=True)
    
    def run_command(self, cmd: List[str], cwd: Path = None) -> Dict[str, Any]:
        """Run a command and return results."""
        if cwd is None:
            cwd = self.project_root
        
        if self.verbose:
            print(f"Running: {' '.join(cmd)}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            duration = time.time() - start_time
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': duration
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timed out',
                'duration': time.time() - start_time
            }
        except Exception as e:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': time.time() - start_time
            }
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests."""
        print("Running unit tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-c", "config/pytest.ini",
            "-m", "unit or not (integration or performance or load)",
            "--tb=short",
            f"--html={self.reports_dir}/unit_tests.html",
            "--self-contained-html",
            f"--junit-xml={self.reports_dir}/unit_tests.xml",
            "--cov=.",
            f"--cov-report=html:{self.reports_dir}/unit_coverage",
            "--cov-report=term-missing"
        ]
        
        if self.verbose:
            cmd.append("-v")
        
        return self.run_command(cmd)
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        print("Running integration tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-c", "config/pytest.ini",
            "-m", "integration",
            "--tb=short",
            f"--html={self.reports_dir}/integration_tests.html",
            "--self-contained-html",
            f"--junit-xml={self.reports_dir}/integration_tests.xml"
        ]
        
        if self.verbose:
            cmd.append("-v")
        
        return self.run_command(cmd)
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        print("Running performance tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-c", "config/pytest.ini",
            "-m", "performance",
            "--tb=short",
            f"--html={self.reports_dir}/performance_tests.html",
            "--self-contained-html",
            f"--junit-xml={self.reports_dir}/performance_tests.xml",
            "--timeout=600"  # 10 minute timeout for performance tests
        ]
        
        if self.verbose:
            cmd.append("-v")
        
        return self.run_command(cmd)
    
    def run_load_tests(self) -> Dict[str, Any]:
        """Run load tests."""
        print("Running load tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-c", "config/pytest.ini",
            "-m", "load",
            "--tb=short",
            f"--html={self.reports_dir}/load_tests.html",
            "--self-contained-html",
            f"--junit-xml={self.reports_dir}/load_tests.xml",
            "--timeout=900"  # 15 minute timeout for load tests
        ]
        
        if self.verbose:
            cmd.append("-v")
        
        return self.run_command(cmd)
    
    def run_smoke_tests(self) -> Dict[str, Any]:
        """Run smoke tests for quick validation."""
        print("Running smoke tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-c", "config/pytest.ini",
            "-m", "smoke",
            "--tb=line",
            f"--junit-xml={self.reports_dir}/smoke_tests.xml"
        ]
        
        if self.verbose:
            cmd.append("-v")
        
        return self.run_command(cmd)
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests."""
        print("Running all tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-c", "config/pytest.ini",
            "--tb=short",
            f"--html={self.reports_dir}/all_tests.html",
            "--self-contained-html",
            f"--junit-xml={self.reports_dir}/all_tests.xml",
            "--cov=.",
            f"--cov-report=html:{self.reports_dir}/full_coverage",
            "--cov-report=term-missing",
            "--timeout=900"
        ]
        
        if self.verbose:
            cmd.append("-v")
        
        return self.run_command(cmd)
    
    def run_specific_test(self, test_path: str) -> Dict[str, Any]:
        """Run a specific test file or test function."""
        print(f"Running specific test: {test_path}")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "-c", "config/pytest.ini",
            test_path,
            "--tb=short"
        ]
        
        if self.verbose:
            cmd.append("-v")
        
        return self.run_command(cmd)
    
    def check_code_quality(self) -> Dict[str, Any]:
        """Run code quality checks."""
        print("Running code quality checks...")
        
        results = {}
        
        # Run flake8 for style checking
        flake8_cmd = ["flake8", ".", "--max-line-length=100", "--exclude=.venv,venv,__pycache__"]
        results['flake8'] = self.run_command(flake8_cmd)
        
        # Run mypy for type checking
        mypy_cmd = ["mypy", ".", "--ignore-missing-imports"]
        results['mypy'] = self.run_command(mypy_cmd)
        
        # Run bandit for security checking
        bandit_cmd = ["bandit", "-r", ".", "-x", ".venv,venv,tests"]
        results['bandit'] = self.run_command(bandit_cmd)
        
        return results
    
    def generate_test_summary(self, results: Dict[str, Dict[str, Any]]) -> None:
        """Generate a summary of test results."""
        print("\n" + "="*60)
        print("TEST EXECUTION SUMMARY")
        print("="*60)
        
        total_duration = 0
        total_success = True
        
        for test_type, result in results.items():
            status = "PASSED" if result['success'] else "FAILED"
            duration = result['duration']
            total_duration += duration
            
            if not result['success']:
                total_success = False
            
            print(f"{test_type.upper():<20} {status:<8} ({duration:.2f}s)")
            
            if not result['success'] and result['stderr']:
                print(f"  Error: {result['stderr'][:100]}...")
        
        print("-" * 60)
        print(f"OVERALL STATUS: {'PASSED' if total_success else 'FAILED'}")
        print(f"TOTAL DURATION: {total_duration:.2f}s")
        print(f"REPORTS LOCATION: {self.reports_dir}")
        print("="*60)
        
        return total_success
    
    def cleanup_reports(self) -> None:
        """Clean up old test reports."""
        if self.reports_dir.exists():
            for file in self.reports_dir.glob("*"):
                if file.is_file():
                    file.unlink()
        print(f"Cleaned up reports directory: {self.reports_dir}")


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="RAG System Test Runner")
    
    parser.add_argument("--type", choices=[
        "unit", "integration", "performance", "load", "smoke", "all", "quality"
    ], default="all", help="Type of tests to run")
    
    parser.add_argument("--test", type=str, help="Specific test file or function to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old reports before running")
    parser.add_argument("--ci", action="store_true", help="CI mode (exit with error code on failure)")
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose)
    
    if args.cleanup:
        runner.cleanup_reports()
    
    results = {}
    
    try:
        if args.test:
            # Run specific test
            results['specific'] = runner.run_specific_test(args.test)
        
        elif args.type == "unit":
            results['unit'] = runner.run_unit_tests()
        
        elif args.type == "integration":
            results['integration'] = runner.run_integration_tests()
        
        elif args.type == "performance":
            results['performance'] = runner.run_performance_tests()
        
        elif args.type == "load":
            results['load'] = runner.run_load_tests()
        
        elif args.type == "smoke":
            results['smoke'] = runner.run_smoke_tests()
        
        elif args.type == "quality":
            results.update(runner.check_code_quality())
        
        elif args.type == "all":
            results['unit'] = runner.run_unit_tests()
            results['integration'] = runner.run_integration_tests()
            results['performance'] = runner.run_performance_tests()
            results['load'] = runner.run_load_tests()
            
            # Also run quality checks
            quality_results = runner.check_code_quality()
            results.update(quality_results)
        
        # Generate summary
        success = runner.generate_test_summary(results)
        
        # Exit with appropriate code for CI
        if args.ci and not success:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()