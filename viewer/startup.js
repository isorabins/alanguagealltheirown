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
      "rules adopted":"The rules currently in force and given to an encoder or decoder. Rejected, repealed, and historical rules are not part of the current language.",
      "best strict savings · V2":"The largest reduction in message-body tokens among valid exams where 100% of the required meaning survived and the encoded message was actually smaller. Rulebook overhead is not included.",
      "latest coverage · V2":"The share of explicit facts that survived the latest encode-and-decode exam. Strict passing requires 100%; this result also grew from 469 to 471 tokens.",
      "latest Conversation":"A six-message coordination test using the captured current language. In this scenario the judge checked four specific required facts, and all four survived."
    };
    element.innerHTML = metrics.map(function (metric) {
      var label=escapeHtml(metric[0]),tip=escapeHtml(explanations[metric[0]] || "Public experiment metric.");
      return '<span class="metric info-hover" tabindex="0" data-tip="'+tip+'" aria-label="'+label+'. '+tip+'">' + label + '<b>'+escapeHtml(metric[1])+'</b></span>';
    }).join("");
  }

  function formatRemaining(milliseconds) {
    var seconds = Math.max(0, Math.ceil(milliseconds / 1000));
    var minutes = Math.floor(seconds / 60);
    seconds %= 60;
    return (minutes < 10 ? "0" : "") + minutes + ":" +
      (seconds < 10 ? "0" : "") + seconds;
  }

  function agentCLabel(agentC) {
    agentC=agentC&&typeof agentC==="object"?agentC:{};
    if(agentC.state==="growing"){
      var growth=Number(agentC.growth_pct),trigger=Number(agentC.trigger_pct);
      return "Agent C · "+(Number.isFinite(growth)?growth.toFixed(1):"0.0")+"% / "+(Number.isFinite(trigger)?trigger:10)+"%";
    }
    if(agentC.state==="blocked_motion")return "Agent C · ready, waiting on "+String(agentC.blocker||"open motion");
    if(agentC.state==="quarantined")return "Agent C · quarantined";
    if(agentC.state==="blocked_attempt")return "Agent C · retry waits for language change";
    if(agentC.state==="eligible")return "Agent C · cleanup ready";
    return "Agent C · status unavailable";
  }

  function renderAgentC(agentC) {
    var label=document.getElementById("agent-c-summary-label");
    var bar=document.getElementById("agent-c-summary-progress");
    if(label)label.textContent=agentCLabel(agentC);
    if(bar){
      var progress=Number(agentC&&agentC.progress_pct);
      if(!Number.isFinite(progress))progress=0;
      bar.style.width=Math.max(0,Math.min(100,progress))+"%";
    }
  }

  function updateCounters() {
    var examElement = document.getElementById("t-exam");
    var turnElement = document.getElementById("t-turn");
    var examLink = document.getElementById("exam-jump");
    renderAgentC(runtime.agent_c);
    if (!examElement || !turnElement) return;
    if (runtime.status === "paused") {
      examElement.textContent = "Paused";
      turnElement.textContent = "Paused";
      examElement.classList.remove("running");
      turnElement.classList.remove("running");
      var status = document.getElementById("runtime-status");
      var detail = document.getElementById("runtime-status-detail");
      if (status) status.classList.add("visible");
      if (detail) detail.textContent = runtime.message || "Experiment paused.";
      if (examLink) examLink.textContent = "see last test ↓";
      return;
    }
    if (lastTurnAt === null) {
      examElement.textContent = "unavailable";
      turnElement.textContent = "unavailable";
      if (examLink) examLink.textContent = "open test terminal ↓";
      return;
    }
    var remaining = lastTurnAt + TURN_MS - Date.now();
    var nextTurn = lastTurnNum + 1;
    var examTurn = Number(runtime.next_exam_turn || nextTurn);
    var examRemaining = remaining + Math.max(0, examTurn - nextTurn) * TURN_MS;
    if (remaining <= 0) {
      turnElement.textContent = "running now";
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
      if (examLink) examLink.textContent = "watch live test now ↓";
    } else {
      examElement.textContent = formatRemaining(examRemaining);
      examElement.classList.remove("running");
      if (examLink) examLink.textContent = "watch next test ↓";
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
  window.ALATO_STARTUP = {setSnapshot: setSnapshot, updateCounters: updateCounters, renderMetrics: renderMetrics, agentCLabel: agentCLabel, renderAgentC: renderAgentC};
})(window, document);
