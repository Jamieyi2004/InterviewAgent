"""
评估报告 API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db
from services.report_generator import generate_report, get_report

router = APIRouter(prefix="/api/report", tags=["评估报告"])


@router.post("/generate/{session_id}")
async def create_report(session_id: int, db: Session = Depends(get_db)):
    """
    生成面试评估报告

    - 收集面试对话历史
    - 调用 LLM 生成多维度评估
    - 返回报告数据
    """
    try:
        result = await generate_report(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败：{str(e)}")

    return result


@router.get("/{session_id}")
async def fetch_report(session_id: int, db: Session = Depends(get_db)):
    """
    获取已生成的评估报告
    """
    report = get_report(session_id, db)
    if not report:
        raise HTTPException(status_code=404, detail="报告未找到，请先生成报告")
    return report
