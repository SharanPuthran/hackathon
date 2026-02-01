#!/usr/bin/env node

/**
 * Environment Variable Validation Script
 *
 * This script validates that all required environment variables are set
 * before building the frontend application. It should be run as a pre-build
 * step to catch configuration errors early.
 *
 * Usage:
 *   node validate-env.js
 *   npm run validate:env
 *
 * Exit codes:
 *   0 - All required variables are set
 *   1 - One or more required variables are missing
 */

import { readFileSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

// Get current directory (ESM equivalent of __dirname)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ANSI color codes for terminal output
const colors = {
  reset: "\x1b[0m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  cyan: "\x1b[36m",
};

/**
 * Required environment variables for the frontend application
 * These must be prefixed with VITE_ to be exposed to the client
 */
const REQUIRED_VARIABLES = [
  {
    name: "VITE_GEMINI_API_KEY",
    description: "API key for Google Gemini AI integration",
    example: "AIzaSyD1234567890abcdefghijklmnopqrstuvwxyz",
    required: true,
  },
];

/**
 * Optional environment variables (for documentation purposes)
 */
const OPTIONAL_VARIABLES = [
  {
    name: "GEMINI_API_KEY",
    description: "Legacy API key (automatically mapped to VITE_GEMINI_API_KEY)",
    example: "AIzaSyD1234567890abcdefghijklmnopqrstuvwxyz",
    required: false,
  },
];

/**
 * Load environment variables from .env files
 * Vite automatically loads these, but we need to check them manually
 */
function loadEnvFile(filename) {
  const envPath = resolve(__dirname, filename);

  if (!existsSync(envPath)) {
    return {};
  }

  try {
    const content = readFileSync(envPath, "utf-8");
    const env = {};

    // Parse .env file format
    content.split("\n").forEach((line) => {
      // Skip comments and empty lines
      if (line.trim().startsWith("#") || !line.trim()) {
        return;
      }

      // Parse KEY=VALUE format
      const match = line.match(/^([^=]+)=(.*)$/);
      if (match) {
        const key = match[1].trim();
        let value = match[2].trim();

        // Remove quotes if present
        if (
          (value.startsWith('"') && value.endsWith('"')) ||
          (value.startsWith("'") && value.endsWith("'"))
        ) {
          value = value.slice(1, -1);
        }

        env[key] = value;
      }
    });

    return env;
  } catch (error) {
    console.error(
      `${colors.red}Error reading ${filename}:${colors.reset}`,
      error.message,
    );
    return {};
  }
}

/**
 * Get environment variable value from multiple sources
 * Priority: process.env > .env.local > .env
 */
function getEnvValue(varName, envFiles) {
  // Check process environment first
  if (process.env[varName]) {
    return process.env[varName];
  }

  // Check .env.local
  if (envFiles.local && envFiles.local[varName]) {
    return envFiles.local[varName];
  }

  // Check .env
  if (envFiles.default && envFiles.default[varName]) {
    return envFiles.default[varName];
  }

  return null;
}

/**
 * Validate that a variable value is not a placeholder
 */
function isValidValue(value) {
  if (!value) {
    return false;
  }

  // Check for common placeholder patterns
  const placeholders = [
    "your_",
    "placeholder",
    "example",
    "test_key_for_validation",
    "PLACEHOLDER",
    "YOUR_",
    "EXAMPLE_",
  ];

  const lowerValue = value.toLowerCase();
  return !placeholders.some((placeholder) =>
    lowerValue.includes(placeholder.toLowerCase()),
  );
}

/**
 * Main validation function
 */
function validateEnvironment() {
  console.log(
    `${colors.cyan}========================================${colors.reset}`,
  );
  console.log(`${colors.cyan}Environment Variable Validation${colors.reset}`);
  console.log(
    `${colors.cyan}========================================${colors.reset}\n`,
  );

  // Load environment files
  const envFiles = {
    default: loadEnvFile(".env"),
    local: loadEnvFile(".env.local"),
  };

  // Check which files exist
  const hasEnvFile = existsSync(resolve(__dirname, ".env"));
  const hasEnvLocalFile = existsSync(resolve(__dirname, ".env.local"));

  if (!hasEnvFile && !hasEnvLocalFile) {
    console.log(
      `${colors.yellow}⚠ Warning: No .env or .env.local file found${colors.reset}`,
    );
    console.log(
      `${colors.yellow}  Environment variables must be set in the shell environment${colors.reset}\n`,
    );
  } else {
    console.log(`${colors.blue}Found environment files:${colors.reset}`);
    if (hasEnvFile) console.log(`  ✓ .env`);
    if (hasEnvLocalFile) console.log(`  ✓ .env.local`);
    console.log();
  }

  // Validate required variables
  const missingVars = [];
  const invalidVars = [];
  const validVars = [];

  console.log(`${colors.blue}Checking required variables:${colors.reset}\n`);

  REQUIRED_VARIABLES.forEach((variable) => {
    const value = getEnvValue(variable.name, envFiles);

    if (!value) {
      console.log(`${colors.red}✗ ${variable.name}${colors.reset}`);
      console.log(`  Status: Missing`);
      console.log(`  Description: ${variable.description}`);
      console.log(`  Example: ${variable.example}\n`);
      missingVars.push(variable);
    } else if (!isValidValue(value)) {
      console.log(`${colors.yellow}⚠ ${variable.name}${colors.reset}`);
      console.log(`  Status: Set but appears to be a placeholder`);
      console.log(`  Current value: ${value}`);
      console.log(`  Description: ${variable.description}`);
      console.log(`  Example: ${variable.example}\n`);
      invalidVars.push(variable);
    } else {
      console.log(`${colors.green}✓ ${variable.name}${colors.reset}`);
      console.log(`  Status: Valid`);
      console.log(`  Value: ${value.substring(0, 20)}...${colors.reset}\n`);
      validVars.push(variable);
    }
  });

  // Show optional variables
  if (OPTIONAL_VARIABLES.length > 0) {
    console.log(`${colors.blue}Optional variables:${colors.reset}\n`);

    OPTIONAL_VARIABLES.forEach((variable) => {
      const value = getEnvValue(variable.name, envFiles);

      if (value && isValidValue(value)) {
        console.log(`${colors.green}✓ ${variable.name}${colors.reset}`);
        console.log(`  Status: Set`);
        console.log(`  Description: ${variable.description}\n`);
      } else {
        console.log(`${colors.blue}○ ${variable.name}${colors.reset}`);
        console.log(`  Status: Not set (optional)`);
        console.log(`  Description: ${variable.description}\n`);
      }
    });
  }

  // Summary
  console.log(
    `${colors.cyan}========================================${colors.reset}`,
  );
  console.log(`${colors.cyan}Validation Summary${colors.reset}`);
  console.log(
    `${colors.cyan}========================================${colors.reset}\n`,
  );

  console.log(
    `Valid variables:   ${colors.green}${validVars.length}${colors.reset}`,
  );
  console.log(
    `Invalid variables: ${colors.yellow}${invalidVars.length}${colors.reset}`,
  );
  console.log(
    `Missing variables: ${colors.red}${missingVars.length}${colors.reset}\n`,
  );

  // Exit with error if validation failed
  if (missingVars.length > 0 || invalidVars.length > 0) {
    console.log(`${colors.red}❌ Validation failed!${colors.reset}\n`);

    console.log(`${colors.yellow}To fix this:${colors.reset}`);
    console.log(`  1. Copy .env.example to .env or .env.local:`);
    console.log(`     ${colors.cyan}cp .env.example .env.local${colors.reset}`);
    console.log();
    console.log(
      `  2. Edit the file and replace placeholder values with actual values`,
    );
    console.log();
    console.log(`  3. Run this validation script again:`);
    console.log(`     ${colors.cyan}npm run validate:env${colors.reset}`);
    console.log();
    console.log(`  4. Once validation passes, build the application:`);
    console.log(`     ${colors.cyan}npm run build${colors.reset}\n`);

    process.exit(1);
  }

  console.log(
    `${colors.green}✅ All required environment variables are valid!${colors.reset}\n`,
  );
  console.log(
    `${colors.blue}You can now build the application:${colors.reset}`,
  );
  console.log(`  ${colors.cyan}npm run build${colors.reset}\n`);

  process.exit(0);
}

// Run validation
validateEnvironment();
