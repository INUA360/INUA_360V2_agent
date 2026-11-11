const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const ACCESS_KEY = "inua_access";
let csrfToken: string | null = null;

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function readAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(ACCESS_KEY);
}

function writeAccessToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.sessionStorage.setItem(ACCESS_KEY, token);
  else window.sessionStorage.removeItem(ACCESS_KEY);
}

async function parseResponse(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const type = response.headers.get("content-type") ?? "";
  if (!type.includes("application/json")) return null;
  return response.json();
}

function errorFrom(response: Response, payload: unknown): ApiError {
  const envelope = payload as
    | { error?: { message?: string; details?: unknown }; detail?: string }
    | null;
  const message =
    envelope?.error?.message ?? envelope?.detail ?? "Request failed. Please try again.";
  return new ApiError(message, response.status, envelope?.error?.details);
}

async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  const response = await fetch(`${API_BASE}/auth/csrf`, {
    credentials: "include",
  });
  const payload = (await parseResponse(response)) as { csrfToken?: string } | null;
  csrfToken = payload?.csrfToken ?? null;
  return csrfToken ?? "";
}

async function refreshAccessToken(): Promise<boolean> {
  const token = await ensureCsrf();
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: token ? { "X-CSRFToken": token } : {},
  });
  if (!response.ok) {
    writeAccessToken(null);
    return false;
  }
  const payload = (await parseResponse(response)) as { access?: string } | null;
  if (!payload?.access) return false;
  writeAccessToken(payload.access);
  return true;
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  formData?: FormData;
  auth?: boolean;
  retry?: boolean;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    method = "GET",
    body,
    formData,
    auth = true,
    retry = true,
  } = options;
  const headers: Record<string, string> = {};
  const token = readAccessToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: "include",
    headers,
    body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
  });

  if (response.status === 401 && auth && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request<T>(path, { ...options, retry: false });
    }
  }

  const payload = await parseResponse(response);
  if (!response.ok) throw errorFrom(response, payload);
  return payload as T;
}

export type User = {
  id: string;
  email: string;
  phone: string;
  role: string;
  email_verified: boolean;
  onboarding_step: number;
  onboarding_percent: number;
  consent_version: string;
  consent_at: string | null;
};

export type Business = {
  id: string;
  name: string;
  trading_name: string;
  sector: string;
  what_they_sell: string;
  county: string;
  town: string;
  started_on: string;
  structure: string;
  employee_band: string;
  owner_name: string;
  owner_phone: string;
  onboarding_percent: number;
  years_operating: number;
};

export type Compliance = {
  id: string | null;
  registration_status: string;
  registration_number: string;
  kra_pin: string;
  pin_status: string;
  tcc_status: string;
  tcc_expiry: string | null;
  tcc_effective_status: string;
  county_permit_number: string;
  county_permit_expiry: string | null;
  permit_effective_status: string;
  other_permits: { name: string; expiry: string | null }[];
  verification: Record<string, string>;
};

export type ReadinessComponent = {
  key: string;
  label: string;
  points: number;
  max_points: number;
  explanation: string;
};

export type ReadinessGap = {
  key: string;
  component: string;
  message: string;
  points_gain: number;
  action: string;
};

export type ReadinessAssessment = {
  id: string;
  total_score: number;
  band: string;
  component_scores: ReadinessComponent[];
  gaps: ReadinessGap[];
  data_confidence: "low" | "medium" | "high";
  config_version: string;
  computed_at: string;
};

export type ReadinessResponse = {
  latest: ReadinessAssessment;
  history: ReadinessAssessment[];
  disclaimer: string;
};

export type Opportunity = {
  id: string;
  name: string;
  provider: string;
  provider_type: string;
  type: string;
  description: string;
  min_amount: string;
  max_amount: string;
  min_months_operating: number;
  min_readiness_score: number;
  allowed_sectors: string[];
  counties: string[];
  required_compliance: string[];
  required_documents: string[];
  accepts_informal: boolean;
  application_url: string;
  deadline: string | null;
  last_verified_at: string;
  notes: string;
};

export type OpportunityMatch = {
  id: string;
  opportunity: Opportunity;
  fit_level: "strong" | "possible" | "stretch";
  explanation: {
    summary: string;
    met: { key: string; label: string; detail: string }[];
    missing: { key: string; label: string; detail: string }[];
    moves_to_strong: string[];
    score_gap: number;
  };
  state: string;
  computed_at: string;
};

export type Checklist = {
  opportunity: {
    id: string;
    name: string;
    provider: string;
    application_url: string;
    description: string;
  };
  items: {
    key: string;
    label: string;
    status: "done" | "missing" | "not_applicable";
    detail: string;
    fix_path: string;
  }[];
  requirements_met: number;
  requirements_total: number;
  summary: string;
};

