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
        // data-tag holds space-separated values, and a tag can never contain a space.
        var tags = (actual || "").split(" ");
        if (tags.indexOf(wanted) === -1) return false;
      } else if (key === "time") {
        // "Have I got half an hour?" — an upper bound, not an exact match.
        if (parseInt(card.getAttribute("data-minutes"), 10) > parseInt(wanted, 10)) return false;
      } else if (normalise(actual) !== normalise(wanted)) {
        return false;
      }
    }
    return true;
  }

  var SORTS = {
    title: function (a, b) {
      return a.getAttribute("data-title").localeCompare(b.getAttribute("data-title"));
    },
    time: function (a, b) {
      return a.getAttribute("data-minutes") - b.getAttribute("data-minutes");
    },
    xp: function (a, b) {
      return b.getAttribute("data-xp") - a.getAttribute("data-xp");
    },
    state: function (a, b) {
      return a.getAttribute("data-state").localeCompare(b.getAttribute("data-state"));
    }
  };

  var FILTER_LABELS = {
    q: "Search",
    region: "Region",
    state: "State",
    level: "Difficulty",
    tag: "Tag",
    bookend: "Bookend",
    risk: "Risk",
    time: "Time"
  };

  function initCatalog() {
    var form = document.querySelector("[data-catalog-filter]");
    var results = document.querySelector("[data-catalog-results]");
    if (!form || !results) return;

    var cards = Array.prototype.slice.call(results.querySelectorAll("[data-search]"));
    var count = document.querySelector("[data-result-count]");
    var empty = document.querySelector("[data-empty-results]");
    var submit = form.querySelector("[data-filter-submit]");

    // Only hidden once this script has taken filtering over. Without it the button is the
    // honest affordance: it reloads the page, which shows everything.
    if (submit) submit.hidden = true;

    // Prime the form from the query string, so a shared or bookmarked filtered URL opens
    // filtered rather than silently showing everything.
    try {
      var incoming = new URLSearchParams(window.location.search);
      incoming.forEach(function (value, key) {
        var field = form.elements[key];
        if (field && typeof field.value !== "undefined") field.value = value;
      });
    } catch (error) {
      /* No URLSearchParams, or an opaque origin: fall back to an unfiltered view. */
    }

    function apply() {
      var data = new FormData(form);
      var query = normalise(data.get("q"));
      var filters = {
        region: data.get("region"),
        state: data.get("state"),
        level: data.get("level"),
        tag: data.get("tag"),
        bookend: data.get("bookend"),
        risk: data.get("risk"),
        time: data.get("time")
      };
      var shown = 0;
      cards.forEach(function (card) {
        var visible = matches(card, query, filters);
        card.hidden = !visible;
        if (visible) shown += 1;
      });
      if (count) count.textContent = String(shown);
      if (empty) empty.hidden = shown !== 0;

      var sort = data.get("sort");
      if (sort && SORTS[sort]) {
        cards
          .slice()
          .sort(SORTS[sort])
          .forEach(function (card) {
            results.appendChild(card);
          });
      }

      renderChips(form, data, filters, apply);

      // Reflect the filters in the URL so a filtered view can be shared or reloaded.
      // Wrapped because replaceState throws SecurityError on a file:// page, where the
      // origin is opaque — which made every keystroke end in an uncaught exception.
      try {
        if (window.history && window.history.replaceState) {
          var params = new URLSearchParams();
          data.forEach(function (value, key) {
            if (value) params.set(key, value.toString());
          });
          var query = params.toString();
          window.history.replaceState(null, "", query ? "?" + query : window.location.pathname);
        }
      } catch (error) {
        /* A file:// page cannot rewrite its own URL. Filtering still works. */
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

  /* C07's removable-filter variant: each active filter is a chip whose button clears just
     that one. Rebuilt on every apply, because the alternative — patching chips in place —
     is where this kind of code drifts out of step with the form it describes. */
  function renderChips(form, data, filters, apply) {
    var container = form.parentNode.querySelector("[data-active-filters]");
    if (!container) return;
    container.innerHTML = "";

    var active = {};
    var query = data.get("q");
    if (query) active.q = query;
    for (var key in filters) {
      if (Object.prototype.hasOwnProperty.call(filters, key) && filters[key]) {
        active[key] = filters[key];
      }
    }

    Object.keys(active).forEach(function (key) {
      var item = document.createElement("li");
      var button = document.createElement("button");
      button.type = "button";
      button.className = "chip";
      button.textContent = (FILTER_LABELS[key] || key) + ": " + active[key] + " ✕";
      button.setAttribute("aria-label", "Remove the " + (FILTER_LABELS[key] || key) + " filter");
      button.addEventListener("click", function () {
        var field = form.elements[key];
        if (field) field.value = "";
        apply();
        var first = form.querySelector("input, select");
        if (first) first.focus();
      });
      item.appendChild(button);
      container.appendChild(item);
    });
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
