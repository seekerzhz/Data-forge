// 状态管理模块：维护前端卡片序号和轮询定时器。
const state = {
  nextIndex: 0,
  timers: new Map(),
};

/**
 * 生成单调递增的前端卡片序号。
 * @returns {number} 新卡片序号。
 */
export function nextCardIndex() {
  state.nextIndex += 1;
  return state.nextIndex;
}

/**
 * 保存任务轮询定时器，重复保存前会清理旧定时器。
 * @param {string} cardId - 卡片 DOM id。
 * @param {number} timerId - setInterval 返回值。
 * @returns {void}
 */
export function setPollTimer(cardId, timerId) {
  clearPollTimer(cardId);
  state.timers.set(cardId, timerId);
}

/**
 * 清理指定卡片的轮询定时器。
 * @param {string} cardId - 卡片 DOM id。
 * @returns {void}
 */
export function clearPollTimer(cardId) {
  const timerId = state.timers.get(cardId);
  if (timerId) {
    window.clearInterval(timerId);
    state.timers.delete(cardId);
  }
}
