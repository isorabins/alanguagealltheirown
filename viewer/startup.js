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
    var explanations = {
      "rulebook revisions":"The numbered version of the adopted language. It advances when the official rulebook changes; it is not the number of rules currently in force.",
      "turns":"Numbered steps in the public experiment, including legislation and tests. A turn is a place in the record, not necessarily a new rule.",
      "rules adopted":"The rules currently in force and given to an encoder or decoder. Rejected, repealed, and historical rules are excluded.",
      "best strict savings · V2":"The largest message-body reduction from a valid exam where every meaning survived and the encoded body was smaller. Rulebook overhead is excluded.",
      "latest coverage · V2":"The share of explicit facts that survived the latest valid encode-and-decode exam. Strict passing requires 100%.",
      "latest Conversation":"A six-message coordination test using the captured adopted language. The judge checks each explicit scenario requirement."
    };
    element.innerHTML = metrics.map(function (metric) {
      var label=escapeHtml(metric[0]),tip=escapeHtml(explanations[metric[0]] || "Public experiment metric.");
      return '<span class="metric">' + label + '<button class="help" type="button" aria-label="Explain '+label+'" aria-expanded="false">?</button><span class="tip" role="tooltip">'+tip+'</span><b>'+escapeHtml(metric[1])+'</b></span>';
    }).join("");
    Array.prototype.forEach.call(element.querySelectorAll ? element.querySelectorAll(".help") : [], function(button){
      button.addEventListener("click",function(){button.setAttribute("aria-expanded",button.getAttribute("aria-expanded") === "true" ? "false" : "true");});
    });
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
  window.ALATO_STARTUP = {setSnapshot: setSnapshot, updateCounters: updateCounters, renderMetrics: renderMetrics};
})(window, document);
