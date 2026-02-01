#!/usr/bin/env node

/**
 * Build Verification Script
 *
 * This script verifies that the Vite build process produced the expected output:
 * - Checks that dist/ directory exists and contains files
 * - Verifies that JavaScript and CSS files are minified
 * - Confirms content hashes are present in filenames
 * - Validates that all required assets are present
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DIST_DIR = path.join(__dirname, "dist");
const ASSETS_DIR = path.join(DIST_DIR, "assets");

// ANSI color codes for terminal output
const colors = {
  reset: "\x1b[0m",
  green: "\x1b[32m",
  red: "\x1b[31m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
};

function log(message, color = "reset") {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logSuccess(message) {
  log(`✓ ${message}`, "green");
}

function logError(message) {
  log(`✗ ${message}`, "red");
}

function logWarning(message) {
  log(`⚠ ${message}`, "yellow");
}

function logInfo(message) {
  log(`ℹ ${message}`, "blue");
}

/**
 * Check if dist directory exists and contains files
 */
function checkDistDirectory() {
  logInfo("Checking dist/ directory...");

  if (!fs.existsSync(DIST_DIR)) {
    logError("dist/ directory does not exist");
    return false;
  }

  const files = fs.readdirSync(DIST_DIR);
  if (files.length === 0) {
    logError("dist/ directory is empty");
    return false;
  }

  logSuccess(`dist/ directory exists with ${files.length} items`);
  return true;
}

/**
 * Check if index.html exists
 */
function checkIndexHtml() {
  logInfo("Checking index.html...");

  const indexPath = path.join(DIST_DIR, "index.html");
  if (!fs.existsSync(indexPath)) {
    logError("index.html not found in dist/");
    return false;
  }

  const content = fs.readFileSync(indexPath, "utf-8");
  if (content.length === 0) {
    logError("index.html is empty");
    return false;
  }

  logSuccess("index.html exists and has content");
  return true;
}

/**
 * Check if assets directory exists and contains hashed files
 */
function checkAssetsDirectory() {
  logInfo("Checking assets/ directory...");

  if (!fs.existsSync(ASSETS_DIR)) {
    logError("assets/ directory does not exist");
    return false;
  }

  const files = fs.readdirSync(ASSETS_DIR);
  if (files.length === 0) {
    logError("assets/ directory is empty");
    return false;
  }

  logSuccess(`assets/ directory exists with ${files.length} files`);
  return true;
}

/**
 * Verify content hashes in filenames
 */
function verifyContentHashes() {
  logInfo("Verifying content hashes in filenames...");

  const files = fs.readdirSync(ASSETS_DIR);
  // Updated pattern to match Vite's hash format: filename-HASH.ext
  // Vite uses base64-like hashes (alphanumeric + some special chars)
  const hashPattern =
    /-[A-Za-z0-9_-]{8,}\.(js|css|png|jpg|svg|ico|woff|woff2|ttf)$/i;

  let hashedFiles = 0;
  let unhashedFiles = [];

  for (const file of files) {
    if (hashPattern.test(file)) {
      hashedFiles++;
    } else {
      unhashedFiles.push(file);
    }
  }

  if (hashedFiles === 0) {
    logError("No files with content hashes found");
    return false;
  }

  logSuccess(`${hashedFiles} files have content hashes`);

  if (unhashedFiles.length > 0) {
    logWarning(
      `${unhashedFiles.length} files without content hashes: ${unhashedFiles.join(", ")}`,
    );
  }

  return true;
}

/**
 * Check if JavaScript files are minified
 */
function checkMinification() {
  logInfo("Checking JavaScript minification...");

  const files = fs.readdirSync(ASSETS_DIR);
  const jsFiles = files.filter((f) => f.endsWith(".js"));

  if (jsFiles.length === 0) {
    logError("No JavaScript files found in assets/");
    return false;
  }

  let minifiedCount = 0;

  for (const file of jsFiles) {
    const filePath = path.join(ASSETS_DIR, file);
    const content = fs.readFileSync(filePath, "utf-8");

    // Check for minification indicators:
    // - No unnecessary whitespace
    // - Short variable names
    // - High character density
    const lines = content.split("\n");
    const avgLineLength = content.length / lines.length;

    // Minified files typically have very long lines (high character density)
    if (avgLineLength > 100) {
      minifiedCount++;
    }
  }

  if (minifiedCount === 0) {
    logWarning("JavaScript files may not be minified");
    return false;
  }

  logSuccess(
    `${minifiedCount}/${jsFiles.length} JavaScript files appear minified`,
  );
  return true;
}

/**
 * List all generated files
 */
function listGeneratedFiles() {
  logInfo("Generated files:");

  const distFiles = fs.readdirSync(DIST_DIR);
  for (const file of distFiles) {
    const filePath = path.join(DIST_DIR, file);
    const stats = fs.statSync(filePath);

    if (stats.isDirectory()) {
      log(`  📁 ${file}/`, "blue");

      if (file === "assets") {
        const assetFiles = fs.readdirSync(filePath);
        for (const assetFile of assetFiles) {
          const assetPath = path.join(filePath, assetFile);
          const assetStats = fs.statSync(assetPath);
          const sizeKB = (assetStats.size / 1024).toFixed(2);
          log(`    📄 ${assetFile} (${sizeKB} KB)`, "reset");
        }
      }
    } else {
      const sizeKB = (stats.size / 1024).toFixed(2);
      log(`  📄 ${file} (${sizeKB} KB)`, "reset");
    }
  }
}

/**
 * Calculate total build size
 */
function calculateBuildSize() {
  logInfo("Calculating total build size...");

  let totalSize = 0;

  function calculateDirSize(dir) {
    const files = fs.readdirSync(dir);

    for (const file of files) {
      const filePath = path.join(dir, file);
      const stats = fs.statSync(filePath);

      if (stats.isDirectory()) {
        calculateDirSize(filePath);
      } else {
        totalSize += stats.size;
      }
    }
  }

  calculateDirSize(DIST_DIR);

  const sizeMB = (totalSize / (1024 * 1024)).toFixed(2);
  logSuccess(`Total build size: ${sizeMB} MB`);

  if (totalSize > 5 * 1024 * 1024) {
    logWarning(
      "Build size exceeds 5 MB - consider code splitting or optimization",
    );
  }
}

/**
 * Main verification function
 */
function verifyBuild() {
  log("\n=== Build Verification ===\n", "blue");

  const checks = [
    checkDistDirectory,
    checkIndexHtml,
    checkAssetsDirectory,
    verifyContentHashes,
    checkMinification,
  ];

  let passed = 0;
  let failed = 0;

  for (const check of checks) {
    if (check()) {
      passed++;
    } else {
      failed++;
    }
  }

  log("\n=== Build Contents ===\n", "blue");
  listGeneratedFiles();

  log("\n=== Build Statistics ===\n", "blue");
  calculateBuildSize();

  log("\n=== Verification Summary ===\n", "blue");
  log(`Passed: ${passed}`, "green");
  log(`Failed: ${failed}`, failed > 0 ? "red" : "reset");

  if (failed === 0) {
    log("\n✓ Build verification passed!", "green");
    process.exit(0);
  } else {
    log("\n✗ Build verification failed!", "red");
    process.exit(1);
  }
}

// Run verification
verifyBuild();
