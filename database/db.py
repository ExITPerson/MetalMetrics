from clickhouse_driver import Client
from dotenv import load_dotenv

from config.settings import HOST_DB, PORT_DB, USER_DB, PASSWORD_DB

load_dotenv()

client = Client(
    host=HOST_DB,
    port=int(PORT_DB),
    user=USER_DB,
    password=PASSWORD_DB,
)

def create_db(db_name: str) -> client:
    """ Функция для создания БД """
    return client.execute(f'CREATE DATABASE IF NOT EXISTS {db_name}')

def create_table(
        table_name: str,
        database: str,
        columns: dict[str, str],
        order_by: str | list[str],
        engine: str = 'MergeTree()',
        partition_by: str | None = None,
        primary_key: str | None = None
) -> None:
    """
    Функция для создания таблицы в БД
    :param table_name: Имя таблицы
    :param database: Имя БД для создания таблицы в ней
    :param columns: Параметры необходимых колонок в формате dict[str, str]
    :param order_by: Обязательный параметр при MergeTree() для сортировки
    :param engine: Движок таблицы
    :param partition_by: Параметр для разбивки (Например, по датам: toYYYYMM(---Название колонки---)
    :param primary_key: Узкий параметр для индексации
    """
    columns_sql = ',\n'.join(f'{name} {dtype}' for name, dtype in columns.items())
    orderby_sql = ', '.join(order_by) if isinstance(order_by, (list, tuple)) else order_by

    command = [f'CREATE TABLE IF NOT EXISTS {database}.{table_name} (\n {columns_sql}\n)']
    command.append(f'ENGINE = {engine}')

    if partition_by:
        command.append(f'PARTITION BY {partition_by}')
    if primary_key:
        command.append(f'PRIMARY KEY ({primary_key})')
    command.append(f'ORDER BY ({orderby_sql})')

    total = '\n'.join(command)
    client.execute(total)
