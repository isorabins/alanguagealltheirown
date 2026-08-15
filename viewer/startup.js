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

  function projectRuntime(when, now, turn, runtimeState) {
    runtimeState=runtimeState&&typeof runtimeState==="object"?runtimeState:{};
    if(runtimeState.status==="paused"){
      return {mode:"paused",visible:true,heading:"Experiment paused.",detail:runtimeState.message||"Experiment paused.",stamp:"paused at turn "+(runtimeState.turn||turn),kicker:"paused public record",turnClock:"Paused",examClock:"Paused",examLink:"see last test ↓"};
    }
    var timestamp=typeof when==="number"?when:Date.parse(when||"");
    if(!Number.isFinite(timestamp)){
      return {mode:"unavailable",visible:true,heading:"Live update status is unavailable.",detail:"The public record is preserved at turn "+turn+", but the timestamp of its latest canonical update could not be verified.",stamp:"live update status unavailable",kicker:"update status unavailable",turnClock:"unavailable",examClock:"unavailable",examLink:"see last test ↓"};
    }
    var age=now-timestamp;
    var formatted=new Date(timestamp).toISOString().replace("T"," ").slice(0,16)+" UTC";
    if(age>45*60*1000){
      return {mode:"stalled",visible:true,heading:"The scheduled loop is not advancing.",detail:"The public record is preserved at turn "+turn+". New legislation is not being published, and no language rule changes during this hold. Last update: "+formatted+".",stamp:"the loop has been still since "+formatted,kicker:"stalled public record",turnClock:"stalled",examClock:"stalled",examLink:"see last test ↓"};
    }
    var remaining=timestamp+TURN_MS-now;
    var nextTurn=Number(turn||0)+1;
    var examTurn=Number(runtimeState.next_exam_turn||nextTurn);
    var examRemaining=remaining+Math.max(0,examTurn-nextTurn)*TURN_MS;
    var turnRunning=remaining<=0,examRunning=examRemaining<=0;
    var mins=Math.max(0,Math.round(age/60000));
    return {mode:"active",visible:false,heading:"",detail:"The scheduled experiment is advancing from the latest canonical turn.",stamp:"last turn "+mins+" min ago · live",kicker:"active public record",turnClock:turnRunning?"running now":formatRemaining(remaining),examClock:examRunning?"running now":formatRemaining(examRemaining),examLink:(examRunning?"watch live test now":"watch next test")+" ↓",turnRunning:turnRunning,examRunning:examRunning};
  }

  function applyRuntimeProjection(projection) {
    var examElement=document.getElementById("t-exam"),turnElement=document.getElementById("t-turn"),examLink=document.getElementById("exam-jump");
    if(turnElement){turnElement.textContent=projection.turnClock;turnElement.classList[projection.turnRunning?"add":"remove"]("running");}
    if(examElement){examElement.textContent=projection.examClock;examElement.classList[projection.examRunning?"add":"remove"]("running");}
    if(examLink)examLink.textContent=projection.examLink;
    var status=document.getElementById("runtime-status"),heading=document.getElementById("runtime-status-heading"),detail=document.getElementById("runtime-status-detail");
    if(heading)heading.textContent=projection.heading;
    if(detail)detail.textContent=projection.detail;
    if(status)status.classList[projection.visible?"add":"remove"]("visible");
    var kicker=document.getElementById("experiment-status-kicker"),statusDetail=document.getElementById("experiment-status-detail"),statusTurn=document.getElementById("status-next-turn"),statusExam=document.getElementById("status-next-exam");
    if(kicker)kicker.textContent=projection.kicker;
    if(statusDetail)statusDetail.textContent=projection.detail;
    if(statusTurn)statusTurn.textContent=projection.turnClock;
    if(statusExam)statusExam.textContent=projection.examClock;
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
    renderAgentC(runtime.agent_c);
    var projection=projectRuntime(lastTurnAt,Date.now(),lastTurnNum,runtime);
    applyRuntimeProjection(projection);
    if(projection.mode==="active"&&projection.turnRunning){
      if(!refetchArmed&&typeof window.loadState==="function"){
        refetchArmed = true;
        window.setTimeout(window.loadState, refetchDelay);
        refetchDelay = Math.min(refetchDelay * 2, 300000);
      }
    }
    return projection;
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
    return updateCounters();
  }

  renderMetrics(bootstrap.metrics);
  updateCounters();
  window.setInterval(updateCounters, 1000);
  window.ALATO_STARTUP = {setSnapshot: setSnapshot, updateCounters: updateCounters, projectRuntime: projectRuntime, renderMetrics: renderMetrics, agentCLabel: agentCLabel, renderAgentC: renderAgentC};
})(window, document);
