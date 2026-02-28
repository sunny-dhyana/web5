const BASE_URL = "/api";

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
};

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private onUnauthorized: (() => void) | null = null;

  constructor() {
    this.accessToken = localStorage.getItem("mercury_access_token");
    this.refreshToken = localStorage.getItem("mercury_refresh_token");
  }

  setTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem("mercury_access_token", accessToken);
    localStorage.setItem("mercury_refresh_token", refreshToken);
  }

  clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem("mercury_access_token");
    localStorage.removeItem("mercury_refresh_token");
  }

  setOnUnauthorized(cb: () => void): void {
    this.onUnauthorized = cb;
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  private buildHeaders(extra?: Record<string, string>): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...extra,
    };
    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }
    return headers;
  }

  private async tryRefresh(): Promise<boolean> {
    if (!this.refreshToken) return false;
    try {
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      if (res.ok) {
        const data = await res.json();
        this.accessToken = data.access_token;
        this.refreshToken = data.refresh_token;
        localStorage.setItem("mercury_access_token", data.access_token);
        localStorage.setItem("mercury_refresh_token", data.refresh_token);
        return true;
      }
    } catch {
      // Refresh failed
    }
    return false;
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, headers: extraHeaders } = options;

    const doFetch = (headers: Record<string, string>) =>
      fetch(`${BASE_URL}${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });

    let res = await doFetch(this.buildHeaders(extraHeaders));

    if (res.status === 401) {
      const refreshed = await this.tryRefresh();
      if (refreshed) {
        res = await doFetch(this.buildHeaders(extraHeaders));
      } else {
        this.clearTokens();
        this.onUnauthorized?.();
        throw new Error("Session expired. Please log in again.");
      }
    }

    if (res.status === 204) return null as T;

    const data = await res.json().catch(() => ({ detail: "Unexpected server response" }));

    if (!res.ok) {
      let errorMessage = `Request failed: ${res.status}`;
      if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMessage = data.detail.map((err: any) => err.msg).join(", ");
      } else if (data.detail) {
        errorMessage = JSON.stringify(data.detail);
      }
      throw new Error(errorMessage);
    }

    return data as T;
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>(path);
  }

  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, { method: "POST", body });
  }

  put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, { method: "PUT", body });
  }

  patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, { method: "PATCH", body });
  }

  delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "DELETE" });
  }
}

export const api = new ApiClient();
