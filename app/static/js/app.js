// ParaPilot: small client helpers (theme toggle, first-run modal, examples).
(function () {
  "use strict";

  // ---- Theme (light/dark) with persistence + system fallback -------------
  const root = document.documentElement;
  const THEME_KEY = "parapilot-theme";

  function applyTheme(theme) {
    if (theme === "dark") root.classList.add("dark");
    else root.classList.remove("dark");
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved) {
      applyTheme(saved);
    } else {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      applyTheme(prefersDark ? "dark" : "light");
    }
  }

  window.toggleTheme = function () {
    const isDark = root.classList.toggle("dark");
    localStorage.setItem(THEME_KEY, isDark ? "dark" : "light");
  };

  // ---- First-run disclaimer modal ----------------------------------------
  const SEEN_KEY = "parapilot-disclaimer-ack";

  window.dismissDisclaimer = function () {
    const modal = document.getElementById("disclaimer-modal");
    if (modal) modal.classList.add("hidden");
    localStorage.setItem(SEEN_KEY, "1");
  };

  function maybeShowDisclaimer() {
    if (localStorage.getItem(SEEN_KEY)) return;
    const modal = document.getElementById("disclaimer-modal");
    if (modal) modal.classList.remove("hidden");
  }

  // ---- Ask: clicking an example fills + submits the form ------------------
  window.useExample = function (text) {
    const input = document.getElementById("question");
    if (!input) return;
    input.value = text;
    const form = document.getElementById("ask-form");
    if (form && window.htmx) {
      window.htmx.trigger(form, "submit");
    }
  };

  // Initialize theme as early as possible to avoid a flash.
  initTheme();
  document.addEventListener("DOMContentLoaded", maybeShowDisclaimer);
})();
