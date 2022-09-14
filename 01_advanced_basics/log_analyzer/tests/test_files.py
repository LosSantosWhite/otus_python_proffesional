import datetime

import pytest
from log_analyzer import checking_log_file_ext, get_file_date, files_comparison


@pytest.mark.parametrize("file_name,result", [
    ('.nginx-access-ui.log-20170630.gz', True),
    ('.nginx-access-ui.log-201730.gz', None),
    ('nginx-access-ui.log-20170630.log', True),
    ('nginx-access-ui.log-20.log', None)

])
def test_checking_log_file_ext(file_name, result):
    assert checking_log_file_ext(file_name) == result


@pytest.mark.parametrize("file_name,report,result", [
    ('nginx-access-ui.log-20170630.log', False, '20170630'),
    ('report-2017.06.30.html', True, '2017.06.30'),
    ('report-2017.06.30.html', True, '2017.06.30'),
])
def test_get_file_date(file_name, report, result):
    assert get_file_date(file_name, report) == result


@pytest.mark.parametrize("file_1,file_2,result", [
    (datetime.datetime(2020, 10, 9), datetime.datetime(2020, 10, 10), True),
    (None, datetime.datetime(2020, 10, 10), True)
])
def test_files_comparison(file_1, file_2, result):
    assert files_comparison(file_1, file_2) == result


@pytest.mark.parametrize("file_1,file_2", [
    (datetime.datetime(2020, 10, 10), datetime.datetime(2020, 10, 10))
])
def test_files_comparison_exception(file_1, file_2):
    with pytest.raises(ValueError):
        assert files_comparison(file_1, file_2)