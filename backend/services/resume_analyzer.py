"""
简历分析服务 —— 调用 LLM 分析简历，生成优化建议
"""

import json
import logging

from sqlalchemy.orm import Session

from agent.chains import call_llm_json
from agent.prompt_templates import RESUME_ANALYSIS_PROMPT
from models.resume import Resume
from models.resume_analysis import ResumeAnalysis

logger = logging.getLogger(__name__)


async def analyze_resume(
    resume_id: int, db: Session, target_position: str = "通用岗位"
) -> dict:
    """
    分析简历并生成优化建议

    流程：
    1. 加载简历原始文本
    2. 调用 LLM 生成结构化分析
    3. 存入数据库

    Returns:
        分析结果字典
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise ValueError(f"简历不存在：resume_id={resume_id}")

    raw_text = resume.raw_text or ""
    if not raw_text.strip():
        raise ValueError("简历文本为空，无法分析")

    # 截取前 6000 字符避免超长
    text_for_analysis = raw_text[:6000]

    prompt = RESUME_ANALYSIS_PROMPT.format(
        target_position=target_position,
        resume_text=text_for_analysis,
    )

    logger.info("开始分析简历 resume_id=%d, 岗位=%s", resume_id, target_position)

    analysis_data = await call_llm_json(
        system_prompt="你是一位资深HR顾问和简历优化专家，只输出JSON格式。",
        user_message=prompt,
    )

    # 存入数据库
    record = ResumeAnalysis(
        resume_id=resume_id,
        overall_score=analysis_data.get("overall_score", 0),
        analysis_json=json.dumps(analysis_data, ensure_ascii=False),
        target_position=target_position,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info("简历分析完成 resume_id=%d, score=%d", resume_id, record.overall_score)

    return {
        "resume_id": resume_id,
        "analysis_id": record.id,
        **analysis_data,
    }


def get_resume_analysis(resume_id: int, db: Session) -> dict | None:
    """查询已有的简历分析结果"""
    record = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.resume_id == resume_id)
        .order_by(ResumeAnalysis.id.desc())
        .first()
    )
    if not record:
        return None

    analysis_data = json.loads(record.analysis_json)
    return {
        "resume_id": resume_id,
        "analysis_id": record.id,
        "target_position": record.target_position,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        **analysis_data,
    }
