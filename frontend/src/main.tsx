import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import "./index.css";

if ("serviceWorker" in navigator) {
  // Minimal SW just for PWA lifecycle support. No offline caching of API/auth responses.
  window.addEventListener("load", () => {
    void navigator.serviceWorker
      .register("/sw.js")
      .catch(() => {
        // ignore registration failures
      });
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
