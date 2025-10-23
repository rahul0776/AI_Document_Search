import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "./index.css";
import App from "./App";
import "./pdf.worker";
import { ThemeProvider } from "./contexts/ThemeContext";

function Upload() {
  return <div className="p-6">Upload page (PDFs go here)</div>;
}
function Chat() {
  return <div className="p-6">Chat page (QA UI)</div>;
}

const router = createBrowserRouter([
  { path: "/", element: <App /> },
  { path: "/upload", element: <Upload /> },
  { path: "/chat", element: <Chat /> },
]);

createRoot(document.getElementById("root")!).render(
  <ThemeProvider>
    <RouterProvider router={router} />
  </ThemeProvider>
);
