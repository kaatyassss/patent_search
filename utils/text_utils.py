from datetime import date, datetime

def normalize_applicant(name: str) -> str:
    name = name.upper()
    for ch in ['"', "'", '«', '»', '“', '”', '‘', '’', '<', '>']:
        name = name.replace(ch, '')
    return name.strip()

def extract_field(item, *keys):
    for key in keys:
        if hasattr(item, key):
            val = getattr(item, key)
            if val:
                return val
        if isinstance(item, dict) and item.get(key):
            return item[key]
    return None

def extract_year(item):
    d = extract_field(item, 'pub_date', 'date', 'publication_date', 'pubDate')
    if isinstance(d, (datetime, date)):
        return str(d.year)
    if isinstance(d, str) and len(d) >= 4 and d[:4].isdigit():
        return d[:4]
    return None
