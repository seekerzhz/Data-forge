// API 服务模块：集中封装后端请求、错误处理与下载触发。
const JSON_HEADERS = {'content-type': 'application/json'};

/**
 * 调用后端 JSON API，并把非 2xx 响应转换为可展示错误。
 * @param {string} url - API 路径。
 * @param {RequestInit} [options] - fetch 配置。
 * @returns {Promise<object>} 解析后的 JSON 响应。
 */
export async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  let payload = {};

  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }

  if (!response.ok) {
    const message = payload.detail || payload.error || `请求失败：${response.status}`;
    throw new Error(message);
  }

  return payload;
}

/**
 * 创建后端生成任务。
 * @param {{pid: string, statementMarkdown: string, numCases: number}} task - 表单任务数据。
 * @returns {Promise<{task_id: string}>} 后端任务标识。
 */
export function createTask({pid, statementMarkdown, numCases}) {
  return requestJson('/tasks', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({pid, statement_markdown: statementMarkdown, num_cases: numCases}),
  });
}

/**
 * 读取任务状态。
 * @param {string} taskId - 后端任务标识。
 * @returns {Promise<{status: string, progress?: string, percent?: number}>} 当前任务进度。
 */
export function getTask(taskId) {
  return requestJson(`/tasks/${encodeURIComponent(taskId)}`);
}

/**
 * 通知后端下载已触发，任务可以进入终态。
 * @param {string} taskId - 后端任务标识。
 * @returns {Promise<object>} 操作结果。
 */
export function finishTask(taskId) {
  return requestJson(`/tasks/${encodeURIComponent(taskId)}/finish`, {method: 'POST'});
}

/**
 * 通过隐藏 iframe 触发文件下载，避免离开当前表单页。
 * @param {string} taskId - 后端任务标识。
 * @returns {void}
 */
export function autoDownload(taskId) {
  const iframe = document.createElement('iframe');
  iframe.hidden = true;
  iframe.src = `/download/${encodeURIComponent(taskId)}`;
  document.body.appendChild(iframe);
}
