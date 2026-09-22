export const api_base = (import.meta.env.VITE_OPSCOPE_API_BASE || '/api/opscope').replace(/\/$/, '')
export async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(api_base + path, { method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? {} : {'Content-Type': 'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body), signal })
  const value = await response.json()
  if (!response.ok) throw new Error(value.error || value.detail || '服务暂不可用')
  return value
}
