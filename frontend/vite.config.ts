import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const isGitHubActions = Boolean(
  (globalThis as typeof globalThis & { process?: { env?: Record<string, string | undefined> } })
    .process?.env?.GITHUB_ACTIONS,
);

export default defineConfig({
  plugins: [react()],
  base: isGitHubActions ? "/Real-time-ai-powered-gym-coach/" : "/",
});
