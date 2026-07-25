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
