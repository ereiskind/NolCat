"""Tests the methods in StatisticsSources."""
########## Passing 2024-12-19 ##########

import pytest
import logging
import json
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from random import choice
import re
import pandas as pd
from pandas.testing import assert_frame_equal
from dateutil.relativedelta import relativedelta  # dateutil is a pandas dependency, so it doesn't need to be in requirements.txt

# `conftest.py` fixtures are imported automatically
from conftest import match_direct_SUSHI_harvest_result
from conftest import COUNTER_reports_offered_by_statistics_source
from nolcat.app import *
from nolcat.models import *
from nolcat.statements import *

log = logging.getLogger(__name__)


#Section: Introductory Fixtures
@pytest.fixture(scope='module')
def current_month_like_most_recent_month_with_usage():
    """Creates `begin_date` and `end_date` SUSHI parameter values representing the current month.

    Testing `StatisticsSources._check_if_data_in_database()` requires a month for which the `StatisticsSources_fixture` statistics source won't have SUSHI data loaded. The current month is guaranteed to meet this criteria, as that data isn't available.

    Yields:
        tuple: two datetime.date values, representing the first and last day of a month respectively
    """
    current_date = date.today()
    begin_date = current_date.replace(day=1)
    end_date = last_day_of_month(begin_date)
    log.info(f"`current_month_like_most_recent_month_with_usage()` yields `begin_date` {begin_date} (type {type(begin_date)}) and `end_date` {end_date} (type {type(end_date)}).")
    yield (begin_date, end_date)


@pytest.fixture(scope='module')
def StatisticsSources_fixture(engine, most_recent_month_with_usage):
    """A fixture simulating a `StatisticsSources` object containing the necessary data to make a real SUSHI call.
    
    The SUSHI API has no test values, so testing SUSHI calls requires using actual SUSHI credentials. This fixture creates a `StatisticsSources` object with mocked values in all fields except `statisticsSources_relation['Statistics_Source_Retrieval_Code']`, which uses a random value taken from the R5 SUSHI credentials file. Because the `_harvest_R5_SUSHI()` method includes a check preventing SUSHI calls to stats source/date combos already in the database, stats sources current with the available usage statistics are filtered out to prevent their use.

    Args:
        engine (sqlalchemy.engine.Engine): a SQLAlchemy engine
        most_recent_month_with_usage (tuple): the first and last days of the most recent month for which COUNTER data is available

    Yields:
        StatisticsSources: a StatisticsSources object connected to valid SUSHI data
    """
    # Cannot use `caplog` for `query_database()` due to scope mismatch
    retrieval_codes_as_interface_IDs = []  # The list of `StatisticsSources.statistics_source_retrieval_code` values from the JSON, which are labeled as `interface_id` in the JSON
    with open(PATH_TO_CREDENTIALS_FILE()) as JSON_file:
        SUSHI_data_file = json.load(JSON_file)
        for vendor in SUSHI_data_file:
            for statistics_source_dict in vendor['interface']:
                if "interface_id" in list(statistics_source_dict.keys()):
                        retrieval_codes_as_interface_IDs.append(statistics_source_dict['interface_id'])
    
    retrieval_codes = []
    for interface in retrieval_codes_as_interface_IDs:
        query_result = query_database(
            query=f"""
                SELECT COUNT(*)
                FROM statisticsSources
                JOIN COUNTERData ON statisticsSources.statistics_source_ID=COUNTERData.statistics_source_ID
                WHERE statisticsSources.statistics_source_retrieval_code={interface}
                AND COUNTERData.usage_date={most_recent_month_with_usage[0].strftime('%Y-%m-%d')};
            """,
            engine=engine,
        )
        if isinstance(query_result, str):
            pytest.skip(database_function_skip_statements(query_result, False))
        if not query_result.empty or not query_result.isnull().all().all():  # `empty` returns Boolean based on if the dataframe contains data elements; `isnull().all().all()` returns a Boolean based on a dataframe of Booleans based on if the value of the data element is null or not
            retrieval_codes.append(interface)
    
    fixture_retrieval_code = str(choice(retrieval_codes)).split(".")[0]  # String created is of a float (aka `n.0`), so the decimal and everything after it need to be removed
    statistics_source_name = query_database(  # With a placeholder name, `SUSHICallAndResponse._evaluate_individual_SUSHI_exception()`, which makes a StatisticsSource object from a record based on that record's `statistics_source_name` value, fails; the `choice()` function ensures the retrieval code chosen is in the test data
        query=f"SELECT statistics_source_name FROM statisticsSources WHERE statistics_source_retrieval_code={choice(['1', '2', '3'])}",
        engine=engine,
    )
    if isinstance(statistics_source_name, str):
        pytest.skip(database_function_skip_statements(statistics_source_name, False))
    yield_object = StatisticsSources(
        statistics_source_ID = 0,
        statistics_source_name = extract_value_from_single_value_df(statistics_source_name, False),
        statistics_source_retrieval_code = fixture_retrieval_code,
        vendor_ID = 0,
    )
    log.warning(fixture_variable_value_declaration_statement("StatisticsSources_fixture", yield_object))  # The level is `warning` so it always displays, ensuring the SUSHI credentials source can be determined in the event that the tests don't pass because of problems on the vendor side
    yield yield_object


