// 应用编排模块：连接用户事件、API 服务、状态管理与渲染模块。
import {autoDownload, createTask, finishTask, getTask} from './api.js';
import {clearPollTimer, nextCardIndex, setPollTimer} from './store.js';
import {bindLabel, clearForm, readTaskForm, requireElement, setStatus, setSubmitDisabled} from './ui.js';

const POLL_INTERVAL_MS = 1200;
const list = requireElement(document, '#list');
const template = requireElement(document, '#task-card-template');
const addButton = requireElement(document, '[data-action="add-item"]');

/**
 * 根据模板创建新任务卡片并绑定事件。
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
  requireElement(card, '.submit').addEventListener('click', () => submitOne(card));
  requireElement(card, '.clear').addEventListener('click', () => {
    clearPollTimer(card.id);
    clearForm(card);
    setSubmitDisabled(card, false);
  });
  list.appendChild(card);
}

/**
 * 提交单张卡片，并在成功后追加下一张空卡片。
 * @param {HTMLElement} card - 任务卡片。
 * @returns {Promise<void>}
 */
async function submitOne(card) {
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
    poll(card, payload.task_id);
    addItem();
  } catch (error) {
    setStatus(card, error.message, 'failed', 100);
    setSubmitDisabled(card, false);
  }
}

/**
 * 轮询后端任务状态，并在完成时触发下载和终态清理。
 * @param {HTMLElement} card - 任务卡片。
 * @param {string} taskId - 后端任务标识。
 * @returns {void}
 */
function poll(card, taskId) {
  const timer = window.setInterval(async () => {
    try {
      const state = await getTask(taskId);
      setStatus(card, `${state.status} ${state.progress || ''}`.trim(), state.status, state.percent);

      if (state.status === 'done') {
        clearPollTimer(card.id);
        autoDownload(taskId);
        setStatus(card, 'finished', 'finished', 100);
        await finishTask(taskId);
      }

      if (state.status === 'failed') {
        clearPollTimer(card.id);
        setSubmitDisabled(card, false);
      }
    } catch (error) {
      clearPollTimer(card.id);
      setStatus(card, error.message, 'failed', 100);
      setSubmitDisabled(card, false);
    }
  }, POLL_INTERVAL_MS);

  setPollTimer(card.id, timer);
}

addButton.addEventListener('click', addItem);
addItem();
