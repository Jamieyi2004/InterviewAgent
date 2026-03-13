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
