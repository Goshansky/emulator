import type {
  ErrorDiagnostic,
  ProgramExample,
  SessionResponse,
  StateResponse,
  StepResponse,
} from '../types';

const BASE_URL = '/api';

/** Ошибка API с диагностикой бэкенда (код, позиция в исходнике). */
export class ApiError extends Error {
  readonly diagnostic: ErrorDiagnostic | null;
  readonly status: number;

  constructor(status: number, diagnostic: ErrorDiagnostic | null) {
    super(diagnostic?.message ?? `Ошибка запроса: HTTP ${status}.`);
    this.name = 'ApiError';
    this.status = status;
    this.diagnostic = diagnostic;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(BASE_URL + path, init);
  } catch {
    throw new ApiError(0, {
      code: 'NETWORK',
      message: 'Нет связи с сервером эмулятора.',
      target: 'machine',
    });
  }
  if (!response.ok) {
    let diagnostic: ErrorDiagnostic | null = null;
    try {
      const body = await response.json();
      if (body && typeof body === 'object' && body.detail && typeof body.detail === 'object') {
        diagnostic = body.detail as ErrorDiagnostic;
      }
    } catch {
      diagnostic = null;
    }
    throw new ApiError(response.status, diagnostic);
  }
  return (await response.json()) as T;
}

const post = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<{ status: string }>('/health'),
  programs: () => request<readonly ProgramExample[]>('/programs'),
  createSession: (source: string, data: string) =>
    request<SessionResponse>('/sessions', post({ source, data })),
  getSession: (sessionId: string) => request<StateResponse>(`/sessions/${sessionId}`),
  steps: (sessionId: string, count: number) =>
    request<StepResponse>(`/sessions/${sessionId}/steps`, post({ count })),
  reset: (sessionId: string) =>
    request<StateResponse>(`/sessions/${sessionId}/reset`, { method: 'POST' }),
};
