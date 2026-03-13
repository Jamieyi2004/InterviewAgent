"""统一后端日志配置：控制台 + 文件，带时间与级别。"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> None:
  """配置根 logger：INFO 级别，控制台 + 滚动文件。"""
  log_dir = Path(__file__).resolve().parent / "logs"
  log_dir.mkdir(exist_ok=True)
  log_file = log_dir / "backend.log"

  fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
  datefmt = "%Y-%m-%d %H:%M:%S"

  root = logging.getLogger()
  root.setLevel(logging.INFO)

  # 避免重复添加 handler
  if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
    return

  console = logging.StreamHandler()
  console.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))

  file_handler = RotatingFileHandler(
      log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
  )
  file_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))

  root.addHandler(console)
  root.addHandler(file_handler)
