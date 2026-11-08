from database.crud import add_entries, show_table
from database.db import create_table, create_db
from config.settings import COMPANY_COLUMNS
from src.chk.client_chk import client_chk
from utils.prepare import prepare_company_row

if __name__ == "__main__":
    create_db('metal_metrics')
    create_table(
        table_name='clients_chk',
        database='metal_metrics',
        columns=COMPANY_COLUMNS,
        order_by=['inn'],
        primary_key='inn',
        partition_by='toYYYYMM(parsed_at)',
        engine='ReplacingMergeTree(parsed_at)',
    )
    print("Таблица создана")
    companies = client_chk.get_data()
    print("Компании найдены")
    prepare_company = prepare_company_row(companies)
    print("Компании преобразованы")
    cols_to_insert = [
        name for name, dtype in COMPANY_COLUMNS.items()
        if 'DEFAULT' not in dtype.upper()
    ]
    add_entries('metal_metrics', 'clients_chk', columns=cols_to_insert, rows=prepare_company)

    result = show_table('metal_metrics', 'clients_chk', limit=10000)
    print(result)
    print(len(result))
