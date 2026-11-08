from config.logging_config import setup_logging
from database.db import client


logger = setup_logging('db.log')


def add_entries(db_name: str, table_name: str, columns: list[str], rows: list[tuple]) -> int:
    """ Вставляет строки в ClickHouse с явным указанием колонок """
    if not rows:
        logger.warning("add_entries: пустой список rows")
        return 0

    cols_sql = ', '.join(columns)
    query = f'INSERT INTO {db_name}.{table_name} ({cols_sql}) VALUES'

    client.execute(query, rows)
    logger.info(
        "add_entries: вставлено %d строк в %s.%s (колонок: %d)",
        len(rows), db_name, table_name, len(columns),
    )
    return len(rows)

def show_table(db_name: str, table_name: str, limit: int = 10) -> list[dict]:
    """ Показывает первые несколько строк таблицы """
    query = f'SELECT * FROM {db_name}.{table_name} LIMIT {limit}'
    result = client.execute(query, with_column_types=True)

    rows, columns = result
    col_names = [c[0] for c in columns]

    data = [dict(zip(col_names, row)) for row in rows]
    logger.info("show_table: %s.%s — %d строк", db_name, table_name, len(data))
    return data