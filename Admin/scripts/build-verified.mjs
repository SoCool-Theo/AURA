// Cross-platform equivalent of the bounded build; no shell or global tooling.
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const cli = fileURLToPath(new URL("../node_modules/vinext/dist/cli.js", import.meta.url));
const child = spawn(process.execPath, [cli, "build"], {
  cwd: root,
  stdio: "inherit",
  env: {
    ...process.env,
    WRANGLER_WRITE_LOGS: "false",
    WRANGLER_LOG_PATH: ".wrangler/logs",
    MINIFLARE_REGISTRY_PATH: ".wrangler/registry",
  },
});
const timeout = setTimeout(() => {
  console.error("Admin build exceeded the three-minute limit.");
  child.kill();
  process.exitCode = 124;
}, 180_000);
child.on("error", error => {
  clearTimeout(timeout);
  console.error(`Unable to start admin build: ${error.message}`);
  process.exitCode = 1;
});
child.on("exit", code => {
  clearTimeout(timeout);
  process.exitCode ??= code ?? 1;
});