#Section: Tests and Fixture for SUSHI Credentials
def test_fetch_SUSHI_information_for_API(StatisticsSources_fixture):
    """Test collecting SUSHI credentials based on a `StatisticsSources.statistics_source_retrieval_code` value and returning a value suitable for use in a API call."""
    credentials = StatisticsSources_fixture.fetch_SUSHI_information()
    assert isinstance(credentials, dict)
    assert re.fullmatch(r"https?://.*\.(\w{3}|\w{2,3}\.\w{2})(/.*)?/", credentials['URL'])


def test_fetch_SUSHI_information_for_display(StatisticsSources_fixture):
    """Test collecting SUSHI credentials based on a `StatisticsSources.statistics_source_retrieval_code` value and returning the credentials for user display."""
    # credentials = StatisticsSources_fixture.fetch_SUSHI_information(False)
    #ToDo: assert `credentials` is displaying credentials to the user
    pass


@pytest.fixture(scope='module')
def SUSHI_credentials_fixture(StatisticsSources_fixture):
    """A fixture returning the SUSHI credentials dictionary to avoid repeated callings of the `StatisticsSources.fetch_SUSHI_information()` method in later test functions.

    Args:
        StatisticsSources_fixture (StatisticsSources): a StatisticsSources object connected to valid SUSHI data
    
    Yields:
        dict: SUSHI credentials
    """
    yield StatisticsSources_fixture.fetch_SUSHI_information()


#Section: Fixture Listing Available Reports
@pytest.fixture(scope='module')
def reports_offered_by_StatisticsSource_fixture(StatisticsSources_fixture, SUSHI_credentials_fixture):
    """A fixture feeding a StatisticsSources object into the `COUNTER_reports_offered_by_statistics_source` function.

    Args:
        StatisticsSources_fixture (StatisticsSources): a StatisticsSources object connected to valid SUSHI data
        SUSHI_credentials_fixture (dict): a SUSHI credentials dictionary
    
    Yields:
        list: the uppercase abbreviation of all the customizable COUNTER R5 reports offered by the given statistics source
    """
    yield COUNTER_reports_offered_by_statistics_source(
        StatisticsSources_fixture.statistics_source_name,
        SUSHI_credentials_fixture['URL'],
        {k: v for (k, v) in SUSHI_credentials_fixture.items() if k != "URL"},
    )


def test_COUNTER_reports_offered_by_statistics_source(reports_offered_by_StatisticsSource_fixture):
    """Tests creating list of available reports from a `/reports` SUSHI call.
    
    This function's call of a class method from `nolcat.models` means it's in `tests.conftest`, which lacks its own test module. To best test this function, the test is placed immediately after the instantiation of a fixture that exists to call the function in a test module that randomly selects SUSHI credentials to use. Since the fixture is generated dynamically from a randomly designated source, it cannot be compared to a static value, and dynamically retrieving the data for comparison would effectively be comparing the same code in two places; instead, this test checks various aspects of the data that will be true in all cases.
    """
    assert isinstance(reports_offered_by_StatisticsSource_fixture, list)
    assert 1 <= len(reports_offered_by_StatisticsSource_fixture) <= 4
    for report in reports_offered_by_StatisticsSource_fixture:
        assert re.fullmatch(r"[PDTI]R", report)


