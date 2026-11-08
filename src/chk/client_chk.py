import logging
from itertools import chain

import requests
from cypher_cell import CypherCell

from config.logging_config import setup_logging
from config.settings import (
    OKVED_PRIORITY_MAP,
    REGIONS_DICT,
    TOKEN,
    API_URL,
    OKVED_NOT_CLIENTS,
    OKVED_COLD_CLIENTS,
    OKVED_WARM_CLIENTS,
)
from utils.logging_decorators import log_calls

logger = setup_logging('client_chk.log')


class ClientCHK:
    """ Клиент для API: выгружает компании по ОКВЭД """

    def __init__(self):
        self._token = CypherCell(TOKEN.encode())
        self.url = API_URL
        self.okveds = list(
            chain(
                OKVED_NOT_CLIENTS,
                OKVED_NOT_CLIENTS,
                OKVED_COLD_CLIENTS,
                OKVED_WARM_CLIENTS,
            )
        )
        logger.info("ClientCHK: инициализирован с %d ОКВЭД", len(self.okveds))

    @log_calls(logger=logger, level=logging.DEBUG, log_result=False)
    def _connect(self, okved: str, page: int) -> dict | None:
        """ Запрос к API: одна страница для одного ОКВЭД """
        with self._token as cell:
            token = bytes(cell).decode()

        params = {
            'key': token,
            'by': 'okved',
            'obj': 'org',
            'query': okved,
            # 'active': 'True',
            'page': page,
        }

        try:
            response = requests.get(url=self.url, params=params, timeout=30)
        except requests.RequestException:
            logger.exception("_connect: ошибка запроса (okved=%s, page=%d)", okved, page)
            return None

        if response.status_code == 200:
            result = response.json()

            if result.get('meta', {}).get('status') == 'error':
                msg = result['meta'].get('message')
                logger.warning(
                    "_connect: ошибка API (okved=%s, page=%d): %s",
                    okved, page, msg,
                )
                return None

            return result.get('data', {})

        logger.warning(
            "_connect: HTTP %d (okved=%s, page=%d)",
            response.status_code, okved, page,
        )
        return None

    @log_calls(logger=logger, level=logging.INFO, log_result=False)
    def get_data(self) -> list[dict]:
        """ Выгружает все компании по всем ОКВЭД (с пагинацией) """
        data = []

        for okved in self.okveds:
            page = 1
            okved_count = 0

            while True:
                result = self._connect(okved, page)

                if not result:
                    break

                companies = result.get('Записи', [])

                if not companies:
                    break

                for company in companies:
                    if company.get('Статус') != 'Не действует':
                        data.append({
                            'priority': OKVED_PRIORITY_MAP.get(okved),
                            'name': company.get('НаимСокр'),
                            'inn': company.get('ИНН'),
                            'status': company.get('Статус'),
                            'date_registration': company.get('ДатаРег'),
                            'date_liquidation': company.get('ДатаЛикв', None),
                            'okved_id': okved,
                            'okved_name': company.get('ОКВЭД'),
                            'region_id': company.get('РегионКод'),
                            'region_name': REGIONS_DICT.get(company.get('РегионКод')),
                        })
                        okved_count += 1

                current_page = result.get('СтрТекущ', 1)
                total_pages = result.get('СтрВсего', 1)

                if current_page >= total_pages:
                    break

                page += 1

            logger.info(
                "get_data: ОКВЭД %s — %d компаний, страниц: %d",
                okved, okved_count, page,
            )

        logger.info("get_data: всего собрано %d компаний", len(data))
        return data

client_chk = ClientCHK()