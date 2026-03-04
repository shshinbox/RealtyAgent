import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "RealtyAgent-server"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    log_dir = Path("logs/server")
    log_dir.mkdir(exist_ok=True)

    # 1. 터미널 핸들러 레벨 설정
    # LLM 프롬프트는 보통 DEBUG 레벨로 찍히므로, 터미널에서도 보고 싶다면 DEBUG로 변경해야 합니다.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # 기존 INFO에서 DEBUG로 변경

    console_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    file_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # ────────────────────────────────────────────────────────────
    # 2. LLM 프롬프트 로깅 활성화 (핵심 추가 부분)
    # ────────────────────────────────────────────────────────────
    # LlamaIndex 내부 로거를 가져와서 설정을 맞춥니다.
    llama_logger = logging.getLogger("llama_index")
    llama_logger.setLevel(logging.DEBUG)
    llama_logger.addHandler(console_handler)  # 터미널에 찍기
    llama_logger.addHandler(file_handler)  # 파일에도 저장하기
    # ────────────────────────────────────────────────────────────

    return logger


logger = setup_logger()
