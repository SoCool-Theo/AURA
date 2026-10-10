// Acceptance harness for the built worker, with a localhost-only API proxy.
// Start serve-backend-fixture.py first; this never uses a production database.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import worker from "../dist/server/index.js";

const assetsRoot = fileURLToPath(new URL("../dist/client/", import.meta.url));
const types = { ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2" };
const env = { ASSETS: { async fetch(request) {
  const url = new URL(typeof request === "string" ? request : request.url);
  const target = path.resolve(assetsRoot, `.${decodeURIComponent(url.pathname)}`);
  if (!target.startsWith(assetsRoot)) return new Response("Not found", { status: 404 });
  try { return new Response(await readFile(target), { headers: { "Content-Type": types[path.extname(target)] ?? "application/octet-stream" } }); }
  catch { return new Response("Not found", { status: 404 }); }
} } };
const server = createServer(async (incoming, outgoing) => {
  try {
    const url = new URL(incoming.url, "http://127.0.0.1:5192");
    const chunks = []; let size = 0;
    for await (const chunk of incoming) { size += chunk.length; if (size > 65536) throw new Error("Body too large"); chunks.push(chunk); }
    const body = chunks.length ? Buffer.concat(chunks) : undefined;
    const headers = new Headers();
    for (const [key, value] of Object.entries(incoming.headers)) if (value && !["host", "connection", "content-length"].includes(key)) headers.set(key, Array.isArray(value) ? value.join(", ") : value);
    const request = new Request(url, { method: incoming.method, headers, ...(body ? { body } : {}) });
    const asset = url.pathname.startsWith("/api/") ? null : await env.ASSETS.fetch(request);
    const response = url.pathname.startsWith("/api/")
      ? await fetch(`http://127.0.0.1:8019${url.pathname}${url.search}`, { method: request.method, headers, ...(body ? { body } : {}) })
      : asset?.ok ? asset : await worker.fetch(request, env, { waitUntil() {}, passThroughOnException() {} });
    outgoing.writeHead(response.status, Object.fromEntries(response.headers));
    outgoing.end(Buffer.from(await response.arrayBuffer()));
  } catch { outgoing.writeHead(502); outgoing.end("Local acceptance server unavailable"); }
});
server.listen(5192, "127.0.0.1", () => console.log("Synthetic acceptance preview: http://127.0.0.1:5192"));
process.on("SIGINT", () => server.close(() => process.exit(0)));
