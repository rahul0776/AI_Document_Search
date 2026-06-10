import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";
import "./pdf.worker";
import { ThemeProvider } from "./contexts/ThemeContext";

// App handles its own path-based routing (/, /app, /verify-email,
// /reset-password, /forgot-password) — no router layer needed.
createRoot(document.getElementById("root")!).render(
  <ThemeProvider>
    <App />
  </ThemeProvider>
);
