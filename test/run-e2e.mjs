#!/usr/bin/env node

/**
 * Portable one-command E2E runner (P-16, TEST-05). Pre-cleans, runs, and
 * always tears down the compose project regardless of the suite's exit
 * code — a contract that has no single portable npm-script spelling across
 * cmd.exe and POSIX shells, hence a plain Node script using
 * child_process.spawnSync rather than a shell one-liner. Steps:
 *
 *   1. `down -v --remove-orphans` — removes any leftover volume from an
 *      earlier interrupted run, so this run always starts from a
 *      genuinely fresh database (idempotency, see 06-05-PLAN.md
 *      must_haves.truths).
 *   2. `up --build --abort-on-container-exit --exit-code-from playwright`
 *      — builds both images, waits on the app's own HEALTHCHECK
 *      (service_healthy, D-08), then runs the suite.
 *   3. `down -v --remove-orphans` again — always, whether step 2 passed,
 *      failed, or was interrupted — so no `finally-e2e` volume or
 *      container ever survives this script.
 *   4. Exit with the suite's own status code from step 2, not step 1 or 3.
 */

import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const COMPOSE_FILE = fileURLToPath(
  new URL("./docker-compose.test.yml", import.meta.url),
);

function compose(args) {
  const result = spawnSync("docker", ["compose", "-f", COMPOSE_FILE, ...args], {
    stdio: "inherit",
  });

  if (result.error) {
    console.error(`Failed to run "docker compose ${args.join(" ")}": ${result.error.message}`);
    return 1;
  }

  // A null status means the process was killed by a signal rather than
  // exiting normally — treat that as failure rather than as a falsy 0.
  return result.status === null ? 1 : result.status;
}

compose(["down", "-v", "--remove-orphans"]);

const suiteStatus = compose([
  "up",
  "--build",
  "--abort-on-container-exit",
  "--exit-code-from",
  "playwright",
]);

compose(["down", "-v", "--remove-orphans"]);

process.exit(suiteStatus);
