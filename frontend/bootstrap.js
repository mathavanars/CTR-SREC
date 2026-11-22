// This module loads shared public app settings before the main app starts.
import config from "./app-config.json" with { type: "json" };

window.APP_CONFIG = config; // Share the single app config with the page scripts.
document.querySelector('meta[name="author"]').content = config.APP_CREDIT; // Fill the author tag from the shared setting.
document.getElementById("app-credit").textContent = config.APP_CREDIT; // Show the same credit beside the footer disclaimer.
import("./app.js"); // Start the app after the shared config is ready.
