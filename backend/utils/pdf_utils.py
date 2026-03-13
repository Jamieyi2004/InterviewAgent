"""
PDF 处理工具函数
"""

import pdfplumber
from pathlib import Path


def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    从 PDF 文件中提取纯文本

    Args:
        file_path: PDF 文件路径

    Returns:
        提取的文本内容
    """
    text_parts = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n".join(text_parts)
