/**
 * API client for Hire Desk AI.
 *
 * - Prefixes all requests with VITE_API_BASE_URL
 * - Sends Content-Type: application/json for POST and PATCH
 * - Parses JSON responses when a body exists (not 204)
 * - Throws ApiError for non-2xx responses
 * - Applies a 30-second timeout only to /analyze calls
 * - Produces clear network/timeout errors without exposing internals
 *
 * Requirements: 7.2, 8.3, 8.4
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

const ANALYZE_TIMEOUT_MS = 30_000

/**
 * Typed error thrown on non-2xx API responses.
 */
export class ApiError extends Error {
  public readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Internal: build full URL from a relative path.
 */
function buildUrl(path: string): string {
  // Ensure no double slashes between base and path
  const base = BASE_URL.endsWith('/') ? BASE_URL.slice(0, -1) : BASE_URL
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${normalizedPath}`
}

/**
 * Internal: determine if this path should use the extended timeout.
 */
function needsTimeout(path: string): boolean {
  return path.startsWith('/analyze') || path === 'analyze'
}

/**
 * Internal: execute a fetch request with optional timeout and error handling.
 */
async function request<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = buildUrl(path)
  const controller = new AbortController()
  let timeoutId: ReturnType<typeof setTimeout> | undefined

  if (needsTimeout(path)) {
    timeoutId = setTimeout(() => controller.abort(), ANALYZE_TIMEOUT_MS)
  }

  let response: Response

  try {
    response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
  } catch (error: unknown) {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId)
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(0, 'Request timed out. Please try again.')
    }

    throw new ApiError(0, 'Network error. Please check your connection.')
  } finally {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId)
    }
  }

  if (!response.ok) {
    // Try to extract a safe message from the error envelope
    let message = `Request failed with status ${response.status}`
    try {
      const body = await response.json()
      if (body?.error?.message) {
        message = body.error.message
      }
    } catch {
      // Response body was not JSON — use the default message
    }
    throw new ApiError(response.status, message)
  }

  // 204 No Content — no body to parse
  if (response.status === 204) {
    return undefined as unknown as T
  }

  // Parse JSON response
  return (await response.json()) as T
}

/**
 * GET request.
 */
export async function get<T = unknown>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' })
}

/**
 * POST request with JSON body.
 */
export async function post<T = unknown>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/**
 * PATCH request with JSON body.
 */
export async function patch<T = unknown>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/**
 * DELETE request.
 */
export async function del<T = unknown>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}
