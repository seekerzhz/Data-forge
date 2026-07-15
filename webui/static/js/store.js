// 状态管理模块：维护前端卡片序号和 AbortController。
const state = {
  nextIndex: 0,
  controllers: new Map(),
};

/**
 * @returns {number}
 */
export function nextCardIndex() {
  state.nextIndex += 1;
  return state.nextIndex;
}

/**
 * @param {string} cardId
 * @returns {AbortSignal}
 */
export function beginWatch(cardId) {
  stopWatch(cardId);
  const controller = new AbortController();
  state.controllers.set(cardId, controller);
  return controller.signal;
}

/**
 * @param {string} cardId
 * @returns {void}
 */
export function stopWatch(cardId) {
  const controller = state.controllers.get(cardId);
  if (controller) {
    controller.abort();
    state.controllers.delete(cardId);
  }
}

/** @deprecated 兼容旧命名 */
export function clearPollTimer(cardId) {
  stopWatch(cardId);
}

/** @deprecated 兼容旧命名 */
export function setPollTimer() {
  // no-op: 已改用 AbortController
}