export type StatementPreview = {
  pending_id: string;
  expires_at: string;
  summary: {
    rows_parsed: number;
    rows_skipped: number;
    rows_seen: number;
    period_start: string | null;
    period_end: string | null;
    confidence: string;
    warnings: string[];
    skipped_reasons: { reason: string; count: number }[];
    preview: {
      source_ref: string;
      occurred_at: string;
      direction: string;
      amount: string;
      category: string;
      counterparty_text: string;
    }[];
    caveat: string;
  };
};

export type LoanRow = {
  id: string;
  lender: string;
  outstanding: string;
  monthly_repayment: string;
  ends_on: string | null;
};

export type DocumentRow = {
  id: string;
  doc_type: string;
  doc_type_label: string;
  filename: string;
  content_type: string;
  size: number;
  expiry_date: string | null;
  created_at: string;
};

export type DocumentsResponse = {
  checklist: { doc_type: string; label: string; present: boolean }[];
  documents?: DocumentRow[];
  results?: DocumentRow[];
  count?: number;
};

export const api = {
  hasToken: () => Boolean(readAccessToken()),
  clearToken: () => writeAccessToken(null),

  async register(payload: {
    email: string;
    phone?: string;
    password: string;
    consent_version: string;
    consent_given: boolean;
  }): Promise<{ user: User; access: string }> {
    const data = await request<{ user: User; access: string }>("/auth/register", {
      method: "POST",
      body: payload,
      auth: false,
    });
    writeAccessToken(data.access);
    return data;
  },

  async login(email: string, password: string): Promise<{ user: User; access: string }> {
    const data = await request<{ user: User; access: string }>("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    writeAccessToken(data.access);
    return data;
  },

  async logout(): Promise<void> {
    const token = await ensureCsrf();
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: token ? { "X-CSRFToken": token } : {},
      });
    } finally {
      writeAccessToken(null);
    }
  },

  me: () => request<User>("/me"),
  updateMe: (payload: Partial<User>) => request<User>("/me", { method: "PUT", body: payload }),

  business: () => request<Business>("/business"),
  saveBusiness: (payload: Record<string, unknown>) =>
    request<Business>("/business", { method: "PUT", body: payload }),

  compliance: () => request<Compliance>("/business/compliance"),
  saveCompliance: (payload: Record<string, unknown>) =>
    request<Compliance>("/business/compliance", { method: "PUT", body: payload }),

  readiness: () => request<ReadinessResponse>("/readiness"),
  recomputeReadiness: () => request<ReadinessResponse>("/readiness/recompute", { method: "POST" }),

  financialSummary: () => request<Record<string, unknown>>("/financials/summary"),
  monthly: () => request<Record<string, string | number>[]>("/financials/monthly"),

  loans: () => request<{ results?: LoanRow[] } | LoanRow[]>("/loans"),
  createLoan: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>("/loans", { method: "POST", body: payload }),
  deleteLoan: (id: string) => request<null>(`/loans/${id}`, { method: "DELETE" }),

  fundingNeed: () => request<Record<string, unknown>>("/funding-need"),
  saveFundingNeed: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>("/funding-need", { method: "PUT", body: payload }),

  parseStatement: (file: File, password: string) => {
    const data = new FormData();
    data.append("file", file);
    data.append("password", password);
    return request<StatementPreview>("/statements/parse", {
      method: "POST",
      formData: data,
    });
  },
  confirmStatement: (pendingId: string) =>
    request<Record<string, unknown>>(`/statements/${pendingId}/confirm`, { method: "POST" }),
  statements: () => request<{ results?: Record<string, unknown>[] }>("/statements"),

  documents: () => request<DocumentsResponse>("/documents"),
  uploadDocument: (file: File, docType: string, expiryDate?: string) => {
    const data = new FormData();
    data.append("file", file);
    data.append("doc_type", docType);
    if (expiryDate) data.append("expiry_date", expiryDate);
    return request<DocumentRow>("/documents", { method: "POST", formData: data });
  },
  deleteDocument: (id: string) => request<null>(`/documents/${id}`, { method: "DELETE" }),
  documentDownloadUrl: (id: string) =>
    request<{ url: string; expires_in: number }>(`/documents/${id}/download-url`),

  matches: () => request<OpportunityMatch[]>("/opportunities/matches"),
  updateMatchState: (id: string, state: string) =>
    request<OpportunityMatch>(`/opportunities/matches/${id}`, {
      method: "PATCH",
      body: { state },
    }),
  checklist: (id: string) => request<Checklist>(`/opportunities/${id}/checklist`),

  deleteMyData: () => request<null>("/me/data", { method: "DELETE" }),
};
