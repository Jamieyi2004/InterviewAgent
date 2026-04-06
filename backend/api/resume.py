"""
简历上传 API
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from config import UPLOAD_DIR
from models.database import get_db
from models.schemas import ResumeUploadResponse
from models.user import User
from services.resume_parser import parse_resume

router = APIRouter(prefix="/api/resume", tags=["简历管理"])


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(..., description="简历PDF文件"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    上传并解析简历

    - 接收 PDF 文件
    - 提取文本内容
    - 返回解析结果
    """
    # 校验文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式文件")

    # 保存文件到本地
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        result = await parse_resume(file_path, file.filename, db, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"简历解析失败：{str(e)}")

    return ResumeUploadResponse(
        resume_id=result["resume_id"],
        filename=file.filename,
        parsed_data=result["parsed_data"] or {},
    )
