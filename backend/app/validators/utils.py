from datetime import datetime


DATE_FORMAT = "%Y-%m-%d" # YYYY-MM-DD


def parse_date_str(date_str: str) -> datetime:
    return datetime.strptime(date_str, DATE_FORMAT)


def validate_date_str(date_str: str, field_name: str) -> str | None:
    try:
        parse_date_str(date_str)
    except ValueError:
        return f"{field_name} value \"{date_str!r}\" does not match format \"YYYY-MM-DD\"."