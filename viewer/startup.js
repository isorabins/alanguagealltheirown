(function (window, document) {
  "use strict";

  var TURN_MS = 15 * 60 * 1000;
  var bootstrap = window.PUBLIC_BOOTSTRAP || {};
  var runtime = bootstrap.runtime || {};
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
    var examElement = document.getElementById("t-exam");
    var conversationElement = document.getElementById("t-conversation");
    if (!examElement || !conversationElement) return;
    if (runtime.status === "paused") {
      examElement.textContent = "Paused";
      conversationElement.textContent = "Paused";
      examElement.classList.remove("running");
      conversationElement.classList.remove("running");
      var status = document.getElementById("runtime-status");
      var detail = document.getElementById("runtime-status-detail");
      if (status) status.classList.add("visible");
      if (detail) detail.textContent = runtime.message || "Experiment paused.";
      return;
    }
    if (lastTurnAt === null) {
      examElement.textContent = "unavailable";
      conversationElement.textContent = "unavailable";
      return;
    }
    var remaining = lastTurnAt + TURN_MS - Date.now();
    var nextTurn = lastTurnNum + 1;
    var examTurn = Number(runtime.next_exam_turn || nextTurn);
    var conversationTurn = Number(runtime.next_conversation_turn || examTurn);
    var examRemaining = remaining + Math.max(0, examTurn - nextTurn) * TURN_MS;
    var conversationRemaining = remaining + Math.max(0, conversationTurn - nextTurn) * TURN_MS;
    if (examRemaining <= 0) {
      examElement.textContent = "running now";
      examElement.classList.add("running");
      if (!refetchArmed && typeof window.loadState === "function") {
        refetchArmed = true;
        window.setTimeout(window.loadState, refetchDelay);
        refetchDelay = Math.min(refetchDelay * 2, 300000);
      }
    } else {
      examElement.textContent = formatRemaining(examRemaining);
      examElement.classList.remove("running");
    }
    if (conversationRemaining <= 0) {
      conversationElement.textContent = "running now";
      conversationElement.classList.add("running");
    } else {
      conversationElement.textContent = formatRemaining(conversationRemaining);
      conversationElement.classList.remove("running");
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
    if (arguments.length > 2 && arguments[2]) runtime = arguments[2];
    refetchArmed = false;
    updateCounters();
  }

  renderMetrics(bootstrap.metrics);
  updateCounters();
  window.setInterval(updateCounters, 1000);
  window.ALATO_STARTUP = {setSnapshot: setSnapshot, updateCounters: updateCounters};
})(window, document);
