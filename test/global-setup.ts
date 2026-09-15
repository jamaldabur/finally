import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Starts the containerized app fresh for the run (LLM_MOCK=true, isolated
// throwaway volume — see docker-compose.test.yml) and blocks until its
// healthcheck passes. Using `up -d --wait` here (rather than Playwright's
// `webServer.command`) because killing a foregrounded `docker compose up`
// process doesn't reliably stop the containers on every platform; global
// teardown explicitly runs `down -v` instead.
export default function globalSetup() {
  execSync("docker compose -f docker-compose.test.yml up -d --build --force-recreate --wait", {
    stdio: "inherit",
    cwd: __dirname,
  });
}
