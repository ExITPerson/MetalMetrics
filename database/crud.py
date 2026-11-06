from database.db import client


def add_entries(db_name: str, table_name: str, rows: tuple) -> client:
    """ Добавление записей в БД """
    return client.execute(
        f'INSERT INTO {db_name}.{table_name} VALUES',
        rows
    )