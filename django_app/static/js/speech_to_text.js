/*
 * speech_to_text.js - reusable voice-to-text for textareas (browser Web Speech API).
 *
 * No audio is recorded, stored, or uploaded by this code. Only the recognised
 * text is written into the textarea; Django saves it through the normal form.
 *
 * Usage: any <button class="stt-btn" data-stt-target="TEXTAREA_ID"> is wired up
 * automatically. Optional: data-stt-lang="ml-IN" (default "en-US").
 */
(function () {
  "use strict";

  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  var MSG = {
    unsupported: "Voice input isn't supported in this browser (try Chrome or Edge). You can still type.",
    insecure: "Voice input needs HTTPS or localhost.",
    listening: "Listening\u2026 speak now. Click the mic again to stop.",
    done: "Done. You can edit the text before saving.",
    empty: "Didn't catch anything. Click the mic and try again.",
    errors: {
      "not-allowed": "Microphone access is blocked. Allow it in your browser's site settings, then try again.",
      "service-not-allowed": "Microphone access is blocked. Allow it in your browser's site settings, then try again.",
      "no-speech": "No speech detected. Click the mic and try again.",
      "audio-capture": "No microphone found. Check that one is connected.",
      "network": "The speech service couldn't be reached. Check your internet connection.",
      "language-not-supported": "This language isn't supported for voice input in your browser.",
      "default": "Voice input failed. You can still type."
    }
  };

  function joinText(base, spoken) {
    spoken = spoken.trim();
    if (!spoken) return base;
    if (!base) return spoken;
    return /\s$/.test(base) ? base + spoken : base + " " + spoken;
  }

  function init(button) {
    var textarea = document.getElementById(button.getAttribute("data-stt-target"));
    if (!textarea) {
      console.warn("speech_to_text: no textarea with id", button.getAttribute("data-stt-target"));
      return;
    }
    var lang = button.getAttribute("data-stt-lang") || "en-US";

    var wrap = button.closest(".stt-field") || button.parentNode;
    var status = wrap.querySelector(".stt-status");
    if (!status) {
      status = document.createElement("div");
      status.className = "stt-status";
      wrap.appendChild(status);
    }
    status.setAttribute("aria-live", "polite");

    var recognition = null;
    var base = "";
    var spoken = "";      // final + interim text of the current session
    var gotError = false;
    var discard = false;  // true => don't write text back when the session ends
    var settingValue = false;

    function say(text, isError) {
      status.textContent = text || "";
      status.classList.toggle("is-error", !!isError);
    }

    function setListening(on) {
      button.classList.toggle("is-listening", on);
      button.setAttribute("aria-pressed", on ? "true" : "false");
      button.setAttribute("aria-label", on ? "Stop voice input" : "Start voice input");
      button.title = on ? "Stop voice input" : "Start voice input";
    }

    function writeValue(value) {
      settingValue = true;
      textarea.value = value;
      settingValue = false;
    }

    function fireInput() {
      settingValue = true;
      textarea.dispatchEvent(new Event("input", { bubbles: true }));
      settingValue = false;
    }

    setListening(false);

    if (!SpeechRecognition) {
      button.classList.add("is-unsupported");
      button.title = MSG.unsupported;
      button.addEventListener("click", function () { say(MSG.unsupported, true); });
      return;
    }

    function start() {
      if (!window.isSecureContext) { say(MSG.insecure, true); return; }

      var rec = new SpeechRecognition();
      rec.lang = lang;
      rec.continuous = true;
      rec.interimResults = true;
      rec.maxAlternatives = 1;

      base = textarea.value;
      spoken = "";
      gotError = false;
      discard = false;

      rec.onstart = function () { setListening(true); say(MSG.listening, false); };

      rec.onresult = function (event) {
        // Rebuild from ALL results of this session each time, so interim
        // results are replaced (never appended) and nothing is duplicated.
        var text = "";
        for (var i = 0; i < event.results.length; i++) {
          text += event.results[i][0].transcript;
        }
        spoken = text;
        writeValue(joinText(base, spoken));
      };

      rec.onerror = function (event) {
        if (event.error === "aborted") return;
        gotError = true;
        say(MSG.errors[event.error] || MSG.errors["default"], true);
      };

      rec.onend = function () {
        setListening(false);
        recognition = null;
        if (discard) return;
        if (spoken.trim()) {
          writeValue(joinText(base, spoken));
          fireInput();
          say(MSG.done, false);
        } else if (!gotError) {
          say(MSG.empty, true);
        }
      };

      recognition = rec;
      try {
        rec.start();
      } catch (e) {
        recognition = null;
        setListening(false);
        say(MSG.errors["default"], true);
      }
    }

    button.addEventListener("click", function () {
      if (recognition) recognition.stop(); else start();
    });

    // If the user types while listening, keep their typing and stop listening.
    textarea.addEventListener("input", function () {
      if (settingValue || !recognition) return;
      discard = true;
      recognition.abort();
      say("", false);
    });

    // Never let recognition interfere with submitting the form.
    var form = textarea.form;
    if (form) {
      form.addEventListener("submit", function () {
        if (recognition) { discard = true; recognition.abort(); }
      });
    }
    window.addEventListener("pagehide", function () {
      if (recognition) { discard = true; recognition.abort(); }
    });
  }

  function initAll() {
    var buttons = document.querySelectorAll(".stt-btn[data-stt-target]");
    for (var i = 0; i < buttons.length; i++) init(buttons[i]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();