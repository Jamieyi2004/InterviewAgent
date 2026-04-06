/**
 * 后端 API 调用封装（含认证）
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

/**
 * 带认证的 fetch 包装器
 * - 自动注入 Authorization: Bearer <token>
 * - 401 时清 token 跳登录页
 */
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("token");
    window.location.href = "/login";
  }
  return res;
}

// ========== 认证 ==========

export interface AuthUser {
  id: number;
  email: string;
  username: string;
  role: "user" | "admin";
  created_at: string;
}

export async function registerUser(
  email: string,
  username: string,
  password: string
): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "注册失败");
  }
  return res.json();
}

export async function loginUser(
  email: string,
  password: string
): Promise<{ access_token: string; token_type: string; user: AuthUser }> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "登录失败");
  }
  return res.json();
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Token 无效");
  return res.json();
}

// ========== 简历 ==========

export async function uploadResume(file: File): Promise<{
  resume_id: number;
  filename: string;
  parsed_data: Record<string, unknown>;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await authFetch(`${API_BASE}/api/resume/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "简历上传失败");
  }

  return res.json();
}

// ========== 面试 ==========

export async function startInterview(
  resumeId: number,
  position: string
): Promise<{ session_id: number; message: string }> {
  const res = await authFetch(`${API_BASE}/api/interview/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume_id: resumeId, position }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "创建面试失败");
  }

  return res.json();
}

export async function endInterview(
  sessionId: number
): Promise<{ message: string }> {
  const res = await authFetch(`${API_BASE}/api/interview/end/${sessionId}`, {
    method: "POST",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "结束面试失败");
  }

  return res.json();
}

// ========== 报告 ==========

export async function generateReport(
  sessionId: number
): Promise<Record<string, unknown>> {
  const res = await authFetch(`${API_BASE}/api/report/generate/${sessionId}`, {
    method: "POST",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "报告生成失败");
  }

  return res.json();
}

export async function fetchReport(
  sessionId: number
): Promise<Record<string, unknown>> {
  const res = await authFetch(`${API_BASE}/api/report/${sessionId}`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "获取报告失败");
  }

  return res.json();
}

// ========== 算法题 ==========

export interface CodingProblem {
  id: string;
  title: string;
  difficulty: string;
  description: string;
  example: string;
  signature: string;
}

export async function fetchProblem(
  sessionId: number
): Promise<CodingProblem | null> {
  const res = await authFetch(`${API_BASE}/api/interview/problem/${sessionId}`);
  if (!res.ok) return null;
  return res.json();
}

// ========== 会话管理 ==========

export interface SessionListItem {
  id: number;
  resume_id: number;
  candidate_name: string;
  resume_filename: string;
  position: string;
  status: string;
  current_stage: string;
  overall_score: number | null;
  created_at: string | null;
  ended_at: string | null;
  message_count: number;
}

export interface SessionListResponse {
  items: SessionListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SessionListParams {
  status?: string;
  position?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
}

export async function fetchSessions(
  params: SessionListParams = {}
): Promise<SessionListResponse> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") query.append(k, String(v));
  });
  const res = await authFetch(`${API_BASE}/api/sessions?${query}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "获取会话列表失败");
  }
  return res.json();
}

export interface SessionMessage {
  id: number;
  role: "interviewer" | "candidate";
  content: string;
  stage: string;
  created_at: string | null;
}

export interface SessionDetail {
  session: {
    id: number;
    resume_id: number;
    candidate_name: string;
    position: string;
    status: string;
    current_stage: string;
    created_at: string | null;
    ended_at: string | null;
  };
  messages: SessionMessage[];
  report: {
    overall_score: number;
    report_json: Record<string, unknown> | null;
    created_at: string | null;
  } | null;
}

export async function fetchSessionDetail(
  sessionId: number
): Promise<SessionDetail> {
  const res = await authFetch(`${API_BASE}/api/sessions/${sessionId}/detail`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "获取会话详情失败");
  }
  return res.json();
}

// ========== 管理后台 ==========

export interface AdminStats {
  total_sessions: number;
  total_resumes: number;
  active_sessions: number;
  completed_sessions: number;
  total_messages: number;
  total_reports: number;
  total_users: number;
  avg_score: number | null;
  recent_sessions: Array<{
    id: number;
    candidate_name: string;
    position: string;
    status: string;
    current_stage: string;
    created_at: string | null;
  }>;
  position_distribution: Record<string, number>;
  daily_sessions: Array<{ date: string; count: number }>;
}

export async function fetchAdminStats(): Promise<AdminStats> {
  const res = await authFetch(`${API_BASE}/api/admin/stats`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "获取统计数据失败");
  }
  return res.json();
}

export async function fetchAdminSessions(
  params: SessionListParams = {}
): Promise<SessionListResponse> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") query.append(k, String(v));
  });
  const res = await authFetch(`${API_BASE}/api/admin/sessions?${query}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "获取会话列表失败");
  }
  return res.json();
}

export async function fetchAdminSessionDetail(
  sessionId: number
): Promise<SessionDetail> {
  const res = await authFetch(`${API_BASE}/api/admin/sessions/${sessionId}/detail`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "获取会话详情失败");
  }
  return res.json();
}

