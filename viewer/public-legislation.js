(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.ALATO_PUBLIC_LEGISLATION = api;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";

  function identity(value) {
    var candidate = value && value.legislation_identity;
    if (!candidate || typeof candidate.version !== "string" ||
        typeof candidate.hash !== "string" || candidate.hash.length !== 64) return null;
    return {version:candidate.version,hash:candidate.hash};
  }

  function same(left, right) {
    return !!left && !!right && left.version === right.version && left.hash === right.hash;
  }

  function assemble(input) {
    input = input || {};
    var publicModel = input.publicModel || input.fallbackModel || null;
    var currentIdentity = identity(publicModel);
    if (!publicModel || !currentIdentity) return {status:"stale_unavailable",state:null};
    if (input.expectedIdentity && !same(currentIdentity, input.expectedIdentity)) {
      return {status:"stale_unavailable",state:null};
    }
    var runtime = publicModel.runtime_status || null;
    if (runtime && runtime.legislation_identity &&
        !same(currentIdentity, runtime.legislation_identity)) {
      return {status:"stale_unavailable",state:null};
    }
    var rules = Array.isArray(publicModel.complete_legislature) ?
      publicModel.complete_legislature : [];
    var adopted = publicModel.adopted_language || {rules:[],text:""};
    return {
      status:"current",
      state:{
        conversation:input.conversation || [],
        rulebook:{
          version:currentIdentity.version,
          hash:publicModel.complete_legislature_identity,
          rules:rules
        },
        collaboration:input.collaboration || {},
        conversations:input.conversations || [],
        x:input.x || {},
        language:{
          version:currentIdentity.version,
          hash:currentIdentity.hash,
          rules:adopted.rules || [],
          text:adopted.text || ""
        },
        notes:input.notes || [],
        legislation:{
          identity:currentIdentity,
          roles:publicModel.roles || {},
          classifications:publicModel.classifications || {},
          budget:publicModel.budget || {},
          workflow_evidence:publicModel.workflow_evidence || []
        },
        meta:{runtime:runtime,legislation_status:"current"}
      }
    };
  }

  return {assemble:assemble,identity:identity,sameIdentity:same};
});
