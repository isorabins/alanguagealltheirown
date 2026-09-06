/* One public read seam: coherent revisions, ordered refreshes and safe fallback.
 * Production and Node tests call createReader with a fetch adapter. Rendering
 * never joins canonical files or decides which revision won a race. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ALATO_PUBLIC_STATE = api;
})(typeof window === 'undefined' ? globalThis : window, function () {
  'use strict';
  const REPO = 'https://raw.githubusercontent.com/isorabins/alanguagealltheirown/';
  const COMMITS = 'https://api.github.com/repos/isorabins/alanguagealltheirown/commits?sha=main&per_page=1';

  function parseArchive(text) {
    const match = /^window\.STATE = ([\s\S]*);\s*$/.exec(text);
    if (!match) throw new Error('invalid public archive');
    return JSON.parse(match[1]);
  }

  function validSnapshot(state) {
    if (!state || !Array.isArray(state.conversation) || !state.rulebook || !Array.isArray(state.rulebook.rules)) return false;
    const runtime = state.meta && state.meta.runtime;
    const turn = state.conversation.length ? state.conversation[state.conversation.length - 1].turn : 0;
    return !runtime || (Number.isInteger(runtime.turn) && runtime.turn === turn);
  }

  /**
   * @param {{fetch: Function, onSnapshot: Function, onProgress?: Function,
   * onRuntime?: Function, initial?: Object, local?: boolean}} options
   * @returns {{refresh: function(): Promise<void>, refreshProgress: function(): Promise<void>}}
   * A successful read is pinned to one repository commit. Failed refreshes keep
   * the last good view. Older completions never replace a newer refresh. Progress
   * is read only from the displayed revision, never independently from main.
   */
  function createReader(options) {
    let sequence = 0, current = null, revision = null, completeRevision = null, complete = false;
    let acceptedSequence = 0, progressSequence = 0, currentSource = null;
    const turnOf = state => state && state.conversation && state.conversation.length ? state.conversation[state.conversation.length - 1].turn : 0;
    const fetch = options.fetch;
    const progress = options.onProgress || function () {};
    const runtime = options.onRuntime || function () {};
    const local = !!options.local;
    function publish(state, token, source, commit, isComplete = false) {
      if (token !== sequence || token < acceptedSequence || !validSnapshot(state)) return false;
      if (currentSource === 'canonical-unpinned' && turnOf(state) < turnOf(current)) return false;
      acceptedSequence = token;
      currentSource = source;
      if (commit && Array.isArray(commit.notes)) state = Object.assign({}, state, {notes: commit.notes});
      current = state;
      revision = commit || null;
      complete = isComplete;
      completeRevision = isComplete && commit ? commit.sha : null;
      options.onSnapshot(state, {source, revision: commit && commit.sha, complete});
      const stateRuntime = state.meta && state.meta.runtime;
      const displayedTurn = state.conversation.length ? state.conversation[state.conversation.length - 1].turn : 0;
      const completionTime = source === 'canonical-unpinned' && stateRuntime && state.meta && Number.isFinite(Date.parse(state.meta.updated || '')) ? state.meta.updated : null;
      runtime(source === 'canonical' && stateRuntime ? commit.date : completionTime,
              displayedTurn, stateRuntime || {});
      return true;
    }
    async function get(url, asText) {
      const response = await fetch(url, {cache: 'no-store'});
      if (!response.ok) throw new Error('public state unavailable: ' + response.status);
      return asText ? response.text() : response.json();
    }
    async function fallback(token) {
      // Preview is a first paint, never a substitute for the complete archive.
      try {
        const preview = await get('preview.json');
        if (!current) publish(preview, token, 'deployed', null);
      } catch (_) {}
      try {
        const full = parseArchive(await get('state.js', true));
        if (!complete || local) publish(full, token, 'deployed', null, true);
      } catch (_) {}
    }
    function snapshotSignal(state) {
      return JSON.stringify({turn: turnOf(state), updated: state.meta && state.meta.updated,
        runtime: state.meta && state.meta.runtime, language: state.language,
        notes: Array.isArray(state.notes) ? state.notes.slice(-1) : []});
    }
    async function unpinnedFallback(token) {
      // One whole archive remains coherent without the rate-limited revision API.
      // The preview is only a small change detector; never join its data to history.
      const preview = await get(REPO + 'main/viewer/preview.json');
      if (!validSnapshot(preview)) throw new Error('invalid fallback preview');
      if (complete && (turnOf(preview) < turnOf(current) || snapshotSignal(preview) === snapshotSignal(current))) return;
      const full = parseArchive(await get(REPO + 'main/viewer/state.js', true));
      if (!validSnapshot(full) || turnOf(full) < Math.max(turnOf(preview), turnOf(current))) {
        throw new Error('older fallback archive');
      }
      if (turnOf(full) === turnOf(preview) && snapshotSignal(full) !== snapshotSignal(preview)) {
        throw new Error('fallback archive does not yet match preview');
      }
      publish(full, token, 'canonical-unpinned', null, true);
    }
    async function refreshProgress() {
      const requested = ++progressSequence;
      const pinned = revision;
      if (!pinned && !local) { progress(null, 'unavailable'); return; }
      const path = local ? '../state/public-exam-progress.json' : REPO + pinned.sha + '/state/public-exam-progress.json';
      try {
        const response = await fetch(path, {cache: 'no-store'});
        let status = response.status === 404 ? 'missing' : response.ok ? 'ok' : 'unavailable';
        let snapshot = null;
        if (status === 'ok') {
          try { snapshot = await response.json(); } catch (_) { status = 'malformed'; }
        }
        if (requested === progressSequence && pinned === revision) progress(snapshot, status);
      } catch (_) {
        if (requested === progressSequence && pinned === revision) progress(null, 'unavailable');
      }
    }
    async function refresh() {
      const token = ++sequence;
      if (!current && options.initial) publish(options.initial, token, 'deployed', null);
      if (local) {
        await fallback(token);
        await refreshProgress();
        return;
      }
      let headResolved = false;
      try {
        const commits = await get(COMMITS);
        const head = Array.isArray(commits) && commits[0];
        if (!head || !/^[a-f0-9]{40}$/.test(head.sha)) throw new Error('invalid revision');
        headResolved = true;
        if (completeRevision === head.sha) { await refreshProgress(); return; }
        // A notes/code-only commit must not make an old turn look fresh.
        const history = await get(COMMITS.replace('sha=main', 'sha=' + head.sha) + '&path=state%2Fconversation.json');
        const turnCommit = Array.isArray(history) && history[0];
        const commit = {sha: head.sha, date: turnCommit && turnCommit.commit && turnCommit.commit.committer && turnCommit.commit.committer.date};
        try { commit.notes = await get(REPO + head.sha + '/notes.json'); } catch (_) {}
        const prefix = REPO + commit.sha + '/';
        // Compatibility with existing historical commits that have no preview.
        if (!complete) {
          try { publish(await get(prefix + 'viewer/preview.json'), token, 'canonical', commit); } catch (_) {}
        }
        const full = parseArchive(await get(prefix + 'viewer/state.js', true));
        if (!validSnapshot(full)) throw new Error('invalid public snapshot');
        if (publish(full, token, 'canonical', commit, true)) {
          completeRevision = commit.sha;
          await refreshProgress();
        }
      } catch (_) {
        if (!headResolved) {
          try { await unpinnedFallback(token); } catch (_) {}
        }
        if (!complete) await fallback(token);
        if (token === sequence) await refreshProgress();
        if (!current && token === sequence) runtime(null);
      }
    }
    return {refresh, refreshProgress};
  }
  return {createReader, validSnapshot};
});
