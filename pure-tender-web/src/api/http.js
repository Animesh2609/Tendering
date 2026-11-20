import { API_BASE_URL } from '../data/constants';
import { parseApiJson } from './parseApiJson.js';
import { showToast } from '../context/ToastContext';

export class ApiError extends Error {
  constructor(message, status = 0) { super(message); this.name = 'ApiError'; this.status = status; }
}

export async function http(path, { method = 'GET', body, token, signal, binary = false, responseType = 'json' } = {}) {
  const isMultipart = body instanceof FormData;
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal,
      headers: {
        ...(!isMultipart && body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      ...(body !== undefined ? { body: isMultipart ? body : JSON.stringify(body) } : {}),
    });
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    const message = 'Cannot connect to Spring Boot. Check the backend server and Vite proxy.';
    showToast(message, 'error');
    throw new ApiError(message);
  }
  if (response.ok && (binary || responseType === 'blob')) return response.blob();
  const raw = await response.text();
  let data;
  try { data = raw ? parseApiJson(raw) : null; } catch { data = raw; }
  if (!response.ok) {
    if (response.status === 401 && token && typeof window !== 'undefined') {
      window.dispatchEvent(new Event('tenderblock:session-expired'));
    }
    const message = typeof data === 'object' && data
      ? (data.message || data.error || data.detail)
      : null;
    if ([502, 503, 504].includes(response.status)) {
      const unavailable = `Backend/API gateway unavailable (HTTP ${response.status}). Check Spring Boot and its database or Fabric startup logs.`;
      showToast(unavailable, 'error');
      throw new ApiError(unavailable, response.status);
    }
    const errorMessage = message || `Request failed (${response.status}).`;
    showToast(errorMessage, 'error');
    throw new ApiError(errorMessage, response.status);
  }
  if (method !== 'GET' && method !== 'HEAD') {
    const successMessage = method === 'DELETE'
      ? 'Removed successfully.'
      : /\/auth\/login/.test(path) ? 'Signed in successfully.'
        : /\/auth\/register/.test(path) ? 'Account created successfully.'
          : /\/tenders\/?(?:\?|$)/.test(path) && method === 'POST' ? 'Tender submitted successfully.'
            : /\/bids\/?(?:\?|$)/.test(path) && method === 'POST' ? 'Bid submitted successfully.'
              : 'Changes saved successfully.';
    showToast(successMessage, 'success');
  }
  return data;
}

export const pageItems = value => Array.isArray(value) ? value : value?.content || [];

// Fetch every Spring Page so staff queues do not silently stop at 100 records.
export async function readAllPages(path, token, signal) {
  const items = [];
  for (let page = 0; page < 1000; page += 1) {
    const separator = path.includes('?') ? '&' : '?';
    const response = await http(`${path}${separator}page=${page}&size=100`, { token, signal });
    if (Array.isArray(response)) return response;
    if (!Array.isArray(response?.content)) throw new ApiError('Expected a Spring Page response.');
    items.push(...response.content);
    if (response.last || page + 1 >= response.totalPages || !response.content.length) return items;
  }
  throw new ApiError('The queue is too large to load. Narrow the backend results.');
}
