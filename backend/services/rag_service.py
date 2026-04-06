"""
面试题库 RAG 检索服务

基于 ChromaDB 向量库 + DashScope Embedding，为面试出题和评估提供检索增强。
"""

# ChromaDB 需要 sqlite3 >= 3.35.0，系统版本过低时用 pysqlite3 替代
try:
    import pysqlite3
    import sys
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import json
import threading
from typing import List, Dict

import chromadb
from loguru import logger

from config import LLM_API_KEY, LLM_BASE_URL


# ---- 岗位到题库分类映射 ----
POSITION_CATEGORY_MAP: Dict[str, List[str]] = {
    "Java后端开发工程师": ["java", "system_design", "algorithm"],
    "前端开发工程师": ["frontend", "algorithm"],
    "Python开发工程师": ["python", "system_design", "algorithm"],
    "全栈开发工程师": ["java", "frontend", "python", "system_design"],
    "数据分析师": ["python", "algorithm"],
    "算法工程师": ["python", "algorithm"],
}


class DashScopeEmbedding:
    """DashScope text-embedding-v3 封装（OpenAI 兼容接口）"""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.model = "text-embedding-v3"
        self._available = None  # 缓存可用性检查结果

    @property
    def available(self) -> bool:
        """检查 DashScope embedding 是否可用（只检查一次）"""
        if self._available is None:
            try:
                resp = self.client.embeddings.create(model=self.model, input=["测试"])
                self._available = len(resp.data) > 0 and len(resp.data[0].embedding) > 0
                if self._available:
                    logger.info(f"DashScope embedding 可用，维度: {len(resp.data[0].embedding)}")
            except Exception as e:
                logger.warning(f"DashScope embedding 不可用: {e}，将使用 ChromaDB 内置 embedding")
                self._available = False
        return self._available

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本嵌入向量（DashScope 限制每批 <=6 条）"""
        if not self.available:
            return []
        try:
            all_embeddings = []
            for i in range(0, len(texts), 6):
                batch = texts[i:i + 6]
                resp = self.client.embeddings.create(model=self.model, input=batch)
                all_embeddings.extend([item.embedding for item in resp.data])
            return all_embeddings
        except Exception as e:
            logger.warning(f"DashScope embedding 批量调用失败: {e}")
            return []


class KnowledgeRAGService:
    """面试题库 RAG 检索服务（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        import os
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="interview_questions",
            metadata={"hnsw:space": "cosine"},
        )
        self.embedder = DashScopeEmbedding()
        # 标记导入时使用的 embedding 类型，确保查询时一致
        self._uses_dashscope = False
        logger.info(f"ChromaDB 初始化完成，路径: {db_path}")

    @classmethod
    def get_instance(cls) -> "KnowledgeRAGService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def init_knowledge_base(self, force: bool = False) -> int:
        """
        从 knowledge.py 的题库数据导入向量库（幂等）

        Returns: 导入的题目数量
        """
        from api.knowledge import QUESTIONS

        # 检查是否已导入
        existing = self.collection.count()
        if existing > 0 and not force:
            logger.info(f"题库已导入 ({existing} 条)，跳过")
            # 检测已有数据的 embedding 维度来判断类型
            self._detect_embedding_type()
            return existing

        # force 模式：清空重建
        if force and existing > 0:
            self.client.delete_collection("interview_questions")
            self.collection = self.client.get_or_create_collection(
                name="interview_questions",
                metadata={"hnsw:space": "cosine"},
            )

        ids = []
        documents = []
        metadatas = []

        for category, questions in QUESTIONS.items():
            for q in questions:
                doc_id = q["id"]
                # 用于嵌入的文本：标题 + 标签 + 答案
                doc_text = f"{q['title']} {' '.join(q.get('tags', []))} {q['answer']}"
                metadata = {
                    "category": category,
                    "difficulty": q.get("difficulty", "中等"),
                    "title": q["title"],
                    "answer": q["answer"],
                    "key_points": json.dumps(q.get("key_points", []), ensure_ascii=False),
                    "tags": json.dumps(q.get("tags", []), ensure_ascii=False),
                }
                ids.append(doc_id)
                documents.append(doc_text)
                metadatas.append(metadata)

        # 尝试用 DashScope embedding
        embeddings = self.embedder.embed(documents)

        if embeddings and len(embeddings) == len(documents):
            self.collection.add(
                ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings,
            )
            self._uses_dashscope = True
            logger.info("题库使用 DashScope embedding 导入")
        else:
            # fallback: ChromaDB 内置 embedding (all-MiniLM-L6-v2)
            self.collection.add(
                ids=ids, documents=documents, metadatas=metadatas,
            )
            self._uses_dashscope = False
            logger.info("题库使用 ChromaDB 内置 embedding 导入")

        count = self.collection.count()
        logger.info(f"题库导入完成，共 {count} 道题")
        return count

    def _detect_embedding_type(self):
        """检测已有数据使用的 embedding 维度，推断类型"""
        try:
            sample = self.collection.peek(limit=1)
            if sample and sample.get("embeddings") and len(sample["embeddings"]) > 0:
                dim = len(sample["embeddings"][0])
                # DashScope text-embedding-v3 = 1024 维, all-MiniLM-L6-v2 = 384 维
                self._uses_dashscope = dim > 512
                logger.info(f"检测到已有 embedding 维度: {dim}，{'DashScope' if self._uses_dashscope else '内置'}")
        except Exception:
            self._uses_dashscope = False

    def search_questions(
        self,
        query: str,
        position: str = "",
        k: int = 3,
    ) -> List[Dict]:
        """
        检索与 query 相关的面试题

        Args:
            query: 搜索查询（自然语言）
            position: 岗位名称（可选，用于分类过滤）
            k: 返回数量

        Returns:
            [{title, answer, key_points, difficulty, category, tags}]
        """
        if self.collection.count() == 0:
            return []

        n_results = min(k, self.collection.count())
        query_params: Dict = {"n_results": n_results}

        # 岗位过滤
        categories = POSITION_CATEGORY_MAP.get(position)
        if categories:
            query_params["where"] = {"category": {"$in": categories}}

        # 使用与导入时一致的 embedding 方式
        if self._uses_dashscope:
            query_embedding = self.embedder.embed([query])
            if query_embedding:
                query_params["query_embeddings"] = query_embedding
            else:
                query_params["query_texts"] = [query]
        else:
            query_params["query_texts"] = [query]

        try:
            results = self.collection.query(**query_params)
        except Exception as e:
            logger.warning(f"RAG 检索失败: {e}")
            return []

        # 解析结果
        items = []
        if results and results["metadatas"]:
            for meta in results["metadatas"][0]:
                items.append({
                    "title": meta.get("title", ""),
                    "answer": meta.get("answer", ""),
                    "key_points": json.loads(meta.get("key_points", "[]")),
                    "difficulty": meta.get("difficulty", ""),
                    "category": meta.get("category", ""),
                    "tags": json.loads(meta.get("tags", "[]")),
                })

        return items

    def search_reference_answer(self, question: str, k: int = 2) -> List[Dict]:
        """根据面试官提出的问题，检索参考答案（用于评估对照）"""
        return self.search_questions(query=question, k=k)
