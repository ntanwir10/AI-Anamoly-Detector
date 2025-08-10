#!/usr/bin/env python3
"""
Test runner for Python SDK with comprehensive testing options
"""

import subprocess
import sys
import argparse
import os


def run_command(cmd, check=True):
    """Run a command and return the result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def install_dependencies():
    """Install test dependencies"""
    print("📦 Installing test dependencies...")
    run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])


def run_unit_tests():
    """Run unit tests only"""
    print("🧪 Running unit tests...")
    run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "test_anomaly_client.py",
            "-v",
            "--tb=short",
            "-m",
            "not integration",
        ]
    )


def run_integration_tests():
    """Run integration tests (requires running data collector)"""
    print("🔗 Running integration tests...")
    run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "test_anomaly_client.py",
            "-v",
            "--tb=short",
            "-m",
            "integration",
        ]
    )


def run_all_tests():
    """Run all tests"""
    print("🚀 Running all tests...")
    run_command(
        [sys.executable, "-m", "pytest", "test_anomaly_client.py", "-v", "--tb=short"]
    )


def run_coverage():
    """Run tests with coverage report"""
    print("📊 Running tests with coverage...")
    run_command(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "pytest",
            "test_anomaly_client.py",
            "-v",
        ]
    )
    run_command([sys.executable, "-m", "coverage", "report"])
    run_command([sys.executable, "-m", "coverage", "html"])
    print("📈 Coverage report generated in htmlcov/")


def test_example_usage():
    """Test the example usage in the SDK"""
    print("💡 Testing example usage...")
    try:
        # Try to import and create client
        from anomaly_client import AnomalyClient

        client = AnomalyClient("http://localhost:4000", api_key="test-key")
        print("✅ SDK imports and initializes correctly")

        # Test health check if service is running
        try:
            health = client.health_check()
            print(f"✅ Health check successful: {health}")
        except Exception as e:
            print(f"⚠️  Health check failed (service may not be running): {e}")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Test runner for Python SDK")
    parser.add_argument("--install", action="store_true", help="Install dependencies")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Run with coverage report"
    )
    parser.add_argument("--example", action="store_true", help="Test example usage")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")

    args = parser.parse_args()

    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if args.install:
        install_dependencies()

    if args.unit:
        run_unit_tests()
    elif args.integration:
        run_integration_tests()
    elif args.coverage:
        run_coverage()
    elif args.example:
        test_example_usage()
    elif args.all or not any(
        [args.unit, args.integration, args.coverage, args.example]
    ):
        run_all_tests()


if __name__ == "__main__":
    main()
