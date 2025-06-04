import requests
from collections import defaultdict
import re
from googletrans import Translator

LENS_API_TOKEN = "6x3bo53zNBAXq2HIyWoTvfC7xKYqaGV3dSvGu9qsp0oCL2jN7OCP"
translator = Translator()


def translate_to_russian(text):
    try:
        return translator.translate(text, src='en', dest='ru').text
    except Exception:
        return text


def translate_to_english(text):
    try:
        return translator.translate(text, src='ru', dest='en').text
    except Exception:
        return text


def get_patents_from_lens(keyword, year_start=None, year_end=None):
    # Переводим кириллицу в английский для поиска
    if any('\u0400' <= c <= '\u04FF' for c in keyword):
        keyword = translate_to_english(keyword)

    headers = {
        "Authorization": f"Bearer {LENS_API_TOKEN}",
        "Content-Type": "application/json"
    }

    terms = keyword.split()
    query_must = [{
        "query_string": {
            "query": " AND ".join(terms),  # "machine AND learning AND in AND physics"
            "fields": ["title", "abstract", "claims", "description"]
        }
    }]

    date_range = {}
    if year_start:
        date_range["gte"] = f"{year_start}-01-01"
    if year_end:
        date_range["lte"] = f"{year_end}-12-31"
    if date_range:
        query_must.append({"range": {"date_published": date_range}})

    body = {
        "query": {"bool": {"must": query_must}},
        "size": 50,
        "sort": [{"_score": "desc"}, {"date_published": "desc"}]
    }

    resp = requests.post(
        "https://api.lens.org/patent/search",
        headers=headers,
        json=body,
        timeout=15
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for patent in data.get('data', []):
        biblio = patent.get('biblio', {})
        lid = patent.get('lens_id', '')
        pub_date = patent.get('date_published') \
                   or biblio.get('publication_reference', {}).get('date', '')
        year = pub_date[:4]
        if year.isdigit():
            y = int(year)
            if year_start and y < int(year_start): continue
            if year_end and y > int(year_end):   continue

        # Заголовок (en → ru)
        title_en = next(
            (t['text'] for t in biblio.get('invention_title', []) if t.get('lang') == 'en'),
            ''
        )
        title = translate_to_russian(title_en) if title_en else 'Нет названия'

        # Реферат: пробуем abstract → claims
        # сначала пытаемся из abstract
        abstract_en = next(
            (a.get('text') for a in patent.get('abstract', [])
             if a.get('lang') == 'en' and a.get('text')),
            ''
        )
        if not abstract_en:
            # fallback в claims, но только если у элемента есть ключ 'text'
            abstract_en = next(
                (c.get('text') for c in patent.get('claims', [])
                 if c.get('lang') == 'en' and c.get('text')),
                ''
            )
        abstract = translate_to_russian(abstract_en) if abstract_en else 'Нет реферата'

        # Заявители — всегда переводим в русский
        apps = [
            x.get('extracted_name', {}).get('value', '')
            for x in biblio.get('parties', {}).get('applicants', [])
        ]
        applicants = ', '.join(filter(None, apps)).upper() or 'НЕТ ЗАЯВИТЕЛЕЙ'

        results.append({
            'title': title,
            'url': f'https://www.lens.org/lens/patent/{lid}',
            'pub_date': pub_date,
            'applicants': applicants,
            'abstract': abstract
        })

    return results, len(results)


def prepare_chart_data(patents):
    counts = defaultdict(int)
    for p in patents:
        y = p['pub_date'][:4]
        if y.isdigit(): counts[y] += 1
    years = sorted(counts);
    counts_data = [counts[y] for y in years]

    app_cnt = defaultdict(int)
    for p in patents:
        for a in p['applicants'].split(','):
            n = a.strip()
            if n: app_cnt[n] += 1
    top10 = sorted(app_cnt.items(), key=lambda x: x[1], reverse=True)[:10]
    names = [n for n, _ in top10];
    vals = [v for _, v in top10]


    stack = defaultdict(lambda: defaultdict(int))
    for p in patents:
        y = p['pub_date'][:4]
        for a in names:
            if a in p['applicants']:
                stack[y][a] += 1
    datasets = [
        {'label': a, 'data': [stack[y].get(a, 0) for y in years]}
        for a in names
    ]

    pie = {
        'labels': names,
        'values': vals
    }

    return {
        'years': {'labels': years, 'data': counts_data},
        'stacked_bar': {'labels': years, 'datasets': datasets},
        'pie': pie
    }


def search_lens(keyword, year_start=None, year_end=None):
    patents, total = get_patents_from_lens(keyword, year_start, year_end)
    charts = prepare_chart_data(patents)
    return {'patents': patents, 'total': total, 'charts': charts}
