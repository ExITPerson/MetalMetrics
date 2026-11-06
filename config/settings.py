import os
from dotenv import load_dotenv

load_dotenv()

# --- БД ---
HOST_DB = os.getenv('HOST_DB')
PORT_DB = os.getenv('PORT_DB')
USER_DB = os.getenv('USER_DB')
PASSWORD_DB = os.getenv('PASSWORD_DB')

# --- Создание таблиц ---
COMPANY_TABLE_NAME = os.getenv('COMPANY_TABLE_NAME')