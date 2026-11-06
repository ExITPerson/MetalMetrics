from itertools import chain

import requests
from cypher_cell import CypherCell
from config.settings import OKVED_PRIORITY_MAP, REGIONS_DICT, TOKEN, API_URL, OKVED_NOT_CLIENTS, OKVED_COLD_CLIENTS, \
    OKVED_WARM_CLIENTS


class ClientCHK:

    def __init__(self):
        self._token = CypherCell(TOKEN.encode())
        self.url = API_URL
        self.okveds = list(
            chain(
                OKVED_NOT_CLIENTS,
                OKVED_NOT_CLIENTS,
                OKVED_COLD_CLIENTS,
                OKVED_WARM_CLIENTS
            )
        )

    def _connect(self, okved, page):
        with self._token as cell:
            token = bytes(cell).decode()

        params = {
            'key': token,
            'by': 'okved',
            'obj': 'org',
            'query': okved,
            'active': 'True',
            'page': page,
        }

        response = requests.get(url=self.url, params=params)

        if response.status_code == 200:
            result = response.json()

            if result.get('meta', {}).get('status') == 'error':
                print(f"Ошибка API на странице {page}: {result['meta'].get('message')}")
                return None

            return result.get('data', {})

        return None

    def get_data(self):
        data = []

        for okved in self.okveds:
            page = 1
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
                            'region_name': REGIONS_DICT.get(company.get('РегионКод'))
                        })

                current_page = result.get('СтрТекущ', 1)
                total_pages = result.get('СтрВсего', 1)

                if current_page >= total_pages:
                    break

                page += 1

        return data
