"""Test using `UploadCOUNTERReports`."""
########## Passing 2024-12-19 ##########

import pytest
import logging
from pathlib import Path
from random import choice
from pandas.testing import assert_frame_equal

# `conftest.py` fixtures are imported automatically
from conftest import mock_FileStorage_object  # Direct import is required because it isn't a fixture
from nolcat.app import *
from nolcat.upload_COUNTER_reports import UploadCOUNTERReports
from nolcat.app import *

log = logging.getLogger(__name__)


#Section: Test Uploading Single Workbook
@pytest.fixture
def sample_COUNTER_report_workbook(create_COUNTERData_workbook_iterdir_list):
    """Creates a mock_FileStorage_object object enclosed in a list for use in testing the `UploadCOUNTERReports` class.
    
    The `UploadCOUNTERReports` constructor takes a list of Werkzeug FileStorage object(s), but when this fixture uses those objects, a `File is not a zip file` error is raised. The `mock_FileStorage_object` class was devised as a way around that issue.

    Yields:
        list: a mock_FileStorage_object object enclosed in a list simulating a single file selected in a MultipleFileField field
    """
    yield [mock_FileStorage_object(choice(create_COUNTERData_workbook_iterdir_list))]


def test_create_dataframe_from_single_workbook(sample_COUNTER_report_workbook, workbooks_and_relations):
    """Tests transforming an Excel workbook with tabular COUNTER data into a dataframe."""
    COUNTERData_relation = workbooks_and_relations[sample_COUNTER_report_workbook[0].filename]
    df, data_not_in_df = UploadCOUNTERReports(sample_COUNTER_report_workbook).create_dataframe()
    assert isinstance(data_not_in_df, list)
    assert_frame_equal(df, COUNTERData_relation[df.columns.tolist()], check_names=False)  # `check_names` argument allows test to pass if indexes don't have the same name


#Section: Test Uploading All Workbooks
@pytest.fixture
def sample_COUNTER_report_workbooks(create_COUNTERData_workbook_iterdir_list):
    """Creates a list of mock_FileStorage_object object(s) for use in testing the `UploadCOUNTERReports` class.
    
    The `UploadCOUNTERReports` constructor takes a list of Werkzeug FileStorage object(s), but when this fixture uses those objects, a `File is not a zip file` error is raised. The `mock_FileStorage_object` class was devised as a way around that issue.

    Yields:
        list: a list of mock_FileStorage_object object(s) simulating multiple files selected in a MultipleFileField field
    """
    fixture = []
    for workbook in create_COUNTERData_workbook_iterdir_list:
        fixture.append(mock_FileStorage_object(workbook))
    yield fixture


@pytest.mark.slow
def test_create_dataframe(sample_COUNTER_report_workbooks, COUNTERData_relation):
    """Tests transforming multiple Excel workbooks with tabular COUNTER data into a single dataframe.
    
    The order of the possible delimiters means the existence of the delimiter characters in a string field is tested, but the possibility of a delimiter character as the first character in a string field isn't covered by this test.
    """
    df, data_not_in_df = UploadCOUNTERReports(sample_COUNTER_report_workbooks).create_dataframe()
    assert isinstance(data_not_in_df, list)
    assert_frame_equal(df, COUNTERData_relation[df.columns.tolist()], check_names=False)  # `check_names` argument allows test to pass if indexes don't have the same name
