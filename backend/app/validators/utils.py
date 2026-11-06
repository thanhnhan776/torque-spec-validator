from datetime import date, datetime
import re

DATE_FORMAT = "%Y-%m-%d"  # YYYY-MM-DD


def parse_date_str(date_str: str) -> datetime:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date_str):
        raise ValueError("Date must use YYYY-MM-DD format")
    return datetime.strptime(date_str, DATE_FORMAT)


def parsed_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return parse_date_str(value).date()
    except ValueError:
        return None


def validate_date_str(date_str: str, field_name: str) -> str | None:
    try:
        parse_date_str(date_str)
    except ValueError:
        return f'{field_name} value "{date_str!r}" does not match format "YYYY-MM-DD".'
