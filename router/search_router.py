# router/search_router.py

from datetime import datetime
import logging

from adapters.google_module import scrape_google_data
from adapters.fips_module import scrape_fips_data, fetch_holder, fetch_abstract, fetch_claims
from adapters.lens_module import search_lens
from router.source_executor import run_source

logger = logging.getLogger(__name__)

class SearchResult:
    def __init__(self):
        # [(название_источника, список записей)]
        self.sources = []
        # плоский список всех записей
        self.all_records = []

def _parse_year(s: str):
    """Преобразует строку '2020' в datetime.date(2020,1,1) или None."""
    if s and s.isdigit():
        return datetime.strptime(s, '%Y').date()
    return None

def execute_fips(keyword, year_start, year_end):
    """Гарантированный код обработки ФИПС."""
    try:
        recs = scrape_fips_data(
            keyword,
            date_from=_parse_year(year_start),
            date_to=_parse_year(year_end)
        )
        for r in recs:
            # Добавляем информацию о держателе
            r['holder'] = (fetch_holder(r['href']) or '—').upper()
            # Берём abstract, если пустой — claims
            abs_txt = fetch_abstract(r['href'])
            clm_txt = fetch_claims(r['href'])
            r['abstract'] = abs_txt if abs_txt != '-' else clm_txt
        cnt = len(recs)
        logger.info("FIPS: %d", cnt)
        return recs
    except Exception:
        logger.exception("Ошибка FIPS")
        return []

def search_router(request):
    """
    Обрабатывает HTTP-запрос, читает параметры формы,
    вызывает адаптеры через run_source,
    нормализует результаты и собирает их для шаблона.
    """
    # Чтение параметров формы
    keyword    = request.form.get('keyword', '').strip()    if request.method == 'POST' else ''
    year_start = request.form.get('year_start', '').strip() if request.method == 'POST' else ''
    year_end   = request.form.get('year_end', '').strip()   if request.method == 'POST' else ''
    use_google = 'source_google' in request.form
    use_fips   = 'source_fips'   in request.form
    use_lens   = 'source_lens'   in request.form

    logger.info("Flags: use_google=%s, use_fips=%s, use_lens=%s", use_google, use_fips, use_lens)

    # Инициализация контейнеров
    raw = SearchResult()
    messages = []
    results = {
        'google': {'patents': []},
        'fips':   [],
        'lens':   {'patents': []}
    }

    if request.method == 'POST':
        # Google Patents
        if use_google:
            run_source(
                raw, results, messages,
                'Патенты Google',               # name
                'google',                       # key
                lambda k, ys, ye: scrape_google_data(k, ys, ye).get('patents', []),
                keyword, year_start, year_end   # func args
            )

        # FIPS
        if use_fips:
            run_source(
                raw, results, messages,
                'ФИПС',
                'fips',
                execute_fips,
                keyword, year_start, year_end
            )

        # Lens.org
        if use_lens:
            run_source(
                raw, results, messages,
                'Lens.org',
                'lens',
                lambda k, ys, ye: search_lens(k, ys, ye).get('patents', []),
                keyword, year_start, year_end
            )

        # Объединяем все записи для последующей обработки
        for _, lst in raw.sources:
            raw.all_records.extend(lst)
        logger.info("Total all_records → %d", len(raw.all_records))

    return keyword, year_start, year_end, raw, results, messages
