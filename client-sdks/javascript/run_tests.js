#!/usr/bin/env node
/**
 * Test runner for JavaScript SDK with comprehensive testing options
 */

const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

function runCommand(command, args = [], options = {}) {
  return new Promise((resolve, reject) => {
    console.log(`Running: ${command} ${args.join(" ")}`);

    const child = spawn(command, args, {
      stdio: "inherit",
      shell: true,
      ...options,
    });

    child.on("close", (code) => {
      if (code === 0) {
        resolve(code);
      } else {
        reject(new Error(`Command failed with exit code ${code}`));
      }
    });

    child.on("error", (error) => {
      reject(error);
    });
  });
}

async function installDependencies() {
  console.log("📦 Installing dependencies...");
  try {
    await runCommand("npm", ["install"]);
    console.log("✅ Dependencies installed successfully");
  } catch (error) {
    console.error("❌ Failed to install dependencies:", error.message);
    process.exit(1);
  }
}

async function runUnitTests() {
  console.log("🧪 Running unit tests...");
  try {
    await runCommand("npm", [
      "test",
      "--",
      "--testNamePattern=^(?!.*Integration)",
    ]);
    console.log("✅ Unit tests completed");
  } catch (error) {
    console.error("❌ Unit tests failed:", error.message);
    process.exit(1);
  }
}

async function runIntegrationTests() {
  console.log("🔗 Running integration tests...");
  try {
    await runCommand("npm", ["test", "--", "--testNamePattern=Integration"]);
    console.log("✅ Integration tests completed");
  } catch (error) {
    console.error("❌ Integration tests failed:", error.message);
    process.exit(1);
  }
}

async function runAllTests() {
  console.log("🚀 Running all tests...");
  try {
    await runCommand("npm", ["test"]);
    console.log("✅ All tests completed");
  } catch (error) {
    console.error("❌ Tests failed:", error.message);
    process.exit(1);
  }
}

async function runCoverage() {
  console.log("📊 Running tests with coverage...");
  try {
    await runCommand("npm", ["test", "--", "--coverage"]);
    console.log("📈 Coverage report generated");
  } catch (error) {
    console.error("❌ Coverage tests failed:", error.message);
    process.exit(1);
  }
}

async function runLint() {
  console.log("🔍 Running linter...");
  try {
    await runCommand("npm", ["run", "lint"]);
    console.log("✅ Linting completed");
  } catch (error) {
    console.error("❌ Linting failed:", error.message);
    process.exit(1);
  }
}

async function testExampleUsage() {
  console.log("💡 Testing example usage...");

  try {
    const { AnomalyClient } = require("./anomaly-client");

    // Test basic initialization
    const client = new AnomalyClient("http://localhost:4000", "test-key");
    console.log("✅ SDK imports and initializes correctly");

    // Test health check if service is running
    try {
      const health = await client.healthCheck();
      console.log("✅ Health check successful:", health);
    } catch (error) {
      console.log(
        "⚠️  Health check failed (service may not be running):",
        error.message
      );
    }

    // Test middleware creation
    const middleware = client.expressMiddleware("test-service");
    if (typeof middleware === "function") {
      console.log("✅ Express middleware created successfully");
    }

    const koaMiddleware = client.koaMiddleware("test-service");
    if (typeof koaMiddleware === "function") {
      console.log("✅ Koa middleware created successfully");
    }

    console.log("✅ Example usage test completed");
  } catch (error) {
    console.error("❌ Example usage test failed:", error.message);
    return false;
  }

  return true;
}

function showHelp() {
  console.log(`
🧪 JavaScript SDK Test Runner

Usage: node run_tests.js [options]

Options:
  --install      Install dependencies
  --unit         Run unit tests only
  --integration  Run integration tests only (requires running data collector)
  --coverage     Run tests with coverage report
  --lint         Run linter
  --example      Test example usage
  --all          Run all tests (default)
  --help         Show this help message

Examples:
  node run_tests.js --install --all     # Install deps and run all tests
  node run_tests.js --unit              # Run only unit tests
  node run_tests.js --coverage          # Run with coverage
  node run_tests.js --example           # Test basic functionality
`);
}

async function main() {
  const args = process.argv.slice(2);

  // Change to script directory
  process.chdir(__dirname);

  if (args.includes("--help")) {
    showHelp();
    return;
  }

  if (args.includes("--install")) {
    await installDependencies();
  }

  if (args.includes("--lint")) {
    await runLint();
  }

  if (args.includes("--unit")) {
    await runUnitTests();
  } else if (args.includes("--integration")) {
    await runIntegrationTests();
  } else if (args.includes("--coverage")) {
    await runCoverage();
  } else if (args.includes("--example")) {
    await testExampleUsage();
  } else if (args.includes("--all") || args.length === 0) {
    await runAllTests();
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error("❌ Test runner failed:", error.message);
    process.exit(1);
  });
}

module.exports = {
  installDependencies,
  runUnitTests,
  runIntegrationTests,
  runAllTests,
  runCoverage,
  testExampleUsage,
};
