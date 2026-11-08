import json
import os
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

# --- БД ---
HOST_DB = os.getenv('HOST_DB')
PORT_DB = os.getenv('PORT_DB')
USER_DB = os.getenv('USER_DB')
PASSWORD_DB = os.getenv('PASSWORD_DB')

# --- Создание таблиц ---
COMPANY_TABLE_NAME = os.getenv('COMPANY_TABLE_NAME')
COMPANY_TABLE_COLUMNS = {}

# --- CHK ---
API_URL = os.getenv('API_URL')
TOKEN = os.getenv('TOKEN')
CHK_PROXIES = os.getenv('CHK_PROXIES')
CHK_PROXIES_RAW = json.loads(CHK_PROXIES)
CHK_SEARCH_URL=os.getenv('CHK_SEARCH_URL')
CHK_COMPANY_URL=os.getenv('CHK_COMPANY_URL')

# --- Регионы ---
with open('data/region.json', 'r', encoding='utf-8') as f:
    REGIONS_DICT = json.load(f)


""" Разделение ОКВЭДов по приоритетности """
# --- Высокий приоритет ---
OKVED_HOT_CLIENTS = [
    "25.62",        # Механическая обработка металла (резка, пробивка, гибка)
    "25.6",         # Родительский код (25.61 + 25.62)
    "25.61",        # Обработка металлов и нанесение покрытий
    "24.33",        # Холодная штамповка/гибка профилей
]
# --- Средний приоритет ---
OKVED_WARM_CLIENTS = [
    "25.50.1",      # Ковка, прессование, штамповка
    "25.50.2",      # Штамповка/профилирование листового металла
    "25.1",         # Строительные металлоконструкции
    "25.2",         # Ёмкости, резервуары
    "25.4",         # Инструмент
    "25.5",         # Крепёж
    "25.9",         # Прочие металлоизделия
    "25.11",        # Строительные конструкции
    "25.12",        # Двери, окна
    "25.21.1",      # Радиаторы
    "25.29",        # Котлы
    "25.30.2",      # Столовые приборы
    "25.94",        # Крепёж
    "25.99",        # Прочие металлоизделия
    "25.99.2",      # Прочие металлоизделия
    "25.99.21",     # Прочие металлоизделия
    "25.99.22",     # Прочие металлоизделия
    "25.99.24",     # Прочие металлоизделия
    "25.99.29",     # Прочие металлоизделия
]
# --- Низкий приоритет ---
OKVED_COLD_CLIENTS = [
    "29.1",         # Машины и оборудование общего назначения
    "29.2",         # Прочие машины и оборудование
    "28.25",        # Холодильное/вентиляционное оборудование
    "28.25.1",      # Холодильное оборудование
    "28.25.2",      # Вентиляционное оборудование
]
# --- Под вопросом / конкуренты ---
OKVED_NOT_CLIENTS = [
    # Производители станков (конкуренты)
    "28.41", "28.41.1", "28.41.2",
    "28.49", "28.49.1", "28.49.11", "28.49.12",
    # Металлургия, прокат (поставщики сырья)
    "24.1", "24.2", "24.3",
    # Автомобилестроение (закрытое производство)
    "29.10.3", "29.10.5",
    "29.20.2", "29.20.4", "29.20.5",
]

OKVED_PRIORITY_MAP = {
    **{okved: 0 for okved in OKVED_HOT_CLIENTS},   # Приоритет 0: Горячие
    **{okved: 1 for okved in OKVED_WARM_CLIENTS},  # Приоритет 1: Тёплые
    **{okved: 2 for okved in OKVED_COLD_CLIENTS},  # Приоритет 2: Холодные
    **{okved: 4 for okved in OKVED_NOT_CLIENTS},   # Приоритет 4: Не клиенты
}

COMPANY_COLUMNS = {
    'inn':               'String',
    'name':              'String',
    'status':            'String',
    'priority':          'Nullable(UInt8)',
    'date_registration': 'Nullable(Date)',
    'date_liquidation':  'Nullable(Date)',
    'okved_id':          'LowCardinality(String)',
    'okved_name':        'String',
    'region_id':         'LowCardinality(String)',
    'region_name':       'String',
    'parsed_at':         'DateTime DEFAULT now()',
}