export async function fetchAdminUsers(): Promise<{
  users: Array<{
    id: number;
    email: string;
    username: string;
    role: string;
    is_active: boolean;
    session_count: number;
    created_at: string | null;
  }>;
  total: number;
}> {
  const res = await authFetch(`${API_BASE}/api/admin/users`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "获取用户列表失败");
  }
  return res.json();
}

// ========== Enhanced API（仪表盘数据）==========

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchTokenUsage(sessionId: number): Promise<any> {
  const res = await authFetch(`${API_BASE}/api/enhanced/token-usage/${sessionId}`);
  if (!res.ok) return null;
  return res.json();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchEvaluation(sessionId: number): Promise<any> {
  const res = await authFetch(`${API_BASE}/api/enhanced/evaluation/${sessionId}`);
  if (!res.ok) return null;
  return res.json();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchInsights(sessionId: number): Promise<any> {
  const res = await authFetch(`${API_BASE}/api/enhanced/insights/${sessionId}`);
  if (!res.ok) return null;
  return res.json();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchPersonas(): Promise<any> {
  const res = await authFetch(`${API_BASE}/api/enhanced/personas`);
  if (!res.ok) return { personas: [], total: 0 };
  return res.json();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchSkills(): Promise<any> {
  const res = await authFetch(`${API_BASE}/api/enhanced/skills`);
  if (!res.ok) return { skills: [], total: 0 };
  return res.json();
}

// ========== 简历分析 ==========

export interface ResumeAnalysisSection {
  score: number;
  feedback: string;
  suggestions: string[];
}

export interface ResumeAnalysisResponse {
  resume_id: number;
  analysis_id: number;
  overall_score: number;
  sections: Record<string, ResumeAnalysisSection>;
  keyword_recommendations: string[];
  format_suggestions: string[];
  overall_feedback: string;
  target_position?: string;
  created_at?: string;
}

export async function analyzeResume(
  resumeId: number,
  targetPosition?: string
): Promise<ResumeAnalysisResponse> {
  const query = targetPosition
    ? `?target_position=${encodeURIComponent(targetPosition)}`
    : "";
  const res = await authFetch(
    `${API_BASE}/api/resume-analysis/analyze/${resumeId}${query}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "简历分析失败");
  }
  return res.json();
}

export async function fetchResumeAnalysis(
  resumeId: number
): Promise<ResumeAnalysisResponse | null> {
  const res = await authFetch(`${API_BASE}/api/resume-analysis/${resumeId}`);
  if (!res.ok) return null;
  return res.json();
}

// ========== 面试辅导 ==========

export interface QuestionCoaching {
  question: string;
  user_answer_summary: string;
  ideal_answer: string;
  gap_analysis: string;
  improvement_tips: string[];
  score: number;
}

export interface DimensionCoaching {
  current_score: number;
  target_score: number;
  roadmap: string[];
  resources: string[];
}

export interface CoachingResponse {
  session_id: number;
  coaching_id: number;
  question_coaching: QuestionCoaching[];
  dimension_coaching: Record<string, DimensionCoaching>;
  overall_improvement_plan: {
    short_term: string[];
    medium_term: string[];
    long_term: string[];
  };
  created_at?: string;
}

export async function generateCoaching(
  sessionId: number
): Promise<CoachingResponse> {
  const res = await authFetch(
    `${API_BASE}/api/coaching/generate/${sessionId}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "辅导生成失败");
  }
  return res.json();
}

export async function fetchCoaching(
  sessionId: number
): Promise<CoachingResponse | null> {
  const res = await authFetch(`${API_BASE}/api/coaching/${sessionId}`);
  if (!res.ok) return null;
  return res.json();
}

// ========== 面试题库（公开，无需认证）==========

export interface KnowledgeCategory {
  id: string;
  name: string;
  icon: string;
  count: number;
}

export interface KnowledgeQuestion {
  id: string;
  title: string;
  difficulty: string;
  tags: string[];
  answer: string;
  key_points: string[];
}

export interface KnowledgeTip {
  id: string;
  title: string;
  category: string;
  content: string;
}

export async function fetchKnowledgeCategories(): Promise<{
  categories: KnowledgeCategory[];
}> {
  const res = await fetch(`${API_BASE}/api/knowledge/categories`);
  if (!res.ok) return { categories: [] };
  return res.json();
}

export async function fetchKnowledgeQuestions(
  category: string
): Promise<{ category: string; total: number; questions: KnowledgeQuestion[] }> {
  const res = await fetch(
    `${API_BASE}/api/knowledge/questions?category=${encodeURIComponent(category)}`
  );
  if (!res.ok) return { category, total: 0, questions: [] };
  return res.json();
}

export async function fetchKnowledgeTips(): Promise<{ tips: KnowledgeTip[] }> {
  const res = await fetch(`${API_BASE}/api/knowledge/tips`);
  if (!res.ok) return { tips: [] };
  return res.json();
}

export async function searchKnowledge(
  query: string,
  k: number = 5
): Promise<{ query: string; total: number; results: KnowledgeQuestion[] }> {
  const res = await fetch(
    `${API_BASE}/api/knowledge/search?q=${encodeURIComponent(query)}&k=${k}`
  );
  if (!res.ok) return { query, total: 0, results: [] };
  return res.json();
}
