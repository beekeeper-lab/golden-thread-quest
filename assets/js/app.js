/* Progressive enhancement only.
 *
 * Every generated page is complete and usable before this file runs: navigation is a list
 * of links, filters are a form that submits, disclosures are <details>. This script makes
 * those things faster, and nothing here is the only way to do anything.
 *
 * It never fetches, never writes, and never talks to the local service. State-changing
 * actions are ordinary form submissions, so a browser with JavaScript disabled and a
 * browser with the service stopped both behave honestly.
 */
(function () {
  "use strict";

  // Marks that scripting is available, so CSS can enable the drawer. Without it the
  // navigation stays visible rather than being hidden by a script that never ran.
  document.documentElement.classList.add("js");

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  /* ----------------------------------------------------------- Navigation drawer */

  function initDrawer() {
    var toggle = document.querySelector("[data-nav-toggle]");
    var drawer = document.querySelector("[data-nav-drawer]");
    if (!toggle || !drawer) return;

    function setOpen(open) {
      drawer.setAttribute("data-drawer", open ? "open" : "closed");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }

    setOpen(false);
    toggle.hidden = false;

    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") !== "true";
      setOpen(open);
      if (open) {
        var first = drawer.querySelector("a, button");
        if (first) first.focus();
      }
    });

    // Escape closes the drawer and returns focus to the button that opened it, which is
    // the behaviour the UI specification requires.
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      if (toggle.getAttribute("aria-expanded") !== "true") return;
      setOpen(false);
      toggle.focus();
    });
  }

  /* ----------------------------------------------------------- Catalog filtering */

  function normalise(value) {
    return (value || "").toString().toLowerCase();
  }

  function matches(card, query, filters) {
    if (query) {
      var haystack = normalise(card.getAttribute("data-search"));
      var terms = query.split(/\s+/).filter(Boolean);
      for (var i = 0; i < terms.length; i++) {
        if (haystack.indexOf(terms[i]) === -1) return false;
      }
    }
    for (var key in filters) {
      if (!Object.prototype.hasOwnProperty.call(filters, key)) continue;
      var wanted = filters[key];
      if (!wanted) continue;
      var actual = card.getAttribute("data-" + key);
      if (key === "tag") {
        var tags = (actual || "").split(" ");
        if (tags.indexOf(wanted) === -1) return false;
      } else if (normalise(actual) !== normalise(wanted)) {
        return false;
      }
    }
    return true;
  }

  function initCatalog() {
    var form = document.querySelector("[data-catalog-filter]");
    var results = document.querySelector("[data-catalog-results]");
    if (!form || !results) return;

    var cards = Array.prototype.slice.call(results.querySelectorAll("[data-search]"));
    var count = document.querySelector("[data-result-count]");
    var empty = document.querySelector("[data-empty-results]");
    var submit = form.querySelector("[data-filter-submit]");

    // The form still works without this script, so its submit button is only hidden once
    // filtering has been taken over live.
    if (submit) submit.hidden = true;

    function apply() {
      var data = new FormData(form);
      var query = normalise(data.get("q"));
      var filters = {
        region: data.get("region"),
        state: data.get("state"),
        level: data.get("level"),
        tag: data.get("tag"),
        bookend: data.get("bookend"),
        risk: data.get("risk")
      };
      var shown = 0;
      cards.forEach(function (card) {
        var visible = matches(card, query, filters);
        card.hidden = !visible;
        if (visible) shown += 1;
      });
      if (count) count.textContent = String(shown);
      if (empty) empty.hidden = shown !== 0;

      // Reflect the filters in the URL so a filtered view can be shared or reloaded.
      if (window.history && window.history.replaceState) {
        var params = new URLSearchParams();
        data.forEach(function (value, key) {
          if (value) params.set(key, value.toString());
        });
        var query_string = params.toString();
        window.history.replaceState(null, "", query_string ? "?" + query_string : window.location.pathname);
      }
    }

    form.addEventListener("input", apply);
    form.addEventListener("change", apply);
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      apply();
    });

    var reset = form.querySelector("[data-filter-reset]");
    if (reset) {
      reset.addEventListener("click", function (event) {
        event.preventDefault();
        form.reset();
        apply();
      });
    }

    apply();
  }

  /* ----------------------------------------------------------- Confirmation (C21) */

  function initConfirmations() {
    // A consequential action confirms immediately before it happens, never at the start of
    // a multi-step workflow, so the confirmation is bound to the submit itself.
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        var message = form.getAttribute("data-confirm");
        if (!window.confirm(message)) {
          event.preventDefault();
        }
      });
    });
  }

  /* ----------------------------------------------------------- Timestamps */

  function initTimestamps() {
    // Stored values are ISO 8601 and stay in the `datetime` attribute; only the display
    // text becomes local, so the original is always available to a reader and to a copy.
    document.querySelectorAll("time[datetime][data-format]").forEach(function (element) {
      var value = element.getAttribute("datetime");
      var parsed = new Date(value);
      if (isNaN(parsed.getTime())) return;
      try {
        element.textContent = parsed.toLocaleString();
        element.title = value;
      } catch (error) {
        /* Leave the server-rendered text alone if the locale API is unavailable. */
      }
    });
  }

  ready(function () {
    initDrawer();
    initCatalog();
    initConfirmations();
    initTimestamps();
  });
})();
