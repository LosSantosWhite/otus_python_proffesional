from datetime import datetime
import os
import pytest
from unittest import mock

from log_analyzer import find_last_log_file, file_processing, file_params

valid_file = file_params(
    file_date=datetime(2017, 6, 30),
    path=os.path.join("tests", "logs", ".nginx-access-ui.log-20170630.gz"),
    extension="gz",
)
invalid_file = file_params(
    file_date=datetime(2017, 6, 30),
    path=os.path.join(
        "tests", "exceptions", "logs", ".nginx-access-ui.log-20170630.gz"
    ),
    extension="gz",
)


@pytest.mark.parametrize(
    "log_dir,result",
    [
        (os.path.join("tests", "logs"), (valid_file, "report-2017.06.30.html")),
    ],
)
def test_find_last_log_file(log_dir, result):
    assert find_last_log_file(log_dir) == result


@pytest.mark.parametrize(
    "config",
    [
        (
            {
                "log_dir": os.path.join("tests", "logs", "exceptions", "logs"),
                "report_dir": os.path.join("tests", "logs", "exceptions", "report_dir"),
            }
        ),
    ],
)
def test_file_processing_raises_exception(config):
    with pytest.raises(ValueError):
        file_processing(config)
