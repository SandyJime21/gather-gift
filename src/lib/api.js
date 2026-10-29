let csrfToken = null;
let csrfRequest = null;
let sessionGeneration = 0;
const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "";

async function request(path, options) {
  try {
    return await fetch(`${API_BASE}${path}`, { ...options, credentials: 'include' });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Cannot connect to the server. Check your connection and try again. For local development, run npm run dev to start both servers.');
  }
}

async function readJson(response) {
  const data = await response.json().catch(() => null);
  if (!data) throw Object.assign(new Error(response.status >= 500
    ? 'The server is unavailable. Please try again shortly.'
    : 'The server returned an unexpected response. Refresh the page and try again.'), {status: response.status});
  return data;
}

async function getCsrfToken() {
  if (csrfToken) return csrfToken;
  if (!csrfRequest) {
    const generation = sessionGeneration;
    const pending = (async () => {
    const response = await request('/api/auth/csrf');
    const data = await readJson(response);
    if (!response.ok || !data.csrf_token) throw new Error(data.error || 'Could not start a secure session. Please refresh and try again.');
    if (generation !== sessionGeneration) return getCsrfToken();
    csrfToken = data.csrf_token;
    return csrfToken;
    })().finally(() => { if (csrfRequest === pending) csrfRequest = null; });
    csrfRequest = pending;
  }
  return csrfRequest;
}

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method || 'GET')) headers.set('X-CSRF-Token', await getCsrfToken());
  const generation = sessionGeneration;
  const response = await request(`/api${path}`, { ...options, headers });
  const data = await readJson(response);
  if (!response.ok) throw Object.assign(new Error(data.error || 'Something went wrong. Please try again.'), {status: response.status});
  if (data.csrf_token && generation === sessionGeneration) {
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method || 'GET')) sessionGeneration++;
    csrfToken = data.csrf_token;
  }
  return data;
}

export function clearCsrfToken() { sessionGeneration++; csrfToken = null; csrfRequest = null; }
export function mediaUrl(path) { return path?.startsWith('/api/') ? `${API_BASE}${path}` : path; }
