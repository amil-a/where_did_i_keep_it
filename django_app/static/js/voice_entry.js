/*
 * voice_entry.js - voice-first "Add item" flow.
 * Speak -> live transcript -> Django (/api/extract-item/) -> form is filled in.
 * No audio is recorded or uploaded; only the transcript text is sent.
 */
(function () {
  "use strict";

  var panel = document.getElementById("voice-panel");
  if (!panel) return;

  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  var $ = function (id) { return document.getElementById(id); };

  var mic = $("vo-mic"), stopBtn = $("vo-stop"), processBtn = $("vo-process"),
      manualBtn = $("vo-manual"), transcript = $("vo-transcript"), status = $("vo-status"),
      errBox = $("vo-error"), spinner = $("vo-spinner"), wrap = $("item-form-wrap"),
      note = $("vo-review-note");

  var lang = panel.getAttribute("data-lang") || "en-US";   // e.g. "ml-IN" for Malayalam later
  var url = panel.getAttribute("data-extract-url");
  var FIELDS = { name: "id_name", description: "id_description", category: "id_category", location: "id_location" };

  var MSG = {
    idle: "Tap the microphone and start talking.",
    listening: "Listening\u2026 tap Stop when you're done.",
    heard: "Check the words below, fix anything, then press \u201cFill the form\u201d.",
    unsupported: "Voice input isn't supported in this browser (try Chrome or Edge). You can type your sentence below, or enter details manually.",
    insecure: "Voice input needs HTTPS or localhost.",
    empty: "Nothing to process yet. Speak or type a sentence first.",
    emptySpeech: "We didn't catch anything. Tap the microphone and try again.",
    network: "Couldn't reach the server. Check your connection and try again, or enter details manually.",
    nothingFound: "We couldn't pick out any item details. Please fill in the form yourself.",
    errors: {
      "not-allowed": "Microphone access is blocked. Allow it in your browser's site settings, or type your sentence instead.",
      "service-not-allowed": "Microphone access is blocked. Allow it in your browser's site settings, or type your sentence instead.",
      "no-speech": "No speech detected. Tap the microphone and try again.",
      "audio-capture": "No microphone found. Check that one is connected.",
      "network": "The speech service couldn't be reached. Check your internet connection.",
      "language-not-supported": "This language isn't supported for voice input in your browser.",
      "default": "Voice input failed. You can type your sentence instead."
    }
  };

  var recognition = null, base = "", spoken = "", gotError = false, discard = false, settingValue = false;

  function joinText(b, s) {
    s = s.trim();
    if (!s) return b;
    if (!b) return s;
    return /\s$/.test(b) ? b + s : b + " " + s;
  }
  function say(t) { status.textContent = t; }
  function showError(t) { errBox.textContent = t; errBox.classList.remove("d-none"); }
  function hideError() { errBox.classList.add("d-none"); errBox.textContent = ""; }
  function setListening(on) {
    mic.classList.toggle("is-listening", on);
    mic.setAttribute("aria-pressed", on ? "true" : "false");
    mic.setAttribute("aria-label", on ? "Listening" : "Start speaking");
    stopBtn.disabled = !on;
  }
  function setBusy(on) {
    spinner.classList.toggle("d-none", !on);
    processBtn.disabled = on;
    mic.disabled = on;
  }
  function csrf() {
    var el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }
  function abortRecognition() {
    if (recognition) { discard = true; recognition.abort(); }
  }

  setListening(false);
  say(SpeechRecognition ? MSG.idle : MSG.unsupported);

  /* ---------- speech recognition ---------- */
  function start() {
    if (!SpeechRecognition) { showError(MSG.unsupported); return; }
    if (!window.isSecureContext) { showError(MSG.insecure); return; }
    hideError();

    var rec = new SpeechRecognition();
    rec.lang = lang;
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    base = transcript.value;
    spoken = "";
    gotError = false;
    discard = false;

    rec.onstart = function () { setListening(true); say(MSG.listening); };
    rec.onresult = function (event) {
      // Rebuild from all results of this session: interim text is replaced, never duplicated.
      var text = "";
      for (var i = 0; i < event.results.length; i++) text += event.results[i][0].transcript;
      spoken = text;
      settingValue = true;
      transcript.value = joinText(base, spoken);
      settingValue = false;
    };
    rec.onerror = function (event) {
      if (event.error === "aborted") return;
      gotError = true;
      showError(MSG.errors[event.error] || MSG.errors["default"]);
    };
    rec.onend = function () {
      setListening(false);
      recognition = null;
      if (discard) return;
      if (spoken.trim()) {
        settingValue = true;
        transcript.value = joinText(base, spoken);
        settingValue = false;
        say(MSG.heard);
      } else if (!gotError) {
        say(MSG.emptySpeech);
      } else {
        say(MSG.idle);
      }
    };

    recognition = rec;
    try { rec.start(); } catch (e) { recognition = null; setListening(false); showError(MSG.errors["default"]); }
  }

  mic.addEventListener("click", function () {
    if (recognition) recognition.stop(); else start();
  });
  stopBtn.addEventListener("click", function () { if (recognition) recognition.stop(); });

  // Typing while listening: keep the typing, stop listening.
  transcript.addEventListener("input", function () {
    if (settingValue || !recognition) return;
    abortRecognition();
    setListening(false);
    say(MSG.heard);
  });

  /* ---------- form helpers ---------- */
  function categoryOptions() {
    var list = document.getElementById("category-options");
    return list ? Array.prototype.slice.call(list.querySelectorAll("option")).map(function (o) { return o.value; }) : [];
  }
  function matchCategory(val) {
    if (!val) return { value: "", matched: false };
    var opts = categoryOptions();
    for (var i = 0; i < opts.length; i++) {
      if (opts[i].toLowerCase() === val.toLowerCase()) return { value: opts[i], matched: true };
    }
    return { value: val, matched: opts.length === 0 };  // unknown category => ask the user to check
  }
  function revealForm() { wrap.classList.remove("d-none"); }

  function fill(data) {
    var any = false, firstReview = null;
    Object.keys(FIELDS).forEach(function (key) {
      var el = $(FIELDS[key]);
      if (!el) return;
      var val = typeof data[key] === "string" ? data[key].trim() : "";
      var needsReview = false;
      if (key === "category" && val) {
        var m = matchCategory(val);
        val = m.value;
        needsReview = !m.matched;
      }
      if (val) { el.value = val; any = true; }
      if (!el.value.trim() || needsReview) {
        el.classList.add("needs-review");
        if (!firstReview) firstReview = el;
      } else {
        el.classList.remove("needs-review");
      }
    });

    revealForm();
    if (!any) { showError(MSG.nothingFound); }
    else { note.classList.remove("d-none"); }
    wrap.scrollIntoView({ behavior: "smooth", block: "start" });
    var focusEl = firstReview || $(FIELDS.name);
    if (focusEl) setTimeout(function () { focusEl.focus({ preventScroll: true }); }, 300);
  }

  function fail(message) { var e = new Error(message); e.friendly = true; return e; }

  /* ---------- send transcript to Django ---------- */
  processBtn.addEventListener("click", function () {
    hideError();
    var text = transcript.value.trim();
    if (!text) { showError(MSG.empty); return; }
    abortRecognition();
    setListening(false);
    setBusy(true);
    say("Working out the details\u2026");

    fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "Accept": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify({ transcript: text })
    })
      .then(function (r) {
        return r.json().catch(function () { return null; }).then(function (d) { return { ok: r.ok, data: d }; });
      })
      .then(function (res) {
        if (!res.ok) throw fail((res.data && res.data.error) || MSG.network);
        if (!res.data || typeof res.data !== "object") throw fail("We got an unexpected answer. Please fill in the form yourself.");
        fill(res.data);
        say(MSG.heard);
      })
      .catch(function (e) { showError(e && e.friendly ? e.message : MSG.network); say(MSG.idle); })
      .then(function () { setBusy(false); });
  });

  /* ---------- manual entry (always available) ---------- */
  manualBtn.addEventListener("click", function () {
    revealForm();
    var nameEl = $(FIELDS.name);
    wrap.scrollIntoView({ behavior: "smooth", block: "start" });
    if (nameEl) setTimeout(function () { nameEl.focus({ preventScroll: true }); }, 300);
  });

  wrap.addEventListener("input", function (e) { e.target.classList.remove("needs-review"); });
  wrap.addEventListener("change", function (e) { e.target.classList.remove("needs-review"); });
  if (wrap.closest("form")) wrap.closest("form").addEventListener("submit", abortRecognition);
  window.addEventListener("pagehide", abortRecognition);
})();