#!/usr/bin/env node
/**
 * faber — npx entry point.
 *
 * A thin shim, on purpose. The installer is `plugins/faber/install.sh`, the
 * same file the Claude Code plugin and `bootstrap.sh` run, so there is exactly
 * one install code path to reason about and to test. This file resolves it,
 * checks the two prerequisites Node can check cheaply, and hands over.
 *
 *   npx @uhitlei/faber                  install into the current directory
 *   npx @uhitlei/faber install ../repo  install into another repository
 *   npx @uhitlei/faber --help           the installer's own help
 */
"use strict";

const { spawnSync } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const INSTALLER = path.join(__dirname, "..", "plugins", "faber", "install.sh");

function die(msg, code = 1) {
  console.error(`faber: ${msg}`);
  process.exit(code);
}

if (process.platform === "win32") {
  die(
    "Windows is not supported directly — the factory is bash and POSIX tooling.\n" +
      "       Run it inside WSL, where git, bash and python3 are available."
  );
}

if (!fs.existsSync(INSTALLER)) {
  die(`the payload is missing (${INSTALLER}).\n       Reinstall the package.`, 2);
}

// `install` is a courtesy verb so `npx @uhitlei/faber install .` reads naturally.
// Everything else is forwarded to install.sh untouched, including --help.
const argv = process.argv.slice(2);
const args = argv[0] === "install" ? argv.slice(1) : argv;

for (const bin of ["git", "python3"]) {
  if (spawnSync(bin, ["--version"], { stdio: "ignore" }).status !== 0) {
    die(`${bin} is required and was not found on PATH.`);
  }
}

const r = spawnSync("bash", [INSTALLER, ...args], { stdio: "inherit" });
if (r.error) die(`could not run bash: ${r.error.message}`, 2);
process.exit(r.status === null ? 1 : r.status);
