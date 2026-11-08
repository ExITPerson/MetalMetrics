import functools
import logging
import logging.handlers
import os
from pathlib import Path


LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')


def setup_logging(
        log_file: str = 'app.log',
        level: str = LOG_LEVEL,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5
):
    root = logging.getLogger()
    root.setLevel(level)

    for handler in root.handlers[:]:
        root.removeHandler(handler)

    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
    )

    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_DIR / log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    root.addHandler(file_handler)

    logger = logging.getLogger("metalmetrics")
    return logger
