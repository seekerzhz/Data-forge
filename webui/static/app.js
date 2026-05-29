const list = document.querySelector('#list');
const template = document.querySelector('#task-card-template');
const addButton = document.querySelector('[data-action="add-item"]');
let idx = 0;

function setStatus(card, text, state = 'idle', percent = 0) {
  const status = card.querySelector('.status');
  const progressBar = card.querySelector('.progress-bar');
  status.textContent = text;
  status.className = `status is-${state}`;
  card.classList.remove('is-active', 'is-waiting', 'is-processing', 'is-done', 'is-finished', 'is-failed', 'is-near-complete');
  card.classList.add(`is-${state}`);
  if (['waiting', 'processing', 'done', 'finished', 'failed'].includes(state)) {
    card.classList.add('is-active');
  }
  const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));
  progressBar.style.width = `${safePercent}%`;
  if (safePercent >= 86 && ['waiting', 'processing', 'done', 'finished'].includes(state)) {
    card.classList.add('is-near-complete');
  }
}

function bindLabel(field, id) {
  const label = field.querySelector('label');
  const control = field.querySelector('input, textarea');
  label.setAttribute('for', id);
  control.id = id;
}

function addItem() {
  idx += 1;
  const id = `item${idx}`;
  const card = template.content.firstElementChild.cloneNode(true);
  card.id = id;
  card.querySelector('.card-title').textContent = `题面 #${idx}`;
  bindLabel(card.querySelector('.field:nth-child(1)'), `${id}-pid`);
  bindLabel(card.querySelector('.field:nth-child(2)'), `${id}-cases`);
  bindLabel(card.querySelector('.card-body > .field'), `${id}-md`);
  card.querySelector('.submit').addEventListener('click', () => submitOne(card));
  card.querySelector('.clear').addEventListener('click', () => clearItem(card));
  list.appendChild(card);
}

function clearItem(card) {
  card.querySelector('.pid').value = '';
  card.querySelector('.num_cases').value = '20';
  card.querySelector('.md').value = '';
  setStatus(card, 'waiting-edit', 'idle', 0);
}

async function submitOne(card) {
  const pid = card.querySelector('.pid').value;
  const numCases = Number(card.querySelector('.num_cases').value || 20);
  const md = card.querySelector('.md').value;
  if (!md.trim()) {
    alert('题面不能为空');
    return;
  }
  if (!Number.isInteger(numCases) || numCases <= 0) {
    alert('数据组数必须是正整数');
    return;
  }
  setStatus(card, 'waiting', 'waiting', 4);
  card.querySelector('.submit').disabled = true;
  const response = await fetch('/tasks', {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({pid: pid, statement_markdown: md, num_cases: numCases}),
  });
  const payload = await response.json();
  card.dataset.taskId = payload.task_id;
  poll(card, payload.task_id);
  addItem();
}

function autoDownload(taskId) {
  const iframe = document.createElement('iframe');
  iframe.style.display = 'none';
  iframe.src = `/download/${taskId}`;
  document.body.appendChild(iframe);
}

function poll(card, taskId) {
  const timer = setInterval(async () => {
    const state = await (await fetch(`/tasks/${taskId}`)).json();
    setStatus(card, `${state.status} ${state.progress || ''}`, state.status, state.percent);
    if (state.status === 'done') {
      clearInterval(timer);
      autoDownload(taskId);
      setStatus(card, 'finished', 'finished', 100);
      await fetch(`/tasks/${taskId}/finish`, {method: 'POST'});
    }
    if (state.status === 'failed') {
      clearInterval(timer);
      card.querySelector('.submit').disabled = false;
    }
  }, 1200);
}

addButton.addEventListener('click', addItem);
addItem();
