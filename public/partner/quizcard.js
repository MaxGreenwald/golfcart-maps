/* Partner admin: rules quiz. The shop turns it on; renters then answer a few questions on the
   local cart rules (built from the same road rule the map uses) before the map unlocks. Each
   pass is recorded with its code and time. Uses admin.js globals: api, esc, $, flash, refreshShop. */
(function () {
  let info = { on: false, questions: [], passes: [] };
  function when(t) {
    try { return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit', weekday: 'short', month: 'short', day: 'numeric', timeZoneName: 'short' }).format(new Date(t * 1000)); }
    catch (e) { return new Date(t * 1000).toLocaleString(); }
  }
  function card(s) {
    return `<div class="card" id="quizCard"><h2>Rules quiz</h2>
      <p class="muted">When this is on, renters answer a short quiz on the local cart rules before your map opens. Every question must be right; they can try again. Each pass is saved below with the code and time, so you have a record.</p>
      <p class="muted" id="quizNoticeAdmin">Renters also see: "This quiz is a reminder of the local cart rules, not legal advice. You must still follow posted signs and the law." The quiz is a rules reminder, not a liability waiver.</p>
      <label class="qz-on"><input type="checkbox" id="quizOn"${s && s.quiz_on ? ' checked' : ''}> Require the rules quiz before the map</label>
      <h3 class="dash-h">What renters see</h3>
      <ol id="quizPreview"><li class="muted">Loading the quiz…</li></ol>
      <p class="muted">The speed and road questions come from your region's cart rules. Your own rules (Rental info, Cart rules) are added as the last question.</p>
      <h3 class="dash-h">Passes</h3>
      <table id="quizPasses"><thead><tr><th>When</th><th>Code</th><th>Questions</th></tr></thead><tbody><tr><td colspan="3" class="muted">Loading…</td></tr></tbody></table>
    </div>`;
  }
  function paint() {
    const pv = $('#quizPreview');
    if (pv) pv.innerHTML = (info.questions || []).map(q => `<li><b>${esc(q.text)}</b><ul>${q.options.map(o => `<li>${o.id === q.answer ? '\u2713 ' : ''}${esc(o.text)}</li>`).join('')}</ul></li>`).join('') || '<li class="muted">No questions.</li>';
    const tb = $('#quizPasses tbody');
    if (tb) tb.innerHTML = (info.passes || []).map(p => `<tr><td>${esc(when(p.passed_at))}</td><td><code>${esc(p.code)}</code></td><td>${esc(String(p.questions))}</td></tr>`).join('')
      || '<tr><td colspan="3" class="muted">No passes yet.</td></tr>';
  }
  async function load() {
    try { info = await api('/shop/quiz'); } catch (e) { info = { on: false, questions: [], passes: [] }; }
    paint();
  }
  function bind() {
    const cb = $('#quizOn');
    if (!cb) return;
    cb.onchange = async () => {
      try {
        await api('/shop', { method: 'PATCH', body: JSON.stringify({ quiz_on: cb.checked }) });
        await refreshShop();
        flash(true, cb.checked ? 'Rules quiz on' : 'Rules quiz off');
      } catch (e) { flash(false, e.message); }
    };
    load();
  }
  window.GCMQuizAdmin = { card, bind };
})();
