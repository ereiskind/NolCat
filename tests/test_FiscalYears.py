"""Tests the methods in FiscalYears."""
########## Passing 2024-12-19 ##########

import pytest
import logging
from datetime import date
from random import choice
import pandas as pd
from pandas.testing import assert_frame_equal

# `conftest.py` fixtures are imported automatically
from nolcat.app import *
from nolcat.models import *
from nolcat.statements import *

log = logging.getLogger(__name__)


#Section: Test Annual Usage Statistics Methods
@pytest.fixture
def FY2020_FiscalYears_object(engine, caplog):
    """Creates a FiscalYears object for the fiscal year with COUNTER R5 test data.

    Args:
        engine (sqlalchemy.engine.Engine): a SQLAlchemy engine
        caplog (pytest.logging.caplog): changes the logging capture level of individual test modules during test runtime

    Yields:
        nolcat.models.FiscalYears: a FiscalYears object corresponding to the FY 2021 record
    """
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()`
    record = query_database(
        query=f"SELECT * FROM fiscalYears WHERE fiscal_year='2020';",
        engine=engine,
        # Conversion to class object easier when primary keys stay as standard fields
    )
    if isinstance(record, str):
        pytest.skip(database_function_skip_statements(record, False))
    yield_object = FiscalYears(
        fiscal_year_ID=record.at[0,'fiscal_year_ID'],
        fiscal_year=record.at[0,'fiscal_year'],
        start_date=record.at[0,'start_date'],
        end_date=record.at[0,'end_date'],
        notes_on_statisticsSources_used=record.at[0,'notes_on_statisticsSources_used'],
        notes_on_corrections_after_submission=record.at[0,'notes_on_corrections_after_submission'],
    )
    log.info(initialize_relation_class_object_statement("FiscalYears", yield_object))
    yield yield_object


def test_calculate_depreciated_ACRL_60b(client, FY2020_FiscalYears_object):
    """Tests getting the old ACRL 60b value.
    
    Dynamically getting the value through SQL queries would be effectively repeating the method, so the method call is compared to a constant value.
    """
    with client:
        assert FY2020_FiscalYears_object.calculate_depreciated_ACRL_60b() == 2263


def test_calculate_depreciated_ACRL_63(client, FY2020_FiscalYears_object):
    """Tests getting the old ACRL 63 value.
    
    Dynamically getting the value through a SQL query would be effectively repeating the method, so the method call is compared to a constant value.
    """
    with client:
        assert FY2020_FiscalYears_object.calculate_depreciated_ACRL_63() == 2190


def test_calculate_ACRL_61a(client, FY2020_FiscalYears_object):
    """Tests getting the ACRL 61a value.
    
    Dynamically getting the value through SQL queries would be effectively repeating the method, so the method call is compared to a constant value.
    """
    with client:
        assert FY2020_FiscalYears_object.calculate_ACRL_61a() == 73


def test_calculate_ACRL_61b(client, FY2020_FiscalYears_object):
    """Tests getting the ACRL 61b value.
    
    Dynamically getting the value through a SQL query would be effectively repeating the method, so the method call is compared to a constant value.
    """
    with client:
        assert FY2020_FiscalYears_object.calculate_ACRL_61b() == 2190


def test_calculate_ARL_18(client, FY2020_FiscalYears_object):
    """Tests getting the ARL 18 value.
    
    Dynamically getting the value through a SQL query would be effectively repeating the method, so the method call is compared to a constant value.
    """
    with client:
        assert FY2020_FiscalYears_object.calculate_ARL_18() == 2190


def test_calculate_ARL_19(client, FY2020_FiscalYears_object):
    """Tests getting the ARL 19 value.
    
    Dynamically getting the value through a SQL query would be effectively repeating the method, so the method call is compared to a constant value.
    """
    with client:
        assert FY2020_FiscalYears_object.calculate_ARL_19() == 85613


def test_calculate_ARL_20(client, FY2020_FiscalYears_object):
    """Tests getting the ARL 20 value.
    
    Dynamically getting the value through a SQL query would be effectively repeating the method, so the method call is compared to a constant value.
    """
    with client:
        assert FY2020_FiscalYears_object.calculate_ARL_20() == 0


#Section: Test Creating New `annualUsageCollectionTracking` Records
@pytest.fixture
def FY2023_FiscalYears_object_and_record():
    """Creates a FiscalYears object and an empty record for the fiscalYears relation.

    Yields:
        tuple: the FiscalYears object for the 2023 FY; a single-record dataframe for the fiscalYears relation for FY 2023
    """
    primary_key_value = 6
    fiscal_year_value = "2023"
    start_date_value = date.fromisoformat('2022-07-01')
    end_date_value = date.fromisoformat('2023-06-30')

    FY_instance = FiscalYears(
        fiscal_year_ID = primary_key_value,
        fiscal_year = fiscal_year_value,
        start_date = start_date_value,
        end_date = end_date_value,
        notes_on_statisticsSources_used = None,
        notes_on_corrections_after_submission = None,
    )
    FY_df = pd.DataFrame(
        [[fiscal_year_value, start_date_value, end_date_value, None, None]],
        index=[primary_key_value],
        columns=["fiscal_year", "start_date", "end_date", "notes_on_statisticsSources_used", "notes_on_corrections_after_submission"],
    )
    FY_df.index.name = "fiscal_year_ID"
    yield (FY_instance, FY_df)


@pytest.fixture
def load_new_record_into_fiscalYears(engine, FY2023_FiscalYears_object_and_record, caplog):
    """Since the test data AUCT relation includes all of the years in the fiscal years relation, to avoid primary key duplication, a new record is added to the `fiscalYears` relation for the `test_create_usage_tracking_records_for_fiscal_year()` test function.

    Args:
        engine (sqlalchemy.engine.Engine): a SQLAlchemy engine
        FY2023_FiscalYears_object_and_record (tuple): the FiscalYears object for the 2023 FY; a single-record dataframe for the fiscalYears relation for FY 2023
        caplog (pytest.logging.caplog): changes the logging capture level of individual test modules during test runtime
    
    Yields:
        None
    """
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `load_data_into_database()`
    method_result = load_data_into_database(
        df=FY2023_FiscalYears_object_and_record[1],
        relation='fiscalYears',
        engine=engine,
        index_field_name='fiscal_year_ID',
    )
    if not load_data_into_database_success_regex().fullmatch(method_result):
        pytest.skip(database_function_skip_statements(method_result, False))
    yield None


def test_create_usage_tracking_records_for_fiscal_year(engine, client, load_new_record_into_fiscalYears, FY2023_FiscalYears_object_and_record, caplog):  # `load_new_records_into_fiscalYears()` not called but used to load record needed for test
    """Tests creating a record in the `annualUsageCollectionTracking` relation for the given fiscal year for each current statistics source."""
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()`

    #Section: Call Method
    with client:
        method_result = FY2023_FiscalYears_object_and_record[0].create_usage_tracking_records_for_fiscal_year()
    if not load_data_into_database_success_regex().fullmatch(method_result):
        assert False  # If the code comes here, the method call being tested failed; by failing and thus ending the test here, error handling isn't needed in the remainder of the test function
    
    #Section: Create and Compare Dataframes
    retrieved_data = query_database(
        query="SELECT * FROM annualUsageCollectionTracking;",
        engine=engine,
        index=["AUCT_statistics_source", "AUCT_fiscal_year"],
    )
    if isinstance(retrieved_data, str):
        pytest.skip(database_function_skip_statements(retrieved_data))
    retrieved_data = retrieved_data.astype({
        "collection_status": AnnualUsageCollectionTracking.state_data_types()["collection_status"],
        "usage_file_path": AnnualUsageCollectionTracking.state_data_types()["usage_file_path"],
        "notes": AnnualUsageCollectionTracking.state_data_types()["notes"],
    })
    retrieved_data['usage_is_being_collected'] = restore_boolean_values_to_boolean_field(retrieved_data['usage_is_being_collected'])
    retrieved_data['manual_collection_required'] = restore_boolean_values_to_boolean_field(retrieved_data['manual_collection_required'])
    retrieved_data['collection_via_email'] = restore_boolean_values_to_boolean_field(retrieved_data['collection_via_email'])
    retrieved_data['is_COUNTER_compliant'] = restore_boolean_values_to_boolean_field(retrieved_data['is_COUNTER_compliant'])
    
    multiindex = pd.MultiIndex.from_tuples(  # MySQL returns results sorted by index; the order of the dataframe elements below copies that order
        [
            (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
            (1, 0), (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6),
            (2, 0), (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6),
            (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6),
            (4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6),
            (5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6),
            (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6),
            (7, 0), (7, 1), (7, 2),
            (8, 0), (8, 1), (8, 2),
            (9, 3), (9, 4), (9, 5), (9, 6),
            (10, 0), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6),
            (11, 0), (11, 1), (11, 2), (11, 3), (11, 4), (11, 5), (11, 6),
        ],
        names=["AUCT_statistics_source", "AUCT_fiscal_year"],
    )
    expected_output_data = pd.DataFrame(
        [
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection not started", None, None],
            [None, None, None, None, None, None, None],

            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection not started", None, None],
            [None, None, None, None, None, None, None],

            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection not started", None, None],
            [None, None, None, None, None, None, None],

            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection not started", None, None],
            [None, None, None, None, None, None, None],

            [True, True, False, False, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, "Simulating a resource that's become COUNTER compliant"],
            [True, True, False, True, "No usage to report", None, None],
            [True, True, False, True, "Collection complete", None, None],
            [True, True, False, True, "Collection complete", None, "Ended subscription, only Med has content now"],
            [False, False, False, False, "N/A: Paid by Med", None, "Still have access to content through Med"],
            [None, None, None, None, None, None, None],

            [True, True, True, False, "Collection complete", None, "Simulating a resource with usage requested by sending an email"],
            [True, True, True, False, "Collection in process (see notes)", None, "When sending the email, note the date sent and who it was sent to"],
            [True, True, True, False, "Collection in process (see notes)", None, "Having the note about sending the email lets you know if you're in the response window, if you need to follow up, or if too much time has passed for a response to be expected"],
            [True, True, True, False, "Collection in process (see notes)", None, "Email info"],
            [True, True, True, False, "Collection in process (see notes)", None, "Email info"],
            [True, True, True, False, "Collection not started", None, None],
            [None, None, None, None, None, None, None],

            [True, True, False, True, "Collection complete", None, "Simulating a resource that becomes OA at the start of a calendar year"],
            [True, True, False, True, "Collection complete", None, "Resource became OA at start of calendar year 2018"],
            [False, False, False, False, "N/A: Open access", None, None],
            [False, False, False, False, "N/A: Open access", None, None],
            [False, False, False, False, "N/A: Open access", None, None],
            [False, False, False, False, "N/A: Open access", None, None],
            [None, None, None, None, None, None, None],

            [True, True, True, False, "Collection not started", None, None],
            [True, True, True, False, "Collection complete", None, None],
            [True, True, True, False, "Collection complete", None, None],

            [True, True, True, False, "Collection not started", None, None],
            [True, True, True, False, "Collection complete", None, None],
            [True, True, True, False, "Collection complete", None, None],

            [True, True, False, False, "Collection complete", None, None],
            [True, True, False, False, "Collection complete", None, None],
            [True, True, False, False, "Collection not started", None, None],
            [None, None, None, None, None, None, None],

            [False, False, False, False, "N/A: Open access", None, None],
            [False, False, False, False, "N/A: Open access", None, None],
            [False, False, False, False, "N/A: Open access", None, None],
            [False, False, False, False, "N/A: Open access", None, None],
            [False, False, False, False, "N/A: Open access", None, None],
            [False, False, False, False, "N/A: Open access", None, None],
            [None, None, None, None, None, None, None],

            [True, True, True, False, "Usage not provided", None, "Simulating a resource that starts offering usage statistics"],
            [True, True, True, False, "Usage not provided", None, None],
            [True, True, False, False, "Collection complete", "11_2.csv", "This is the first FY with usage statistics"],
            [True, True, False, False, "Collection complete", "11_3.csv", None],
            [True, True, False, False, "Collection complete", "11_4.csv", None],
            [True, False, False, False, "Collection not started", None, "This is the record for `tests.test_FiscalYears.test_collect_fiscal_year_usage_statistics()`"],
            [None, None, None, None, None, None, None],
        ],
        index=multiindex,
        columns=["usage_is_being_collected", "manual_collection_required", "collection_via_email", "is_COUNTER_compliant", "collection_status", "usage_file_path", "notes"],
    )
    expected_output_data = expected_output_data.astype(AnnualUsageCollectionTracking.state_data_types())
    
    regex_match_object = load_data_into_database_success_regex().fullmatch(method_result)
    assert regex_match_object is not None
    assert int(regex_match_object.group(1)) == 10
    assert regex_match_object.group(2) == "annualUsageCollectionTracking"
    assert_frame_equal(retrieved_data, expected_output_data, check_index_type=False)  # `check_index_type` argument allows test to pass if indexes are different dtypes


