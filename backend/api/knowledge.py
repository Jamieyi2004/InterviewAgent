"""
面试题库与技巧 API —— 数据从 data/knowledge_data.json 加载
"""

import json
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/knowledge", tags=["面试题库"])

# ---- 加载题库数据 ----

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "knowledge_data.json"

with open(_DATA_FILE, encoding="utf-8") as _f:
    _DATA = json.load(_f)

CATEGORIES = _DATA["categories"]
QUESTIONS = _DATA["questions"]
TIPS = _DATA["tips"]


@router.get("/categories")
def get_categories():
    """获取题库分类列表"""
    return {"categories": CATEGORIES}


@router.get("/questions")
def get_questions(
    category: str = Query("java", description="分类 ID"),
):
    """获取指定分类的面试题目"""
    questions = QUESTIONS.get(category, [])
    return {
        "category": category,
        "total": len(questions),
        "questions": questions,
    }


@router.get("/tips")
def get_tips():
    """获取面试技巧列表"""
    return {"tips": TIPS}


@router.get("/search")
def search_knowledge(
    q: str = Query(..., description="搜索关键词（自然语言）"),
    k: int = Query(5, ge=1, le=20, description="返回数量"),
):
    """语义搜索面试题（基于 RAG 向量检索）"""
    from services.rag_service import KnowledgeRAGService
    try:
        rag = KnowledgeRAGService.get_instance()
        results = rag.search_questions(q, k=k)
        return {"query": q, "total": len(results), "results": results}
    except Exception as e:
        return {"query": q, "total": 0, "results": [], "error": str(e)}
