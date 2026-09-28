// HireSense AI Frontend Configuration
// When deployed on Vercel, requests use relative paths ('') so they route to /api automatically.
// In local Vite dev server, it points to http://localhost:8000 (or uses Vite proxy).
export const API_BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "http://localhost:8000" : "");