#Section: Test SUSHI Harvesting Methods in Reverse Call Order
#Subsection: Test `StatisticsSources._check_if_data_in_database()`
def test_check_if_data_in_database_no(client, StatisticsSources_fixture, reports_offered_by_StatisticsSource_fixture, current_month_like_most_recent_month_with_usage):
    """Tests if a given date and statistics source combination has any usage in the database when there aren't any matches.
    
    This test uses the current month as the date; since the current month's data isn't available, it won't be in the database. 
    """
    with client:
        data_check = StatisticsSources_fixture._check_if_data_in_database(
            choice(reports_offered_by_StatisticsSource_fixture),
            current_month_like_most_recent_month_with_usage[0],
            current_month_like_most_recent_month_with_usage[1],
        )
    assert data_check is None


def test_check_if_data_in_database_yes(client, StatisticsSources_fixture, reports_offered_by_StatisticsSource_fixture, current_month_like_most_recent_month_with_usage, caplog):
    """Tests if a given date and statistics source combination has any usage in the database when there are matches.
    
    To be certain the date range includes dates for which the given `StatisticsSources.statistics_source_ID` value both does and doesn't have usage, the date range must span from the dates covered by the test data to the current month, for which no data is available. Additionally, the `StatisticsSources.statistics_source_ID` value in `StatisticsSources_fixture` must correspond to a source that has all four possible reports in the test data.
    """
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()`
    report = choice(reports_offered_by_StatisticsSource_fixture)
    last_month_with_usage_in_test_data = date(2020, 6, 1)
    with client:
        data_check = StatisticsSources_fixture._check_if_data_in_database(
            report,
            last_month_with_usage_in_test_data,
            current_month_like_most_recent_month_with_usage[1],
        )
    assert isinstance(data_check, list)
    assert date(2020, 6, 1) not in data_check
    assert current_month_like_most_recent_month_with_usage[0] in data_check


#Subsection: Test `StatisticsSources._harvest_single_report()`
@pytest.mark.dependency()
@pytest.mark.slow
def test_harvest_single_report(client, StatisticsSources_fixture, most_recent_month_with_usage, reports_offered_by_StatisticsSource_fixture, SUSHI_credentials_fixture, caplog):
    """Tests the method making the API call and turing the result into a dataframe."""
    caplog.set_level(logging.INFO, logger='nolcat.SUSHI_call_and_response')  # For `make_SUSHI_call()`
    caplog.set_level(logging.INFO, logger='nolcat.convert_JSON_dict_to_dataframe')  # For `create_dataframe()`
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `upload_file_to_S3_bucket()`
    begin_date = most_recent_month_with_usage[0] + relativedelta(months=-2)  # Using month before month in `test_harvest_R5_SUSHI_with_report_to_harvest()` to avoid being stopped by duplication check
    end_date = last_day_of_month(begin_date)
    with client:
        SUSHI_data_response, flash_message_list = StatisticsSources_fixture._harvest_single_report(
            choice(reports_offered_by_StatisticsSource_fixture),
            SUSHI_credentials_fixture['URL'],
            {k: v for (k, v) in SUSHI_credentials_fixture.items() if k != "URL"},
            begin_date,
            end_date,
            bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
        )
    if isinstance(SUSHI_data_response, str) and skip_test_due_to_SUSHI_error_regex().match(SUSHI_data_response):
        pytest.skip(database_function_skip_statements(SUSHI_data_response, SUSHI_error=True))
    elif isinstance(SUSHI_data_response, str) and reports_with_no_usage_regex().fullmatch(SUSHI_data_response):
        pytest.skip(database_function_skip_statements(SUSHI_data_response, no_data=True))
    assert isinstance(SUSHI_data_response, pd.core.frame.DataFrame)
    assert isinstance(flash_message_list, list)
    assert SUSHI_data_response['statistics_source_ID'].eq(StatisticsSources_fixture.statistics_source_ID).all()
    assert SUSHI_data_response['report_creation_date'].map(lambda dt: dt.strftime('%Y-%m-%d')).eq(datetime.now(timezone.utc).strftime('%Y-%m-%d')).all()  # Inconsistencies in timezones and UTC application among vendors mean time cannot be used to confirm the recency of an API call response


@pytest.mark.dependency(depends=['test_harvest_single_report'])
@pytest.mark.slow
def test_harvest_single_report_with_partial_date_range(client, StatisticsSources_fixture, reports_offered_by_StatisticsSource_fixture, SUSHI_credentials_fixture, caplog):
    """Tests the method making the API call and turing the result into a dataframe when the given date range includes dates for which the date and statistics source combination already has usage in the database.
    
    To be certain the date range includes dates for which the given `StatisticsSources.statistics_source_ID` value both does and doesn't have usage, the date range starts with the last month covered by the test data; for efficiency, the date range only goes another two months past that point.
    """
    caplog.set_level(logging.INFO, logger='nolcat.SUSHI_call_and_response')  # For `make_SUSHI_call()`
    caplog.set_level(logging.INFO, logger='nolcat.convert_JSON_dict_to_dataframe')  # For `create_dataframe()`
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `upload_file_to_S3_bucket()`
    with client:
        SUSHI_data_response, flash_message_list = StatisticsSources_fixture._harvest_single_report(
            choice(reports_offered_by_StatisticsSource_fixture),
            SUSHI_credentials_fixture['URL'],
            {k: v for (k, v) in SUSHI_credentials_fixture.items() if k != "URL"},
            date(2020, 6, 1),  # The last month with usage in the test data
            date(2020, 8, 1),
            bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
        )
    if isinstance(SUSHI_data_response, str) and skip_test_due_to_SUSHI_error_regex().match(SUSHI_data_response):
        pytest.skip(database_function_skip_statements(SUSHI_data_response, SUSHI_error=True))
    elif isinstance(SUSHI_data_response, str) and reports_with_no_usage_regex().fullmatch(SUSHI_data_response):
        pytest.skip(database_function_skip_statements(SUSHI_data_response, no_data=True))  # Many statistics source providers don't have usage going back this far
    assert isinstance(SUSHI_data_response, pd.core.frame.DataFrame)
    assert isinstance(flash_message_list, list)
    assert pd.concat([
        SUSHI_data_response['usage_date'].eq(pd.Timestamp(2020, 7, 1)),
        SUSHI_data_response['usage_date'].eq(pd.Timestamp(2020, 8, 1)),
    ], axis='columns').any(axis='columns').all()


#Subsection: Test `StatisticsSources._harvest_R5_SUSHI()`
@pytest.mark.dependency(depends=['test_harvest_single_report'])
@pytest.mark.slow
def test_harvest_R5_SUSHI(client, StatisticsSources_fixture, most_recent_month_with_usage, caplog):
    """Tests collecting all available R5 reports for a `StatisticsSources.statistics_source_retrieval_code` value and combining them into a single dataframe."""
    caplog.set_level(logging.INFO, logger='nolcat.SUSHI_call_and_response')  # For `make_SUSHI_call()`
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `upload_file_to_S3_bucket()` called in `SUSHICallAndResponse.make_SUSHI_call()` and `self._harvest_single_report()`
    caplog.set_level(logging.INFO, logger='nolcat.convert_JSON_dict_to_dataframe')  # For `create_dataframe()` called in `self._harvest_single_report()`
    with client:
        SUSHI_data_response, flash_message_list = StatisticsSources_fixture._harvest_R5_SUSHI(
            most_recent_month_with_usage[0],
            most_recent_month_with_usage[1],
            bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
        )
    assert isinstance(SUSHI_data_response, pd.core.frame.DataFrame)
    assert isinstance(flash_message_list, dict)
    assert SUSHI_data_response['statistics_source_ID'].eq(StatisticsSources_fixture.statistics_source_ID).all()
    assert SUSHI_data_response['report_creation_date'].map(lambda dt: dt.strftime('%Y-%m-%d')).eq(datetime.now(timezone.utc).strftime('%Y-%m-%d')).all()  # Inconsistencies in timezones and UTC application among vendors mean time cannot be used to confirm the recency of an API call response


@pytest.mark.dependency(depends=['test_harvest_single_report'])
@pytest.mark.slow
def test_harvest_R5_SUSHI_with_report_to_harvest(StatisticsSources_fixture, most_recent_month_with_usage, reports_offered_by_StatisticsSource_fixture, caplog):
    """Tests collecting a single R5 report for a `StatisticsSources.statistics_source_retrieval_code` value."""
    caplog.set_level(logging.INFO, logger='nolcat.SUSHI_call_and_response')  # For `make_SUSHI_call()`
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `upload_file_to_S3_bucket()` called in `SUSHICallAndResponse.make_SUSHI_call()` and `self._harvest_single_report()`
    caplog.set_level(logging.INFO, logger='nolcat.convert_JSON_dict_to_dataframe')  # For `create_dataframe()` called in `self._harvest_single_report()`
    begin_date = most_recent_month_with_usage[0] + relativedelta(months=-2)  # Using two months before `most_recent_month_with_usage` to avoid being stopped by duplication check
    end_date = last_day_of_month(begin_date)
    SUSHI_data_response, flash_message_list = StatisticsSources_fixture._harvest_R5_SUSHI(
        begin_date,
        end_date,
        choice(reports_offered_by_StatisticsSource_fixture),
        bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
    )
    assert isinstance(SUSHI_data_response, pd.core.frame.DataFrame)
    assert isinstance(flash_message_list, dict)
    assert SUSHI_data_response['statistics_source_ID'].eq(StatisticsSources_fixture.statistics_source_ID).all()
    assert SUSHI_data_response['report_creation_date'].map(lambda dt: dt.strftime('%Y-%m-%d')).eq(datetime.now(timezone.utc).strftime('%Y-%m-%d')).all()  # Inconsistencies in timezones and UTC application among vendors mean time cannot be used to confirm the recency of an API call response


@pytest.mark.dependency(depends=['test_harvest_single_report'])
def test_harvest_R5_SUSHI_with_invalid_dates(StatisticsSources_fixture, most_recent_month_with_usage, reports_offered_by_StatisticsSource_fixture):
    """Tests the code for rejecting a SUSHI end date before the begin date."""
    begin_date = most_recent_month_with_usage[0] + relativedelta(months=-3)  # Using three months before `most_recent_month_with_usage` so `end_date` is still in the past
    end_date = begin_date - timedelta(days=32)  # Sets `end_date` far enough before `begin_date` that it will be at least the last day of the month before `begin_date`
    end_date = last_day_of_month(end_date)
    SUSHI_data_response, flash_message_list = StatisticsSources_fixture._harvest_R5_SUSHI(
        begin_date,
        end_date,
        choice(reports_offered_by_StatisticsSource_fixture),
        bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
    )
    assert isinstance(SUSHI_data_response, str)
    assert isinstance(flash_message_list, dict)
    assert SUSHI_data_response == attempted_SUSHI_call_with_invalid_dates_statement(end_date, begin_date)
    assert len(flash_message_list) == 1


#Subsection: Test `StatisticsSources.collect_usage_statistics()`
@pytest.fixture(scope='module')
def month_before_month_like_most_recent_month_with_usage(most_recent_month_with_usage):
    """Creates `begin_date` and `end_date` SUSHI parameter values representing the month before the month in `most_recent_month_with_usage`.

    Testing `StatisticsSources.check_usage_statistics()` requires a month for which the `StatisticsSources_fixture` statistics source won't have SUSHI data loaded. The month before the month in `most_recent_month_with_usage` is likely to meet this criteria even after `test_StatisticsSources.test_harvest_R5_SUSHI()` loads data for the month in `most_recent_month_with_usage`. The dates are in a fixture so they can be used by both the test function and the `test_StatisticsSources.SUSHI_result()` fixture.

    Args:
        most_recent_month_with_usage (tuple): the first and last days of the most recent month for which COUNTER data is available

    Yields:
        tuple: two datetime.date values, representing the first and last day of a month respectively
    """
    begin_date = most_recent_month_with_usage[0] + relativedelta(months=-1)
    end_date = last_day_of_month(begin_date)
    log.info(f"`month_before_month_like_most_recent_month_with_usage()` yields `begin_date` {begin_date} (type {type(begin_date)}) and `end_date` {end_date} (type {type(end_date)}).")
    yield (begin_date, end_date)


@pytest.fixture  # Since this fixture is only called once, there's no functional difference between setting it at a function scope and setting it at a module scope
def harvest_R5_SUSHI_result(StatisticsSources_fixture, month_before_month_like_most_recent_month_with_usage, caplog):
    """A fixture with the result of all the SUSHI calls that will be made in `test_collect_usage_statistics()`.

    The `StatisticsSources.collect_usage_statistics()` method loads the data collected by the SUSHI call(s) made in `StatisticsSources._harvest_R5_SUSHI()` into the database. To confirm that the data was loaded successfully, a copy of the data that was loaded is needed for comparison. This fixture yields the same dataframe that `StatisticsSources.collect_usage_statistics()` loads into the database by calling `StatisticsSources._harvest_R5_SUSHI()`, just like the method being tested. Because the method being tested calls the method featured in this fixture, both methods being called in the same test function outputs two nearly identical collections of logging statements in the log of a single test; placing `StatisticsSources._harvest_R5_SUSHI()` in a fixture separates its log from that of `StatisticsSources.collect_usage_statistics()`.

    Args:
        StatisticsSources_fixture (nolcat.models.StatisticsSources): a class instantiation via fixture containing the necessary data to make a real SUSHI call
        month_before_month_like_most_recent_month_with_usage (tuple): the first and last days of the month before the most recent month for which COUNTER data is available
        caplog (pytest.logging.caplog): changes the logging capture level of individual test modules during test runtime

    Yields:
        tuple: a dataframe containing all of the R5 COUNTER data; a dictionary of harvested reports and the list of the statements that should be flashed returned by those reports (dict, key: str, value: list of str)
    """
    caplog.set_level(logging.INFO, logger='nolcat.SUSHI_call_and_response')  # For `make_SUSHI_call()`
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `upload_file_to_S3_bucket()` called in `SUSHICallAndResponse.make_SUSHI_call()` and `self._harvest_single_report()`
    caplog.set_level(logging.INFO, logger='nolcat.convert_JSON_dict_to_dataframe')  # For `create_dataframe()` called in `self._harvest_single_report()`
    yield StatisticsSources_fixture._harvest_R5_SUSHI(
        month_before_month_like_most_recent_month_with_usage[0],
        month_before_month_like_most_recent_month_with_usage[1],
        bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
    )


@pytest.mark.dependency(depends=['test_harvest_R5_SUSHI'])
@pytest.mark.slow
def test_collect_usage_statistics(engine, StatisticsSources_fixture, month_before_month_like_most_recent_month_with_usage, harvest_R5_SUSHI_result, caplog):
    """Tests that the `StatisticsSources.collect_usage_statistics()` successfully loads COUNTER data into the `COUNTERData` relation.
    
    The `harvest_R5_SUSHI_result` fixture contains the same data that the method being tested should've loaded into the database, so it is used to see if the test passes. There isn't a good way to review the flash messages returned by the method from a testing perspective.
    """
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `first_new_PK_value()`
    caplog.set_level(logging.INFO, logger='nolcat.SUSHI_call_and_response')  # For `make_SUSHI_call()` called in `self._harvest_R5_SUSHI()`
    caplog.set_level(logging.INFO, logger='nolcat.convert_JSON_dict_to_dataframe')  # For `create_dataframe()` called in `self._harvest_single_report()` called in `self._harvest_R5_SUSHI()`
    
    SUSHI_method_response, flash_message_list = StatisticsSources_fixture.collect_usage_statistics(
        month_before_month_like_most_recent_month_with_usage[0],
        month_before_month_like_most_recent_month_with_usage[1],
        bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
        )
    method_response_match_object = load_data_into_database_success_regex().fullmatch(SUSHI_method_response)
    assert isinstance(flash_message_list, dict)
    assert method_response_match_object is not None  # The test fails at this point because a failing condition here raises errors below

    records_loaded_by_method = match_direct_SUSHI_harvest_result(engine, method_response_match_object.group(1), caplog)
    df = harvest_R5_SUSHI_result[0]
    # The fields and records in the two dataframes are in different orders; they need to be consistent for `assert_frame_equal()` to work
    field_order = df.columns.tolist()
    records_loaded_by_method = records_loaded_by_method[field_order]
    df = df.sort_values(
        by=field_order,
        ignore_index=True,
    )
    records_loaded_by_method = records_loaded_by_method.sort_values(
        by=field_order,
        ignore_index=True,
    )
    assert_frame_equal(records_loaded_by_method[field_order], df)


#Section: Test `StatisticsSources.add_note()`
def test_add_note():
    """Test adding notes about statistics sources."""
    #ToDo: Develop this test alongside the method it's testing
    pass


#Section: Run `test_check_if_data_already_in_COUNTERData()`
# The function being tested is in `nolcat.app`, but it needs to have data in the `COUNTERData` relation, while the other tests in that module require the database to be empty; the function is being tested here for more accurate results.
@pytest.fixture
def partially_duplicate_COUNTER_data():
    """COUNTER data, some of which is in the `COUNTERData_relation` dataframe.

    Yields:
        dataframe: data formatted for loading into the `COUNTERData` relation
    """
    df = pd.DataFrame(
        [
            [3, "TR", "Empires of Vision<subtitle>A Reader</subtitle>", "Duke University Press", None, "Duke University Press", None, None, None, "10.1215/9780822378976", "Silverchair:417", "978-0-8223-7897-6", None, None, None, "Book", "Chapter", 2013, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Total_Item_Investigations", "2020-01-01", 4, None],
            [3, "TR", "Within the Circle<subtitle>An Anthology of African American Literary Criticism from the Harlem Renaissance to the Present</subtitle>", "Duke University Press", None, "Duke University Press", None, None, None, "10.1215/9780822399889", "Silverchair:1923", "978-0-8223-1536-0", None, None, None, "Book", "Chapter", 1994, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Total_Item_Investigations", "2020-01-01", 4, None],
            [3, "TR", "Pikachu's Global Adventure<subtitle>The Rise and Fall of Pokémon</subtitle>", "Duke University Press", None, "Duke University Press", None, None, None, "10.1215/9780822385813", "Silverchair:891", "978-0-8223-8581-3", None, None, None, "Book", "Book", 2004, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Total_Item_Investigations", "2020-03-01", 2, None],
            [3, "TR", "Pikachu's Global Adventure<subtitle>The Rise and Fall of Pokémon</subtitle>", "Duke University Press", None, "Duke University Press", None, None, None, "10.1215/9780822385813", "Silverchair:891", "978-0-8223-8581-3", None, None, None, "Book", "Book", 2004, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Unique_Item_Investigations", "2020-03-01", 2, None],
            [3, "TR", "Pikachu's Global Adventure<subtitle>The Rise and Fall of Pokémon</subtitle>", "Duke University Press", None, "Duke University Press", None, None, None, "10.1215/9780822385813", "Silverchair:891", "978-0-8223-8581-3", None, None, None, "Book", None, 2004, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Unique_Title_Investigations", "2020-03-01", 2, None],
            [3, "TR", "Within the Circle<subtitle>An Anthology of African American Literary Criticism from the Harlem Renaissance to the Present</subtitle>", "Duke University Press", None, "Duke University Press", None, None, None, "10.1215/9780822399889", "Silverchair:1923", "978-0-8223-1536-0", None, None, None, "Book", "Chapter", 1994, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Total_Item_Investigations", "2020-02-01", 16, None],
            [3, "TR", "Within the Circle<subtitle>An Anthology of African American Literary Criticism from the Harlem Renaissance to the Present</subtitle>", "Duke University Press", None, "Duke University Press", None, None, None, "10.1215/9780822399889", "Silverchair:1923", "978-0-8223-1536-0", None, None, None, "Book", "Chapter", 1994, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Total_Item_Investigations", "2020-02-01", 4, None],
        ],
        columns=["statistics_source_ID", "report_type", "resource_name", "publisher", "publisher_ID", "platform", "authors", "publication_date", "article_version", "DOI", "proprietary_ID", "ISBN", "print_ISSN", "online_ISSN", "URI", "data_type", "section_type", "YOP", "access_type", "access_method",  "parent_title", "parent_authors", "parent_publication_date", "parent_article_version", "parent_data_type", "parent_DOI", "parent_proprietary_ID", "parent_ISBN", "parent_print_ISSN", "parent_online_ISSN", "parent_URI", "metric_type", "usage_date", "usage_count", "report_creation_date"],
    )
    df.index.name = "COUNTER_data_ID"
    df = df.astype(COUNTERData.state_data_types())
    df["publication_date"] = pd.to_datetime(df["publication_date"])
    df["parent_publication_date"] = pd.to_datetime(df["parent_publication_date"])
    df["usage_date"] = pd.to_datetime(df["usage_date"])
    df["report_creation_date"] = pd.to_datetime(df["report_creation_date"])
    yield df


@pytest.fixture
def non_duplicate_COUNTER_data():
    """The COUNTER data from `partially_duplicate_COUNTER_data` not in the `COUNTERData_relation` dataframe.

    Yields:
        dataframe: data formatted for loading into the `COUNTERData` relation
    """
    df = pd.DataFrame(
        [
            [3, "TR", "Within the Circle<subtitle>An Anthology of African American Literary Criticism from the Harlem Renaissance to the Present</subtitle>", "Duke University Press", None, "Duke University Press", None, None, None, "10.1215/9780822399889", "Silverchair:1923", "978-0-8223-1536-0", None, None, None, "Book", "Chapter", 1994, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Total_Item_Investigations", "2020-02-01", 16, None],
            [3, "TR", "Within the Circle<subtitle>An Anthology of African American Literary Criticism from the Harlem Renaissance to the Present</subtitle>", "Duke University Press", None, "Duke University Press", None, None, None, "10.1215/9780822399889", "Silverchair:1923", "978-0-8223-1536-0", None, None, None, "Book", "Chapter", 1994, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Total_Item_Investigations", "2020-02-01", 4, None],
        ],
        columns=["statistics_source_ID", "report_type", "resource_name", "publisher", "publisher_ID", "platform", "authors", "publication_date", "article_version", "DOI", "proprietary_ID", "ISBN", "print_ISSN", "online_ISSN", "URI", "data_type", "section_type", "YOP", "access_type", "access_method",  "parent_title", "parent_authors", "parent_publication_date", "parent_article_version", "parent_data_type", "parent_DOI", "parent_proprietary_ID", "parent_ISBN", "parent_print_ISSN", "parent_online_ISSN", "parent_URI", "metric_type", "usage_date", "usage_count", "report_creation_date"],
    )
    df.index.name = "COUNTER_data_ID"
    df = df.astype(COUNTERData.state_data_types())
    df["publication_date"] = pd.to_datetime(df["publication_date"])
    df["parent_publication_date"] = pd.to_datetime(df["parent_publication_date"])
    df["usage_date"] = pd.to_datetime(df["usage_date"])
    df["report_creation_date"] = pd.to_datetime(df["report_creation_date"])
    yield df


def test_check_if_data_already_in_COUNTERData(engine, partially_duplicate_COUNTER_data, non_duplicate_COUNTER_data):
    """Tests the check for statistics source/report type/usage date combinations already in the database.
    
    While the function being tested here is in `nolcat.app`, the test is in this module because it requires the `COUNTERData` relation to contain data, while the `nolcat.app` test module starts with an empty database and never loads data into that relation.
    """
    number_of_records = query_database(
        query=f"SELECT COUNT(*) FROM COUNTERData;",
        engine=engine,
    )
    if isinstance(number_of_records, str):
        pytest.skip(database_function_skip_statements(number_of_records))
    if extract_value_from_single_value_df(number_of_records) == 0:
        pytest.skip(f"The prerequisite test data isn't in the database, so this test will fail if run.")
    df, message = check_if_data_already_in_COUNTERData(partially_duplicate_COUNTER_data)
    assert_frame_equal(df.reset_index(drop=True), non_duplicate_COUNTER_data.reset_index(drop=True))  # The `drop` argument handles the fact that `check_if_data_already_in_COUNTERData()` returns the matched records with the index values from the dataframe used as the function argument
    # The order of the statistics source ID, report type, and date combinations that were matched is inconsistent, so the return statement containing them is tested in multiple parts
    assert message.startswith(f"Usage statistics for the report type, usage date, and statistics source combination(s) below, which were included in the upload, are already in the database; as a result, it wasn't uploaded to the database. If the data needs to be re-uploaded, please remove the existing data from the database first.\n")
    assert f"TR  | 2020-03-01 | Duke UP (ID 3)" in message
    assert f"TR  | 2020-01-01 | Duke UP (ID 3)" in message