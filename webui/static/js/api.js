// API 服务模块：集中封装后端请求、错误处理、SSE 与下载触发。
const JSON_HEADERS = {'content-type': 'application/json'};
const TOKEN_STORAGE_KEY = 'dataforge_api_token';

/**
 * @returns {string} 当前保存的 API Token。
 */
export function getApiToken() {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY) || '';
}

/**
 * @param {string} token - API Token。
 * @returns {void}
 */
export function setApiToken(token) {
  const value = (token || '').trim();
  if (value) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, value);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

/**
 * @returns {Record<string, string>} 带鉴权的请求头。
 */
function authHeaders(extra = {}) {
  const headers = {...extra};
  const token = getApiToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

/**
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<object>}
 */
export async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: authHeaders({...(options.headers || {})}),
  });
  let payload = {};

  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }

  if (!response.ok) {
    const message = payload.detail || payload.error || `请求失败：${response.status}`;
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }

  return payload;
}

/**
 * @returns {Promise<{auth_required: boolean, bind_hint: string}>}
 */
export function fetchMeta() {
  return requestJson('/api/meta');
}

/**
 * @param {{pid: string, statementMarkdown: string, numCases: number, customSolution?: string}} task
 * @returns {Promise<{task_id: string}>}
 */
export function createTask({pid, statementMarkdown, numCases, customSolution}) {
  return requestJson('/tasks', {
    method: 'POST',
    headers: authHeaders(JSON_HEADERS),
    body: JSON.stringify({
      pid,
      statement_markdown: statementMarkdown,
      num_cases: numCases,
      custom_solution: customSolution || null,
    }),
  });
}

/**
 * @param {string} taskId
 * @returns {Promise<{status: string, progress?: string, percent?: number}>}
 */
export function getTask(taskId) {
  return requestJson(`/tasks/${encodeURIComponent(taskId)}`);
}

/**
 * @param {string} taskId
 * @returns {Promise<object>}
 */
export function finishTask(taskId) {
  return requestJson(`/tasks/${encodeURIComponent(taskId)}/finish`, {method: 'POST'});
}

/**
 * 通过隐藏 iframe 触发文件下载；token 走 query 以兼容 iframe。
 * @param {string} taskId
 * @returns {void}
 */
export function autoDownload(taskId) {
  const iframe = document.createElement('iframe');
  iframe.hidden = true;
  const token = getApiToken();
  const query = token ? `?token=${encodeURIComponent(token)}` : '';
  iframe.src = `/download/${encodeURIComponent(taskId)}${query}`;
  document.body.appendChild(iframe);
}

/**
 * 优先使用 SSE 推送；失败时回退指数退避轮询。
 * @param {string} taskId
 * @param {(state: object) => void | Promise<void>} onUpdate
 * @param {{signal?: AbortSignal}} [options]
 * @returns {Promise<void>}
 */
export async function watchTask(taskId, onUpdate, options = {}) {
  const signal = options.signal;
  try {
    await watchTaskSse(taskId, onUpdate, signal);
  } catch (_error) {
    await watchTaskBackoff(taskId, onUpdate, signal);
  }
}

/**
 * @param {string} taskId
 * @param {(state: object) => void | Promise<void>} onUpdate
 * @param {AbortSignal} [signal]
 * @returns {Promise<void>}
 */
function watchTaskSse(taskId, onUpdate, signal) {
  return new Promise((resolve, reject) => {
    const token = getApiToken();
    const query = token ? `?token=${encodeURIComponent(token)}` : '';
    const source = new EventSource(`/tasks/${encodeURIComponent(taskId)}/events${query}`);
    let settled = false;

    const cleanup = () => {
      source.close();
      if (signal) {
        signal.removeEventListener('abort', onAbort);
      }
    };

    const finish = (fn, value) => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      fn(value);
    };

    const onAbort = () => finish(resolve);

    source.addEventListener('status', async (event) => {
      try {
        const state = JSON.parse(event.data);
        await onUpdate(state);
        if (['done', 'failed', 'finished'].includes(state.status)) {
          finish(resolve);
        }
      } catch (error) {
        finish(reject, error);
      }
    });

    source.onerror = () => {
      finish(reject, new Error('sse unavailable'));
    };

    if (signal) {
      if (signal.aborted) {
        finish(resolve);
        return;
      }
      signal.addEventListener('abort', onAbort, {once: true});
    }
  });
}

/**
 * @param {string} taskId
 * @param {(state: object) => void | Promise<void>} onUpdate
 * @param {AbortSignal} [signal]
 * @returns {Promise<void>}
 */
async function watchTaskBackoff(taskId, onUpdate, signal) {
  let delay = 800;
  const maxDelay = 8000;

  while (!signal?.aborted) {
    const state = await getTask(taskId);
    await onUpdate(state);
    if (['done', 'failed', 'finished'].includes(state.status)) {
      return;
    }
    await sleep(delay, signal);
    delay = Math.min(maxDelay, Math.round(delay * 1.6));
  }
}

/**
 * @param {number} ms
 * @param {AbortSignal} [signal]
 * @returns {Promise<void>}
 */
function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      resolve();
      return;
    }
    const timer = window.setTimeout(resolve, ms);
    if (!signal) {
      return;
    }
    const onAbort = () => {
      window.clearTimeout(timer);
      resolve();
    };
    signal.addEventListener('abort', onAbort, {once: true});
  });
}