#Section: Test Collecting Usage Statistics
@pytest.fixture
def FY2022_FiscalYears_object(engine, caplog):
    """Creates a FiscalYears object for the fiscal year with an `annualUsageCollectionTracking` record that meets the criteria for inclusion in `FiscalYears.collect_fiscal_year_usage_statistics()`.

    Args:
        engine (sqlalchemy.engine.Engine): a SQLAlchemy engine
        caplog (pytest.logging.caplog): changes the logging capture level of individual test modules during test runtime

    Yields:
        nolcat.models.FiscalYears: a FiscalYears object corresponding to the FY 2022 record
    """
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()`
    record = query_database(
        query=f"SELECT * FROM fiscalYears WHERE fiscal_year='2022';",
        engine=engine,
        # Conversion to class object easier when primary keys stay as standard fields
    )
    if isinstance(record, str):
        pytest.skip(database_function_skip_statements(record, False))
    yield_object = FiscalYears(
        fiscal_year_ID=record.at[0,'fiscal_year_ID'],
        fiscal_year=record.at[0,'fiscal_year'],
        start_date=record.at[0,'start_date'],
        end_date=record.at[0,'end_date'],
        notes_on_statisticsSources_used=record.at[0,'notes_on_statisticsSources_used'],
        notes_on_corrections_after_submission=record.at[0,'notes_on_corrections_after_submission'],
    )
    log.info(initialize_relation_class_object_statement("FiscalYears", yield_object))
    yield yield_object


@pytest.mark.slow
def test_collect_fiscal_year_usage_statistics(engine, FY2022_FiscalYears_object, caplog):
    """Create a test calling the `StatisticsSources._harvest_R5_SUSHI()` method with the `FiscalYears.start_date` and `FiscalYears.end_date` as the arguments. """
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `first_new_PK_value()` and `update_database()`
    caplog.set_level(logging.INFO, logger='nolcat.SUSHI_call_and_response')  # For `make_SUSHI_call()` called in `self._harvest_R5_SUSHI()`
    caplog.set_level(logging.INFO, logger='nolcat.convert_JSON_dict_to_dataframe')  # For `create_dataframe()` called in `self._harvest_single_report()` called in `self._harvest_R5_SUSHI()`

    #Section: Add Random Statistics_Source_Retrieval_Code to Relevant Record
    # A random value is added at this point for greater variability in the testing
    retrieval_codes_as_interface_IDs = []  # The list of `StatisticsSources.statistics_source_retrieval_code` values from the JSON, which are labeled as `interface_id` in the JSON
    with open(PATH_TO_CREDENTIALS_FILE()) as JSON_file:
        SUSHI_data_file = json.load(JSON_file)
        for vendor in SUSHI_data_file:
            for statistics_source_dict in vendor['interface']:
                if "interface_id" in list(statistics_source_dict.keys()):
                        retrieval_codes_as_interface_IDs.append(statistics_source_dict['interface_id'])
    retrieval_code = str(choice(retrieval_codes_as_interface_IDs)).split(".")[0]  # String created is of a float (aka `n.0`), so the decimal and everything after it need to be removed

    update_result = update_database(
        update_statement=f"UPDATE statisticsSources SET statistics_source_retrieval_code='{retrieval_code}' WHERE statistics_source_ID=11;",
        engine=engine,
    )
    if not update_database_success_regex().fullmatch(update_result):
        pytest.skip("Unable to add statistics source retrieval code to relevant record.")
    
    #Section: Make Function Call
    before_count = query_database(
        query=f"SELECT COUNT(*) FROM COUNTERData;",
        engine=engine,
    )
    if isinstance(before_count, str):
        pytest.skip(database_function_skip_statements(before_count, False))
    before_count = extract_value_from_single_value_df(before_count)
    logging_statement, flash_messages = FY2022_FiscalYears_object.collect_fiscal_year_usage_statistics()
    if re.fullmatch(r"None of the \d+ statistics sources with SUSHI for FY 2022 returned any data\.", logging_statement):
        pytest.skip(database_function_skip_statements(f"up to {len(flash_messages)} errors.", no_data=True))
    after_count = query_database(
        query=f"SELECT COUNT(*) FROM COUNTERData;",
        engine=engine,
    )
    if isinstance(after_count, str):
        pytest.skip(database_function_skip_statements(after_count, False))
    after_count = extract_value_from_single_value_df(after_count)

    #Section: Assert Statements
    assert before_count < after_count
    assert load_data_into_database_success_regex().match(logging_statement)
    assert update_database_success_regex().search(logging_statement)
    assert isinstance(flash_messages, dict)