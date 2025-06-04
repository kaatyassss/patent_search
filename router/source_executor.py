import logging

logger = logging.getLogger(__name__)

def run_source(raw, results, messages, name: str, key: str, func, *args):
    """
    Универсальная функция для вызова адаптеров источников данных.

    Параметры:
      raw      - объект SearchResult для сбора всех записей по источникам
      results  - словарь для хранения результатов по ключам источников
      messages - список сообщений об ошибках или отсутствии данных
      name     - человекочитаемое имя источника (для логов и сообщений)
      key      - ключ в словаре results, куда сохранять данные
      func     - функция-адаптер, возвращающая список записей
      args     - позиционные аргументы для func
    """
    try:
        # Логируем начало вызова адаптера
        logger.info(f"Calling {name} adapter...")

        # Выполняем функцию-адаптер и получаем список патентов
        patents = func(*args)

        # Подсчитываем количество полученных записей
        cnt = len(patents)
        logger.info(f"{name} → {cnt}")

        if cnt:
            # Сохраняем записи в общий список raw.sources
            raw.sources.append((name, patents))

            # Сохраняем патенты в словарь результатов:
            # если значение по ключу — dict, кладём его в подполе 'patents', иначе перезаписываем
            if isinstance(results[key], dict):
                results[key]['patents'] = patents
            else:
                results[key] = patents
        else:
            # Если записей нет, добавляем сообщение для интерфейса
            messages.append(f"{name} не дал результатов")
    except Exception:
        # Логируем полную трассировку ошибки и добавляем сообщение об ошибке
        logger.exception(f"Ошибка {name}")
        messages.append(f"{name} не дал результатов")