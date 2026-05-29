// 渲染模块：负责 DOM 查询、表单校验、状态渲染和可访问性绑定。
const ACTIVE_STATES = new Set(['waiting', 'processing', 'done', 'finished', 'failed']);
const NEAR_COMPLETE_STATES = new Set(['waiting', 'processing', 'done', 'finished']);
const CARD_STATES = ['is-active', 'is-waiting', 'is-processing', 'is-done', 'is-finished', 'is-failed', 'is-near-complete'];

/**
 * 安全获取卡片内的必需元素，缺失时抛出明确错误。
 * @param {Element} root - 查询根节点。
 * @param {string} selector - CSS 选择器。
 * @returns {Element} 匹配元素。
 */
export function requireElement(root, selector) {
  const element = root.querySelector(selector);
  if (!element) {
    throw new Error(`页面结构缺少元素：${selector}`);
  }
  return element;
}

/**
 * 更新卡片状态文字、状态类和进度条宽度。
 * @param {HTMLElement} card - 任务卡片。
 * @param {string} text - 状态文本。
 * @param {string} [state='idle'] - 状态枚举。
 * @param {number} [percent=0] - 进度百分比。
 * @returns {void}
 */
export function setStatus(card, text, state = 'idle', percent = 0) {
  const status = requireElement(card, '.status');
  const progressBar = requireElement(card, '.progress-bar');
  const safePercent = Math.max(0, Math.min(100, Number(percent) || 0));

  status.textContent = text;
  status.className = `status is-${state}`;
  card.classList.remove(...CARD_STATES);
  card.classList.add(`is-${state}`);

  if (ACTIVE_STATES.has(state)) {
    card.classList.add('is-active');
  }
  if (safePercent >= 86 && NEAR_COMPLETE_STATES.has(state)) {
    card.classList.add('is-near-complete');
  }

  progressBar.style.width = `${safePercent}%`;
}

/**
 * 绑定 label 与控件 id，提升可访问性并避免 nth-child 结构耦合。
 * @param {HTMLElement} card - 任务卡片。
 * @param {string} fieldName - data-field 名称。
 * @param {string} id - 控件 id。
 * @returns {void}
 */
export function bindLabel(card, fieldName, id) {
  const field = requireElement(card, `[data-field="${fieldName}"]`);
  const label = requireElement(field, 'label');
  const control = requireElement(field, 'input, textarea');
  label.setAttribute('for', id);
  control.id = id;
}

/**
 * 从卡片读取并校验用户输入。
 * @param {HTMLElement} card - 任务卡片。
 * @returns {{pid: string, statementMarkdown: string, numCases: number}} 表单数据。
 */
export function readTaskForm(card) {
  const pid = /** @type {HTMLInputElement} */ (requireElement(card, '.pid')).value.trim();
  const numCases = Number(/** @type {HTMLInputElement} */ (requireElement(card, '.num_cases')).value || 20);
  const statementMarkdown = /** @type {HTMLTextAreaElement} */ (requireElement(card, '.md')).value;

  if (!statementMarkdown.trim()) {
    throw new Error('题面不能为空');
  }
  if (!Number.isInteger(numCases) || numCases < 1 || numCases > 100) {
    throw new Error('数据组数必须是 1 到 100 之间的整数');
  }

  return {pid, statementMarkdown, numCases};
}

/**
 * 重置卡片输入内容与状态。
 * @param {HTMLElement} card - 任务卡片。
 * @returns {void}
 */
export function clearForm(card) {
  /** @type {HTMLInputElement} */ (requireElement(card, '.pid')).value = '';
  /** @type {HTMLInputElement} */ (requireElement(card, '.num_cases')).value = '20';
  /** @type {HTMLTextAreaElement} */ (requireElement(card, '.md')).value = '';
  setStatus(card, 'waiting-edit', 'idle', 0);
}

/**
 * 设置提交按钮禁用状态。
 * @param {HTMLElement} card - 任务卡片。
 * @param {boolean} disabled - 是否禁用。
 * @returns {void}
 */
export function setSubmitDisabled(card, disabled) {
  /** @type {HTMLButtonElement} */ (requireElement(card, '.submit')).disabled = disabled;
}
