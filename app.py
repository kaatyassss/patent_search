# app.py

from flask import Flask, render_template, request
import time, logging

from _plotly_utils.colors import qualitative
from router.search_router import search_router
from services.chart_builder import build_charts
from utils.text_utils import normalize_applicant

app = Flask(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    start_request = time.time()
    logger.info("=== Новый запрос ===")

    # 1. Поиск + нормализация
    # функция возвращает 6 значений (включая results)
    keyword, year_start, year_end, search_result, results, messages = search_router(request)

    # 2. Построение графиков
    graph1JSON, graph2JSON, graph3JSON = build_charts(search_result)

    # 3. Собираем топ-10 заявителей для легенды
    from collections import Counter
    apps = [
        normalize_applicant(rec.get('applicants') or rec.get('holder') or '')
        for rec in search_result.all_records
    ]
    top_apps = [app for app, _ in Counter(apps).most_common(10)]
    # из палитры Plotly берём столько цветов, сколько заявителей
    legend_pairs = list(zip(qualitative.Plotly, top_apps))

    total_time = time.time() - start_request
    logger.info(f"Запрос завершён за {total_time:.3f}s")

    return render_template(
        'index.html',
        keyword=keyword,
        year_start=year_start,
        year_end=year_end,
        results=results,
        sources=search_result.sources,
        messages=messages,
        graph1JSON=graph1JSON,
        graph2JSON=graph2JSON,
        graph3JSON=graph3JSON,
        legend_pairs=legend_pairs
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)