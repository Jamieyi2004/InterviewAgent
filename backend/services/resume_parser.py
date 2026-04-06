"""
简历解析服务 —— PDF文本提取（不再调用 LLM 结构化解析，面试官 LLM 可直接理解原始文本）
"""

from pathlib import Path

from sqlalchemy.orm import Session

from models.resume import Resume
from utils.pdf_utils import extract_text_from_pdf

# 简历摘要最多取前 N 字符给面试官 LLM
MAX_RESUME_CHARS_FOR_SUMMARY = 4000


async def parse_resume(file_path: Path, filename: str, db: Session, user_id: int = None) -> dict:
    """
    解析简历（简化流程）：
    1. 从 PDF 提取文本
    2. 直接存入数据库（不再调用 LLM 结构化解析）

    Args:
        file_path: 上传的 PDF 文件路径
        filename: 原始文件名
        db: 数据库 session

    Returns:
        {"resume_id": int, "parsed_data": None}
    """
    # 1. 提取 PDF 文本
    raw_text = extract_text_from_pdf(file_path)
    if not raw_text.strip():
        raise ValueError("无法从 PDF 中提取到文本内容，请检查文件是否为扫描件")

    # 2. 直接存入数据库，parsed_json 存空对象（兼容旧字段）
    resume = Resume(
        filename=filename,
        raw_text=raw_text,
        parsed_json="{}",
        user_id=user_id,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "resume_id": resume.id,
        "parsed_data": None,
    }


def get_resume_summary(resume: Resume) -> str:
    """
    从简历获取摘要文本（直接用原始文本，截取前 N 字符）

    Args:
        resume: 简历数据库对象

    Returns:
        简历摘要字符串
    """
    raw_text = resume.raw_text or ""
    if len(raw_text) > MAX_RESUME_CHARS_FOR_SUMMARY:
        return raw_text[:MAX_RESUME_CHARS_FOR_SUMMARY] + "\n\n(简历内容过长，仅展示前部分)"
    return raw_text
