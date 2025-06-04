import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from bs4 import BeautifulSoup, NavigableString, Tag

CHROMEDRIVER_PATH = r"C:\Users\katya\webdrivers\chromedriver.exe"
BASE_URL = "https://www1.fips.ru/iiss/"

# Настраиваем один драйвер на модуль
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')
service = Service(executable_path=CHROMEDRIVER_PATH, log_path="NUL")
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 10)

def normalize_title(text: str) -> str:
    parts = re.split(r'([.!?])', text)
    out = []
    for i in range(0, len(parts), 2):
        s = parts[i].strip().lower()
        p = parts[i+1] if i+1 < len(parts) else ''
        if s:
            out.append(s.capitalize() + p)
    return ' '.join(out).strip()

def fetch_section(href: str, title_class: str) -> str:
    driver.get(BASE_URL + href)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    title_tag = soup.find('p', class_=title_class)
    if not title_tag:
        return '-'
    texts = []
    for sib in title_tag.find_next_siblings('p'):
        cls = sib.get('class') or []
        if any(c.startswith('Tit') for c in cls):
            break
        texts.append(sib.get_text(strip=True))
    return '\n'.join(texts) if texts else '-'

def fetch_holder(href: str) -> str:
    driver.get(BASE_URL + href)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    bib = soup.find('td', id='bibl')
    if not bib:
        return '-'
    for p in bib.find_all('p', recursive=False):
        txt = p.get_text(separator=' ', strip=True)
        if 'Заявитель' in txt or 'Патентообладатель' in txt:
            b = p.find('b')
            if not b:
                continue
            lines = [line.strip() for line in b.get_text(separator='\n').splitlines() if line.strip()]
            return '; '.join(lines)
    return '-'

def fetch_abstract(href: str) -> str:
    return fetch_section(href, title_class='TitAbs')

def fetch_claims(href: str) -> str:
    return fetch_section(href, title_class='TitCla')

def scrape_fips_data(keyword: str, date_from=None, date_to=None, retry: int = 2):
    records = []
    for attempt in range(retry + 1):
        try:
            driver.get(BASE_URL + "db.xhtml")
            time.sleep(2)
            # галочка «всё»
            wait.until(EC.element_to_be_clickable((By.ID,   "db-selection-form:j_idt74"))).click()
            wait.until(EC.element_to_be_clickable((By.NAME, "db-selection-form:j_idt92"))).click()
            wait.until(EC.element_to_be_clickable((By.NAME, "db-selection-form:j_idt90"))).click()

            fld = wait.until(EC.element_to_be_clickable((By.ID, "j_idt89")))
            fld.clear(); fld.send_keys(keyword)
            wait.until(EC.element_to_be_clickable((By.NAME, "j_idt92"))).click()
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            rows = soup.select('div.bgtable div.table a.tr')
            for row in rows:
                cells = row.select('div.td')
                if len(cells) < 5:
                    continue
                num      = cells[1].get_text(strip=True)
                raw_date = cells[2].get_text(strip=True).strip('()')
                try:
                    date = datetime.strptime(raw_date, '%d.%m.%Y').date()
                except ValueError:
                    date = None
                title = normalize_title(cells[4].get_text(strip=True))
                href  = row.get('href')
                if date:
                    if date_from and date < date_from: continue
                    if date_to   and date > date_to:   continue
                records.append({
                    'href':     href,
                    'number':   num,
                    'date':     date,
                    'title':    title,
                    'holder':   None,
                    'abstract': None
                })
            break
        except (TimeoutException, StaleElementReferenceException):
            if attempt < retry:
                time.sleep(1)
                continue
            break
    return records