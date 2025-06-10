import time
import re
from collections import Counter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

BASE_URL = 'https://patents.google.com'

def _create_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    return driver

def scrape_patents(driver, query, year_from=None, year_to=None):
    """
    Собирает URL патентов по запросу и (опционально) по годам.
    Рабочий селектор: state-modifier[data-result]
    """
    q = query.replace(' ', '+')
    url = f"{BASE_URL}/?q={q}&num=50&language=RUSSIAN"
    if year_from:
        url += f"&after={year_from}"
    if year_to:
        url += f"&before={year_to}"
    driver.get(url)
    time.sleep(2)

    elements = driver.find_elements(By.CSS_SELECTOR, "state-modifier[data-result]")
    urls = []
    for el in elements:
        data = el.get_attribute('data-result') or ''
        if not data:
            continue
        if data.startswith('http'):
            urls.append(data)
        else:
            urls.append(BASE_URL + '/' + data.lstrip('/'))
    return urls

def get_patent_details(driver, url):
    driver.get(url)
    time.sleep(1)

    def safe(selector):
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return ''

    title = safe('h1#title') or safe('h1.scroll-target.style-scope.patent-result')
    abstract = safe('div.abstract')
    filing_date = ''
    applicant = ''

    events = driver.find_elements(
        By.CSS_SELECTOR,
        'div.event.layout.horizontal.style-scope.application-timeline'
    )
    for ev in events:
        try:
            dt = ev.find_element(By.CSS_SELECTOR, 'div.filed').text.strip()
            sm = ev.find_element(By.CSS_SELECTOR, 'state-modifier[data-assignee]')
            assignee = sm.get_attribute('data-assignee').strip()
            filing_date, applicant = dt, assignee
            break
        except NoSuchElementException:
            continue

    return {
        'title': title,
        'abstract': abstract,
        'filing_date': filing_date,
        'applicant': applicant
    }

def scrape_google_data(query, year_from=None, year_to=None):
    """
    Возвращает:
      - search_url  — для ручного открытия,
      - patents     — список словарей {title,abstract,pub_date,applicants,url},
      - total       — число найденных URL,
      - charts      — данные для графиков.
    """
    driver = _create_driver()
    try:
        # 1) формируем ссылку точно так же, как в scrape_patents
        q = query.replace(' ', '+')
        search_url = f"{BASE_URL}/?q={q}&num=100"
        if year_from:
            search_url += f"&after={year_from}"
        if year_to:
            search_url += f"&before={year_to}"

        # 2) собираем URL
        urls = scrape_patents(driver, query, year_from, year_to)
        patents = []
        years = []
        applicants = []
        abstracts = []

        # 3) обходим каждый URL и вытаскиваем детали
        for url in urls:
            try:
                detail = get_patent_details(driver, url)
                patents.append({
                    'title': detail['title'],
                    'abstract': detail['abstract'],
                    'pub_date': detail['filing_date'],
                    'applicants': detail['applicant'],
                    'url': url
                })
                if detail['filing_date'] and len(detail['filing_date']) >= 4:
                    years.append(detail['filing_date'][:4])
                if detail['applicant']:
                    applicants.append(detail['applicant'])
                abstracts.append(detail['abstract'])
            except Exception:
                continue

        # 4) строим данные для графиков
        year_count = Counter(years)
        sorted_years = sorted(year_count)
        year_data = [year_count[y] for y in sorted_years]

        top_apps = Counter(applicants).most_common(15)
        app_labels = [a for a, _ in top_apps]
        app_data = [c for _, c in top_apps]

        stacked = {'labels': sorted_years, 'datasets': []}
        for app_label, _ in top_apps:
            counts = [
                sum(1 for p in patents
                    if p['pub_date'].startswith(year) and p['applicants'] == app_label)
                for year in sorted_years
            ]
            stacked['datasets'].append({'label': app_label, 'data': counts})

        charts = {
            'years': {'labels': sorted_years, 'data': year_data},
            'applicants': {'labels': app_labels, 'data': app_data},
            'stacked_bar': stacked,
            'word_cloud': word_cloud
        }

        return {
            'message': 'Поищите напрямую, если хотите:',
            'search_url': search_url,
            'patents': patents,
            'total': len(urls),
            'charts': charts
        }
    finally:
        driver.quit()
