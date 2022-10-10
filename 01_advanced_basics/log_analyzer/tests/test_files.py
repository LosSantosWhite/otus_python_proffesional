from datetime import datetime
import os
import pytest
from unittest import mock

from log_analyzer import find_last_log_file, file_processing, file_params

ABS_PATH_LOGS = os.path.join(os.path.abspath(__file__).rsplit('/', 1)[0], 'logs')

print(ABS_PATH_LOGS)

VALID_FILE = file_params(
    file_date=datetime(2017, 6, 30),
    path=os.path.join(ABS_PATH_LOGS, ".nginx-access-ui.log-20170630.gz"),
    extension="gz",
)

@pytest.mark.parametrize(
    "log_dir,result",
    [
        (ABS_PATH_LOGS, (VALID_FILE, "report-2017.06.30.html")),
    ],
)
def test_find_last_log_file(log_dir, result):
    assert find_last_log_file(log_dir) == result


@pytest.mark.parametrize(
    "config",
    [
        (
            {
                "log_dir": os.path.join(ABS_PATH_LOGS, "exceptions", "logs"),
                "report_dir": os.path.join("exceptions", "report_dir"),
            }
        ),
    ],
)
def test_file_processing_raises_exception(config):
    with pytest.raises(ValueError):
        file_processing(config)
