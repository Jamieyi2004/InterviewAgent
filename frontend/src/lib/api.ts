/**
 * 后端 API 调用封装
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

/**
 * 上传简历 PDF
 */
export async function uploadResume(file: File): Promise<{
  resume_id: number;
  filename: string;
  parsed_data: Record<string, unknown>;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/resume/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "简历上传失败");
  }

  return res.json();
}

/**
 * 创建面试会话
 */
export async function startInterview(
  resumeId: number,
  position: string
): Promise<{ session_id: number; message: string }> {
  const res = await fetch(`${API_BASE}/api/interview/start`, {
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

/**
 * 结束面试
 */
export async function endInterview(
  sessionId: number
): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/interview/end/${sessionId}`, {
    method: "POST",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "结束面试失败");
  }

  return res.json();
}

/**
 * 生成评估报告
 */
export async function generateReport(
  sessionId: number
): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/report/generate/${sessionId}`, {
    method: "POST",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "报告生成失败");
  }

  return res.json();
}

/**
 * 获取评估报告
 */
export async function fetchReport(
  sessionId: number
): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/report/${sessionId}`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "获取报告失败");
  }

  return res.json();
}

/**
 * 获取当前算法题目
 */
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
  const res = await fetch(`${API_BASE}/api/interview/problem/${sessionId}`);

  if (!res.ok) {
    return null;
  }

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
  const res = await fetch(`${API_BASE}/api/sessions?${query}`);
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
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/detail`);
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
  const res = await fetch(`${API_BASE}/api/admin/stats`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "获取统计数据失败");
  }
  return res.json();
}

// ========== Enhanced API（仪表盘数据）==========

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchTokenUsage(sessionId: number): Promise<any> {
  const res = await fetch(`${API_BASE}/api/enhanced/token-usage/${sessionId}`);
  if (!res.ok) return null;
  return res.json();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchEvaluation(sessionId: number): Promise<any> {
  const res = await fetch(`${API_BASE}/api/enhanced/evaluation/${sessionId}`);
  if (!res.ok) return null;
  return res.json();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchInsights(sessionId: number): Promise<any> {
  const res = await fetch(`${API_BASE}/api/enhanced/insights/${sessionId}`);
  if (!res.ok) return null;
  return res.json();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchPersonas(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/enhanced/personas`);
  if (!res.ok) return { personas: [], total: 0 };
  return res.json();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchSkills(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/enhanced/skills`);
  if (!res.ok) return { skills: [], total: 0 };
  return res.json();
}
