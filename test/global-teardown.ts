import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Always tears down the throwaway stack and its volume, pass or fail.
export default function globalTeardown() {
  execSync("docker compose -f docker-compose.test.yml down -v", {
    stdio: "inherit",
    cwd: __dirname,
  });
}
