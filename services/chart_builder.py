import json
import plotly
import plotly.graph_objs as go
from collections import Counter
from _plotly_utils.colors import qualitative

from utils.text_utils import normalize_applicant, extract_year

def build_charts(search_result):
    """
    Принимает SearchResult с полями:
      - .all_records — плоский список словарей; каждый словарь должен содержать хотя бы
          ключи 'applicants' или 'holder' и 'pub_date' (или аналог)
      - .sources     — список (имя_источника, список_записей) для табличного вывода (не затрагивается здесь)
    Возвращает три JSON-строки (graph1JSON, graph2JSON, graph3JSON) для Plotly.
    """

    # 1) Собираем пары (applicant, year) из всех записей
    app_year_pairs = []
    for rec in search_result.all_records:
        raw = rec.get('applicants') or rec.get('holder') or ''
        name = normalize_applicant(raw)
        year = extract_year(rec)
        if not year:
            continue
        app_year_pairs.append((name, year))

    # 2) График 1 — количество патентов по годам
    years = [year for _, year in app_year_pairs]
    year_counts = Counter(years)
    sorted_years = sorted(year_counts)
    counts = [year_counts[y] for y in sorted_years]

    fig1 = go.Figure([go.Bar(x=sorted_years, y=counts)])
    fig1.update_layout(
        title="Патенты по годам",
        xaxis_title="Год",
        yaxis_title="Количество",
        autosize=True,
        margin=dict(t=50, b=80, l=50, r=50)
    )

    # 3) График 2 — stacked bar по топ-10 заявителям
    applicants = [app for app, _ in app_year_pairs]
    app_counts = Counter(applicants)
    top_apps = [app for app, _ in app_counts.most_common(10)]

    traces = []
    colors = qualitative.Plotly
    for i, app in enumerate(top_apps):
        data = [
            sum(1 for a, y in app_year_pairs if a == app and y == yy)
            for yy in sorted_years
        ]
        bar = go.Bar(x=sorted_years, y=data, name=app)
        bar.marker.color = colors[i % len(colors)]
        traces.append(bar)

    fig2 = go.Figure(traces)
    fig2.update_layout(
        barmode='stack',
        title="Заявители по годам",
        xaxis_title="Год",
        yaxis_title="Кол-во патентов",
        showlegend=False,
        autosize=True,
        margin=dict(t=50, b=80, l=50, r=50)
    )

    # 4) График 3 — круговая диаграмма топ-10 заявителей
    pie_vals = [app_counts[app] for app in top_apps]
    fig3 = go.Figure([go.Pie(labels=top_apps, values=pie_vals, showlegend=False)])
    fig3.update_layout(
        title="Топ заявителей",
        autosize=True,
        margin=dict(t=50, b=80, l=50, r=50)
    )

    # 5) Сериализация в JSON для передачи в шаблон
    graph1JSON = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)
    graph2JSON = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
    graph3JSON = json.dumps(fig3, cls=plotly.utils.PlotlyJSONEncoder)

    return graph1JSON, graph2JSON, graph3JSON
