#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
from asyncio.log import logger
from cmath import log
import configparser
import datetime
import json
import logging
import re
import gzip
from collections import namedtuple, defaultdict
from string import Template
import os
from statistics import median

log_format = (
    "$remote_addr  $remote_user $http_x_real_ip [$time_local] $request $status $body_bytes_sent "
    '$http_referer $http_user_agent $http_x_forwarded_for" $http_X_REQUEST_ID $http_X_RB_USER $request_time'
)

LOG_REQUEST_PATTERN = re.compile(r"^.+\[.+\] \"(.+)\" \d{3}.+ (\d+\.\d+)\n$")

TEMPLATE = os.path.join("template", "report.html")

DEFAULT_CONFIG = {
    "report_size": 1000,
    "report_dir": "./reports",
    "log_dir": "./logs",
    "allowed_invalid_part": 0.2,
    "log_filename": None,
    "logging_level": "INFO",
}


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

file_params = namedtuple("file_params", ["file_date", "path", "extension"])

def init_logging(config):
    logger = logging.basicConfig(
        filename=config.get('log_filename'),
        level=config.get('logging_level')
    )
    return logger

def find_last_log_file(log_dir):
    last_log_file = None
    LOG_FILENAME_PATTERN = r"nginx-access-ui\.log-(\d{8})\.(gz|log)"

    for file in os.listdir(log_dir):
        if not re.search(LOG_FILENAME_PATTERN, file):
            continue
        _date = re.findall(r"\d{8}", file)[0]

        file_date = datetime.datetime.strptime(str(_date), "%Y%m%d")

        file_extensinsion = file.rsplit(".", 1)[-1]
        current_file = file_params(
            file_date, os.path.join(log_dir, file), file_extensinsion
        )
        if last_log_file:
            if last_log_file.file_date < current_file.file_date:
                last_log_file = current_file
        else:
            last_log_file = current_file
    if last_log_file:
        report_file_date = last_log_file.file_date.strftime("%Y.%m.%d")
        report_filename = f"report-{report_file_date}.html"

        return last_log_file, report_filename
    else:
        raise ValueError(f"Не найден файл логов в дерриктории {log_dir}")


def read_log_file(log_file):
    """Построчно yield'ит строки из файла"""
    open_file = {"gz": gzip.open, "log": open}
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


def render_template(path, stats):
    with open(TEMPLATE, "rb") as file:
        template = Template(file.read().decode("utf-8"))

    with open(path, "w") as file:
        file.write(
            template.safe_substitute(table_json=json.dumps([line for line in stats]))
        )


def init_config():
    args = argparse.ArgumentParser()
    args.add_argument("-fc", "--file_config", default="default_config.ini")
    args = args.parse_args()
    if not os.path.exists(args.file_config):
        raise FileNotFoundError("Конфигурационный файл не найден")
    config = configparser.ConfigParser()
    config.read(args.file_config)

    return config._sections["log_analyzer"]


def file_processing(config):
    log_filename, report_filename = find_last_log_file(config["log_dir"])
    if os.path.exists(os.path.join(config["report_dir"], report_filename)):
        raise ValueError("Отчетный файл уже существует")
    stats = iterate_over_file(
        log_filename, config["report_size"], config["allowed_invalid_part"]
    )
    render_template(os.path.join(config["report_dir"], report_filename), stats=stats)


def main():
    config = init_config()
    config = DEFAULT_CONFIG | config

    logger = init_logging()
    logger.info(f"Начинаю обрабатывать файл с кофинфигурацией {config}")
    file_processing(config)


if __name__ == "__main__":
    main()
