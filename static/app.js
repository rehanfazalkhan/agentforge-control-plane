const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);
}

async function loadOverview() {
  const response = await fetch('/api/overview');
  const data = await response.json();
  $('#totalRuns').textContent = data.total_runs;
  $('#successRate').textContent = data.total_runs ? `${data.success_rate}%` : '--';
  $('#evalRate').textContent = data.total_runs ? `${data.evaluation_pass_rate}%` : '--';
  $('#policyBlocks').textContent = data.policy_blocks;
}

async function loadTools() {
  const response = await fetch('/api/tools');
  const tools = await response.json();
  $('#toolList').innerHTML = tools.map((tool) => `<div class="tool"><h3>${escapeHtml(tool.name)}</h3><p>${escapeHtml(tool.description)}</p><span class="roles">${tool.roles.join(' · ')}</span></div>`).join('');
}

function renderRun(run) {
  $('#resultTitle').textContent = `${run.route} specialist response`;
  $('#responseText').textContent = run.response;
  const badge = $('#statusBadge');
  badge.textContent = run.status;
  badge.className = `status ${run.status}`;
  $('#latency').textContent = `${run.latency_ms} ms`;
  $('#citationList').innerHTML = run.citations.map((citation) => `<span class="citation">Source: ${escapeHtml(citation)}</span>`).join('');
  $('#evaluationList').innerHTML = run.evaluations.map((evaluation) => `<div class="evaluation"><strong>${evaluation.passed ? 'PASS' : 'REVIEW'} · ${escapeHtml(evaluation.name)}</strong><span>${escapeHtml(evaluation.rationale)}</span></div>`).join('');
  $('#traceList').innerHTML = run.trace.map((span) => `<li><b>${escapeHtml(span.name)}</b><small>${escapeHtml(span.kind)} · ${span.duration_ms} ms${span.attributes.route ? ` · ${escapeHtml(span.attributes.route)}` : ''}</small></li>`).join('');
}

$('#runForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = $('#runButton');
  button.disabled = true;
  button.textContent = 'Running governed workflow…';
  try {
    const response = await fetch('/api/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: $('#question').value, actor_role: $('#actorRole').value }) });
    if (!response.ok) throw new Error('The workflow could not be started.');
    renderRun(await response.json());
    await loadOverview();
  } catch (error) {
    $('#responseText').textContent = error.message;
    $('#statusBadge').textContent = 'error';
    $('#statusBadge').className = 'status blocked';
  } finally {
    button.disabled = false;
    button.innerHTML = 'Run agent workflow <span>→</span>';
  }
});

document.querySelectorAll('.quick-prompts button').forEach((button) => button.addEventListener('click', () => {
  $('#question').value = button.dataset.prompt;
  $('#actorRole').value = button.dataset.role;
  $('#runForm').requestSubmit();
}));

Promise.all([loadOverview(), loadTools()]);
