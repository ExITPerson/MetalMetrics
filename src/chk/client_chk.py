import requests
from cypher_cell import CypherCell
from config.settings import OKVED_PRIORITY_MAP, REGIONS_DICT, TOKEN, API_URL

okveds = [
    '25.1', '25.5', '25.2', '25.4', '25.6', '25.9', '25.12', '25.30.2', '25.50.1',
    '25.21.1', '25.29', '25.61', '25.94', '25.99', '25.99.2', '25.99.21', '25.99.22',
    '25.99.29', '25.11', '24.3', '24.33', '28.25', '28.25.1', '28.25.2', '28.41',
    '28.41.2', '28.49', '28.49.1', '28.49.12', '28.49.11', '29.10.5', '29.10.3',
    '29.20.2', '29.20.4', '29.20.5', '28.41.1', '25.99.24', '25.50.2', '29.2',
]

class ClientCHK:

    def __init__(self):
        self._token = CypherCell(TOKEN.encode())
        self.url = API_URL
        self.okveds = okveds

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
        okved_list = ["28.41.1"]

        for okved in okved_list:
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
