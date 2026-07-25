// Omaha Lab UI hooks — Chainlit's `custom_js` config option loads exactly one
// file, so every small DOM patch that CSS alone can't reach lives here as its
// own self-contained IIFE. See CUSTOM_CSS_PLAN.md for the running list.

// The Phoenix Traces header link in .chainlit/config.toml is a static
// "http://localhost:6006" — correct when Chainlit and Phoenix run on the
// same machine (Options A/B), but wrong when viewed remotely (Option C:
// Multipass VM, browser on the Mac) since "localhost" then resolves on the
// browser's own machine, not the VM. Rewrite it to match whatever host the
// page is actually being viewed from, so it works in both cases with no
// per-user config edit.
(function () {
  function fixLocalhostLinks() {
    document.querySelectorAll('a[href*="localhost:6006"]').forEach(function (a) {
      a.href = a.href.replace("localhost", window.location.hostname);
    });
  }

  // The header renders after initial page load (client-side), so a single
  // DOMContentLoaded pass can run before the link exists. Poll briefly.
  var attempts = 0;
  var interval = setInterval(function () {
    fixLocalhostLinks();
    attempts += 1;
    if (attempts > 20) clearInterval(interval); // stop after ~10s
  }, 500);
})();

// Tag <body data-persona="..."> with the active persona slug so theme.css
// can recolor --primary per persona (CUSTOM_CSS_PLAN.md item 5) — makes it
// visually obvious which persona/lab context is currently active.
//
// Two sources, since neither is present at every point in the session:
//   1. The "Ready — persona: **X**" / "Settings changed (persona: **X**...)"
//      messages ui.py prints — present from session start, no user action
//      needed. Matched on our own copy text ("persona:"), not a Chainlit
//      internal class, so it won't break on a Chainlit upgrade.
//   2. The Chat Settings "Persona" combobox (id="persona") — only mounted
//      once the settings drawer has been opened at least once, but reflects
//      a live change instantly, so it's preferred when present.
// Both report the slug in different casing (title-cased in messages, raw
// slug in the combobox); normalize by lowercasing and turning spaces into
// underscores, which maps either form back onto the _PERSONA_OPTIONS keys
// in ui.py (e.g. "Security Analyst" / "security_analyst" -> "security_analyst").
(function () {
  function normalize(label) {
    return label.trim().toLowerCase().replace(/\s+/g, "_");
  }

  function fromCombobox() {
    var combo = document.querySelector('[role="combobox"]#persona');
    return combo && combo.textContent.trim() ? normalize(combo.textContent) : null;
  }

  function fromMessageText() {
    var nodes = document.querySelectorAll('[role="article"]');
    var found = null;
    // Last match wins — messages append in chronological order, so a later
    // "Settings changed" message should override the initial "Ready" one.
    for (var i = 0; i < nodes.length; i++) {
      var match = nodes[i].textContent.match(/persona:\s*([^·,)]+)/i);
      if (match) found = normalize(match[1]);
    }
    return found;
  }

  function syncPersonaAttr() {
    var slug = fromCombobox() || fromMessageText();
    if (slug && document.body.getAttribute("data-persona") !== slug) {
      document.body.setAttribute("data-persona", slug);
    }
  }

  syncPersonaAttr();
  new MutationObserver(syncPersonaAttr).observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
  });
})();
