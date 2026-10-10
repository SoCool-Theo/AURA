/// <reference types="vite/client" />

// D1 is optional in the existing hosting template. Aura application data uses
// FastAPI/PostgreSQL; getDb() retains its explicit missing-binding guard.
declare namespace Cloudflare {
  interface Env {
    DB?: D1Database;
  }
}
