from database.db import create_table, create_db
from config.settings import COMPANY_TABLE_COLUMNS

if __name__ == "__main__":
    create_db('metal_metrics')
    create_table(
        table_name='deals',
        database='metal_metrics',
        columns=COMPANY_TABLE_COLUMNS,
        order_by=['category_id', 'stage_semantic_id', 'assigned_by_id', 'id'],
        partition_by='toYYYYMM(date_create)',
    )