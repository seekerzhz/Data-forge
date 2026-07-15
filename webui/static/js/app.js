// 应用编排模块：连接用户事件、API 服务、状态管理与渲染模块。
import {autoDownload, createTask, fetchMeta, finishTask, getApiToken, setApiToken, watchTask} from './api.js';
import {beginWatch, nextCardIndex, stopWatch} from './store.js';
import {bindLabel, clearForm, readTaskForm, requireElement, setStatus, setSubmitDisabled} from './ui.js';

const list = requireElement(document, '#list');
const template = requireElement(document, '#task-card-template');
const addButton = requireElement(document, '[data-action="add-item"]');
const tokenInput = /** @type {HTMLInputElement} */ (requireElement(document, '#api-token'));
const authHint = requireElement(document, '#auth-hint');

tokenInput.value = getApiToken();
tokenInput.addEventListener('change', () => setApiToken(tokenInput.value));
tokenInput.addEventListener('blur', () => setApiToken(tokenInput.value));

fetchMeta()
  .then((meta) => {
    if (meta.auth_required) {
      authHint.textContent = '服务已启用 API Token，请在上方填写后提交。';
      authHint.hidden = false;
    } else {
      authHint.textContent = `当前未强制鉴权；建议仅绑定 ${meta.bind_hint || '127.0.0.1'}。`;
      authHint.hidden = false;
    }
  })
  .catch(() => {
    authHint.hidden = true;
  });

/**
 * @returns {void}
 */
function addItem() {
  const index = nextCardIndex();
  const id = `item${index}`;
  const card = /** @type {HTMLElement} */ (template.content.firstElementChild.cloneNode(true));

  card.id = id;
  requireElement(card, '.card-title').textContent = `题面 #${index}`;
  bindLabel(card, 'pid', `${id}-pid`);
  bindLabel(card, 'cases', `${id}-cases`);
  bindLabel(card, 'markdown', `${id}-md`);
  bindLabel(card, 'custom-solution', `${id}-custom-solution`);
  const customToggle = /** @type {HTMLInputElement} */ (requireElement(card, '.custom-solution-toggle'));
  const customPanel = requireElement(card, '.custom-solution-panel');
  customToggle.id = `${id}-custom-solution-toggle`;
  customToggle.addEventListener('change', () => {
    customPanel.hidden = !customToggle.checked;
  });
  requireElement(card, '.submit').addEventListener('click', () => submitOne(card));
  requireElement(card, '.clear').addEventListener('click', () => {
    stopWatch(card.id);
    clearForm(card);
    setSubmitDisabled(card, false);
  });
  list.appendChild(card);
}

/**
 * @param {HTMLElement} card
 * @returns {Promise<void>}
 */
async function submitOne(card) {
  setApiToken(tokenInput.value);

  let form;
  try {
    form = readTaskForm(card);
  } catch (error) {
    window.alert(error.message);
    return;
  }

  setStatus(card, 'waiting', 'waiting', 4);
  setSubmitDisabled(card, true);

  try {
    const payload = await createTask(form);
    card.dataset.taskId = payload.task_id;
    const signal = beginWatch(card.id);
    await watchTask(payload.task_id, async (state) => {
      setStatus(card, `${state.status} ${state.progress || ''}`.trim(), state.status, state.percent);
      if (state.status === 'done') {
        autoDownload(payload.task_id);
        setStatus(card, 'finished', 'finished', 100);
        await finishTask(payload.task_id);
        stopWatch(card.id);
      }
      if (state.status === 'failed') {
        setSubmitDisabled(card, false);
        stopWatch(card.id);
      }
    }, {signal});
    addItem();
  } catch (error) {
    setStatus(card, error.message, 'failed', 100);
    setSubmitDisabled(card, false);
    stopWatch(card.id);
  }
}

addButton.addEventListener('click', addItem);
addItem();
