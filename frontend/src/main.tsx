import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { lazy, Suspense } from "react";
const Benchmark = lazy(() => import("./components/VisionBenchmark"));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {new URLSearchParams(location.search).has("benchmark") ? <Suspense fallback="Loading benchmark…"><Benchmark /></Suspense> : <App />}
  </StrictMode>,
);
