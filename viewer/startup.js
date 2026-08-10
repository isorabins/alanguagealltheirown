(function (window, document) {
  "use strict";

  var TURN_MS = 15 * 60 * 1000;
  var bootstrap = window.PUBLIC_BOOTSTRAP || {};
  var lastTurnAt = Date.parse(bootstrap.updated || "");
  var lastTurnNum = Number(bootstrap.turn || 0);
  var refetchArmed = false;
  var refetchDelay = 45000;

  if (!Number.isFinite(lastTurnAt)) lastTurnAt = null;

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"]/g, function (character) {
      return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[character];
    });
  }

  function renderMetrics(metrics) {
    var element = document.getElementById("metrics");
    if (!element || !Array.isArray(metrics)) return;
    element.innerHTML = metrics.map(function (metric) {
      return "<span>" + escapeHtml(metric[0]) + "<b>" + escapeHtml(metric[1]) + "</b></span>";
    }).join("");
  }

  function formatRemaining(milliseconds) {
    var seconds = Math.max(0, Math.ceil(milliseconds / 1000));
    var minutes = Math.floor(seconds / 60);
    seconds %= 60;
    return (minutes < 10 ? "0" : "") + minutes + ":" +
      (seconds < 10 ? "0" : "") + seconds;
  }

  function updateCounters() {
    var turnElement = document.getElementById("t-turn");
    var examElement = document.getElementById("t-test");
    if (!turnElement || !examElement) return;
    if (lastTurnAt === null) {
      turnElement.textContent = "unavailable";
      examElement.textContent = "unavailable";
      return;
    }
    var remaining = lastTurnAt + TURN_MS - Date.now();
    var nextTurn = lastTurnNum + 1;
    var turnsUntilExam = (3 - (nextTurn % 3)) % 3;
    var examRemaining = remaining + turnsUntilExam * TURN_MS;
    if (remaining <= 0) {
      turnElement.textContent = remaining > -5 * 60 * 1000 ? "running now" : "delayed";
      turnElement.classList.add("running");
      if (!refetchArmed && typeof window.loadState === "function") {
        refetchArmed = true;
        window.setTimeout(window.loadState, refetchDelay);
        refetchDelay = Math.min(refetchDelay * 2, 300000);
      }
    } else {
      turnElement.textContent = formatRemaining(remaining);
      turnElement.classList.remove("running");
    }
    if (examRemaining <= 0) {
      examElement.textContent = "running now";
      examElement.classList.add("running");
    } else {
      examElement.textContent = formatRemaining(examRemaining);
      examElement.classList.remove("running");
    }
  }

  function setSnapshot(when, turn) {
    var nextTimestamp = Date.parse(when || "");
    if (Number.isFinite(nextTimestamp)) {
      if (lastTurnAt !== null && nextTimestamp > lastTurnAt) refetchDelay = 45000;
      lastTurnAt = nextTimestamp;
    } else {
      lastTurnAt = null;
    }
    lastTurnNum = Number(turn || 0);
    refetchArmed = false;
    updateCounters();
  }

  renderMetrics(bootstrap.metrics);
  updateCounters();
  window.setInterval(updateCounters, 1000);
  window.ALATO_STARTUP = {setSnapshot: setSnapshot, updateCounters: updateCounters};
})(window, document);
