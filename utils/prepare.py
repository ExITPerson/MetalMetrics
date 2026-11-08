from datetime import datetime, date


def _to_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(value, '%d.%m.%Y').date()
        except (ValueError, TypeError):
            return None


def _to_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def prepare_company_row(data: list[dict]) -> list[tuple]:
    return [
        (
            str(item.get('inn') or ''),
            str(item.get('name') or ''),
            str(item.get('status') or ''),
            _to_int(item.get('priority')),
            _to_date(item.get('date_registration')),
            _to_date(item.get('date_liquidation')),
            str(item.get('okved_id') or ''),
            str(item.get('okved_name') or ''),
            str(item.get('region_id') or ''),
            str(item.get('region_name') or ''),
        )
        for item in data
    ]