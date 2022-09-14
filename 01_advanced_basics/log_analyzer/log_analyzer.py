#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import configparser
import datetime
import json
import logging
import re
import gzip
from collections import namedtuple, defaultdict
from string import Template
import os

log_format = (
    "$remote_addr  $remote_user $http_x_real_ip [$time_local] $request $status $body_bytes_sent "
    '$http_referer $http_user_agent $http_x_forwarded_for" $http_X_REQUEST_ID $http_X_RB_USER $request_time'
)

LOG_REQUEST_PATTERN = re.compile(r"^.+\[.+\] \"(.+)\" \d{3}.+ (\d+\.\d+)\n$")

TEMPLATE = os.path.join("template", "report.html")

DEFAULT_CONFIG = {
    "log_analyzer": {
        "REPORT_SIZE": 1000,
        "REPORT_DIR": "./reports",
        "LOG_DIR": "./logs",
        "ALLOWED_INVALID_PART": 0.2,
        "LOG_FILENAME": None,
        "LOGGING_LEVEL": "INFO",
    }
}

logger = logging.getLogger()

log_params = namedtuple("log_params", ["url", "time"])

log_stat = namedtuple(
    "log_stat",
    [
        "count",
        "count_perc",
        "time_perc",
        "time_sum",
        "time_avg",
        "time_max",
        "time_med",
    ],
)


def init_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("-fc", "--file-config", default=DEFAULT_CONFIG)
    args = parser.parse_args()
    config = configparser.ConfigParser()
    config.read("default_config.ini")
    config.read(args.file_config)

    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
        level="INFO",
    )
    return config


def checking_log_file_ext(file_name, report=False):
    """Проверка расширения файлов"""
    LOG_FILENAME_PATTERN = r"nginx-access-ui\.log-(\d{8})\.(gz|log)"
    REPORT_FILENAME_PATTERN = r"report-\d{4}.\d{2}.\d{2}.html"
    if re.search(
        REPORT_FILENAME_PATTERN if report else LOG_FILENAME_PATTERN, file_name
    ):
        return True


def get_file_date(file_name, report=False):
    """Возвращает дату файла из названия"""
    if report:
        return re.findall(r"\d{4}.\d{2}.\d{2}", file_name)[0]
    return re.findall(r"\d{8}", file_name)[0]


def get_last_file(files_paths, report=False):
    """Возвращает самый 'свежий файл' из директории логов/отчетов"""
    last_file = None
    file_params = namedtuple("file_params", ["file_date", "path", "extension"])
    for file in files_paths:
        _file_date = get_file_date(file.name, report)
        _, file_extension = os.path.splitext(file.name)
        file_date = datetime.datetime.strptime(
            _file_date, "%Y.%m.%d" if report else "%Y%m%d"
        )
        if not last_file:
            last_file = file_params(file_date, file, file_extension)
        else:
            if file_date > last_file.file_date:
                last_file = file_params(file_date, file, file_extension)
    return last_file


def get_file(dir, report=False):
    """Поиск файлов в директориях названия которых соответствуют паттерну"""
    files = [
        file
        for file in os.scandir(dir)
        if checking_log_file_ext(file.name, report=report)
    ]
    if not files:
        raise FileNotFoundError(f"Didn't find any files in {dir}")
    return get_last_file(files, report)


def read_log_file(log_file):
    """Построчно yield'ит строки из файла"""
    open_file = {".gz": gzip.open, ".log": open}
    with open_file[log_file.extension](log_file.path, "rb") as file:
        for line in file:
            try:
                line = line.decode("utf-8")
                search = LOG_REQUEST_PATTERN.search(line)
                time = search.group(2)
                method, url, protocol = search.group(1).split()
                yield log_params(url, float(time))
            except ValueError:
                yield None


def files_comparison(log_file_date, report_file_date):
    """Сравнение дат файла логов и отчета"""
    try:
        if log_file_date == report_file_date:
            raise ValueError(
                f"Отчетный файл уже существует!"
            )
    except AttributeError:
        pass
    return True


def iterate_over_file(log_file, report_size, allowed_invalid_part):
    """Итерируемся по файлу"""
    total_line_count = 0

    count_valid = 0
    count_error = 0

    time_valid = 0.0
    statistics = defaultdict(list)

    for line in read_log_file(log_file):
        if total_line_count < int(report_size):
            total_line_count += 1
            if not line:
                count_error += 1
                continue
            count_valid += 1
            time_valid += line.time
            statistics[line.url].append(line.time)
        else:
            break
    if count_error / count_valid > float(allowed_invalid_part):
        raise ValueError("Слишком много ошибок в файле.")
    return normalize_report(statistics, total_line_count, count_valid, time_valid)


def median(time):
    """Выбор медианы"""
    return sorted(time)[(len(time) // 2)]


def normalize_report(statistics, total_line_count, count_valid, time_valid):
    stats = []
    for url, times in statistics.items():
        stat_for_url = log_stat(
            count=len(times),
            count_perc=f"{100 * count_valid / total_line_count}%",
            time_perc=f"{100 * sum(times) / time_valid}%",
            time_sum=sum(times),
            time_avg=sum(times) / len(times),
            time_max=max(times),
            time_med=median(times),
        )
        stats.append(stat_for_url)
    return stats


def create_template(stats: log_stat):
    with open(TEMPLATE, "rb") as file:
        template = Template(file.read().decode("utf-8"))
    return template.safe_substitute(
        table_json=json.dumps([line._asdict() for line in stats])
    )


def write_template(path, stats):
    with open(path, "w") as file:
        file.write(create_template(stats))


def main():
    config = init_config()
    report_dir = config.get("log_analyzer", "REPORT_DIR")
    if not os.path.exists(report_dir):
        os.mkdir(report_dir)
    try:
        report_file = get_file(report_dir, report=True)
        logger.info(
            f"Последний отчетный файл найден в {os.path.join(config.get('log_analyzer', 'REPORT_DIR'), report_file.path)}"
        )
    except FileNotFoundError:
        report_file = None
        logger.info(
            f"Не найден ни один отчетный файл в {config.get('log_analyzer', 'REPORT_DIR')}"
        )
    log_file = get_file(config.get("log_analyzer", "LOG_DIR"))
    logger.info(
        f'Лог-файл найден в {os.path.join(config.get("log_analyzer", "LOG_DIR"), log_file.path.name)}'
    )
    report_file_name = f"report-{log_file.file_date.strftime('%Y.%m.%d')}.html"
    logger.info(f"Создаю отчетный файл report-{report_file_name}.html")
    if files_comparison(log_file.file_date, report_file.file_date):
        stats = iterate_over_file(
            log_file,
            config.get("log_analyzer", "REPORT_SIZE"),
            config.get("log_analyzer", "ALLOWED_INVALID_PART"),
        )

        write_template(
            os.path.join(config.get("log_analyzer", "REPORT_DIR"), report_file_name),
            stats,
        )
        logger.info("Выполнено")


if __name__ == "__main__":
    main()
