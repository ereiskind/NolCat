"""Tests the methods in AnnualUsageCollectionTracking."""
########## Passing 2024-12-19 ##########

import pytest
import logging
from filecmp import cmp
from pandas.testing import assert_frame_equal
from werkzeug.datastructures import FileStorage

# `conftest.py` fixtures are imported automatically
from conftest import match_direct_SUSHI_harvest_result
from nolcat.app import *
from nolcat.models import *
from nolcat.statements import *

log = logging.getLogger(__name__)


#Section: Collecting Annual COUNTER Usage Statistics
@pytest.fixture(scope='module')
def AUCT_fixture_for_SUSHI(engine):
    """Creates an `AnnualUsageCollectionTracking` object with a non-null `StatisticsSources.statistics_source_retrieval_code` value.

    Args:
        engine (sqlalchemy.engine.Engine): a SQLAlchemy engine
        caplog (pytest.logging.caplog): changes the logging capture level of individual test modules during test runtime
    
    Yields:
        nolcat.models.AnnualUsageCollectionTracking: an AnnualUsageCollectionTracking object corresponding to a record with a non-null `statistics_source_retrieval_code` attribute
    """
    record = query_database(
        query=f"SELECT * FROM annualUsageCollectionTracking JOIN statisticsSources ON statisticsSources.statistics_source_ID=annualUsageCollectionTracking.AUCT_statistics_source WHERE statisticsSources.statistics_source_retrieval_code IS NOT NULL;",
        engine=engine,
    )
    if isinstance(record, str):
        pytest.skip(database_function_skip_statements(record, False))
    record = record.sample().reset_index()
    yield_object = AnnualUsageCollectionTracking(
        AUCT_statistics_source=record.at[0,'AUCT_statistics_source'],
        AUCT_fiscal_year=record.at[0,'AUCT_fiscal_year'],
        usage_is_being_collected=record.at[0,'usage_is_being_collected'],
        manual_collection_required=record.at[0,'manual_collection_required'],
        collection_via_email=record.at[0,'collection_via_email'],
        is_COUNTER_compliant=record.at[0,'is_COUNTER_compliant'],
        collection_status=record.at[0,'collection_status'],
        usage_file_path=record.at[0,'usage_file_path'],
        notes=record.at[0,'notes'],
    )
    log.warning(initialize_relation_class_object_statement("AnnualUsageCollectionTracking", yield_object))  # This is set at `warning` to show the retrieval code
    yield yield_object


@pytest.fixture  # Since this fixture is only called once, there's no functional difference between setting it at a function scope and setting it at a module scope
def harvest_R5_SUSHI_result(engine, AUCT_fixture_for_SUSHI, caplog):
    """A fixture with the result of all the SUSHI calls that will be made in `test_collect_annual_usage_statistics()`.

    The `AnnualUsageCollectionTracking.collect_annual_usage_statistics()` method loads the data collected by the SUSHI call made to the designated statistics source for the dates indicated by the fiscal year into the database. To confirm that the data was loaded successfully, a copy of the data that was loaded is needed for comparison. This fixture yields the same dataframe that `AnnualUsageCollectionTracking.collect_annual_usage_statistics()` loads into the database by calling `StatisticsSources._harvest_R5_SUSHI()`, just like the method being tested. Because the method being tested calls the method featured in this fixture, both methods being called in the same test function outputs two nearly identical collections of logging statements in the log of a single test; placing `StatisticsSources._harvest_R5_SUSHI()` in a fixture separates its log from that of `AnnualUsageCollectionTracking.collect_annual_usage_statistics()`.

    Args:
        engine (sqlalchemy.engine.Engine): a SQLAlchemy engine
        AUCT_fixture_for_SUSHI (nolcat.models.AnnualUsageCollectionTracking): a class instantiation via fixture used to get the necessary data to make a real SUSHI call
        caplog (pytest.logging.caplog): changes the logging capture level of individual test modules during test runtime

    Yields:
        dataframe: a dataframe containing all of the R5 COUNTER data
    """
    caplog.set_level(logging.INFO, logger='nolcat.SUSHI_call_and_response')  # For `make_SUSHI_call()`
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `upload_file_to_S3_bucket()` called in `SUSHICallAndResponse.make_SUSHI_call()`, `self._harvest_single_report()`, and for `query_database()`
    caplog.set_level(logging.INFO, logger='nolcat.convert_JSON_dict_to_dataframe')  # For `create_dataframe()` called in `self._harvest_single_report()`

    record = query_database(
        query=f"""
            SELECT
                fiscalYears.start_date,
                fiscalYears.end_date,
                statisticsSources.statistics_source_ID,
                statisticsSources.statistics_source_name,
                statisticsSources.statistics_source_retrieval_code,
                statisticsSources.vendor_ID
            FROM annualUsageCollectionTracking
                JOIN statisticsSources ON statisticsSources.statistics_source_ID=annualUsageCollectionTracking.AUCT_statistics_source
                JOIN fiscalYears ON fiscalYears.fiscal_year_ID=annualUsageCollectionTracking.AUCT_fiscal_year
            WHERE
                annualUsageCollectionTracking.AUCT_statistics_source={AUCT_fixture_for_SUSHI.AUCT_statistics_source}
                AND annualUsageCollectionTracking.AUCT_fiscal_year={AUCT_fixture_for_SUSHI.AUCT_fiscal_year};
        """,
        engine=engine,
    )
    if isinstance(record, str):
        pytest.skip(database_function_skip_statements(record, False))
    
    start_date = record.at[0,'start_date']
    end_date = record.at[0,'end_date']
    StatisticsSources_object = StatisticsSources(  # Even with one value, the field of a single-record dataframe is still considered a series, making type juggling necessary
        statistics_source_ID = int(record.at[0,'statistics_source_ID']),
        statistics_source_name = str(record.at[0,'statistics_source_name']),
        statistics_source_retrieval_code = str(record.at[0,'statistics_source_retrieval_code']).split(".")[0],  # String created is of a float (aka `n.0`), so the decimal and everything after it need to be removed
        vendor_ID = int(record.at[0,'vendor_ID']),
    )
    log.debug(return_value_from_query_statement((start_date, end_date, StatisticsSources_object), f"start date, end date, and `StatisticsSources` object"))
    yield_object = StatisticsSources_object._harvest_R5_SUSHI(
        start_date,
        end_date,
        bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
    )[0]
    log.debug(f"`harvest_R5_SUSHI_result()` fixture using StatisticsSources object {StatisticsSources_object}, start date {start_date}, and end date {end_date} returned the following:\n{yield_object}.")
    if isinstance(yield_object, str):
        file_name_match_object = upload_file_to_S3_bucket_success_regex().match(yield_object)
        if file_name_match_object:
            file_name = file_name_match_object.group(1)
            try:
                s3_client.delete_object(
                    Bucket=BUCKET_NAME,
                    Key=PATH_WITHIN_BUCKET_FOR_TESTS + file_name
                )
            except botocore.exceptions as error:
                log.error(unable_to_delete_test_file_in_S3_statement(file_name, error))
        pytest.skip(f"Unable to create fixture because `_harvest_R5_SUSHI()` returned the errors {yield_object}.")
    yield yield_object


@pytest.mark.slow
@pytest.mark.skip(reason="Almost all of the options for this test will trigger skipping the test.")  #TEST: Remove if reason for skip changes
def test_collect_annual_usage_statistics(engine, client, AUCT_fixture_for_SUSHI, harvest_R5_SUSHI_result, caplog):
    """Test calling the `StatisticsSources._harvest_R5_SUSHI()` method for the record's StatisticsSources instance with arguments taken from the record's FiscalYears instance.
    
    The `harvest_R5_SUSHI_result` fixture contains the same data that the method being tested should've loaded into the database, so it is used to see if the test passes. There isn't a good way to review the flash messages returned by the method from a testing perspective.
    """
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `first_new_PK_value()` and `query_database()`
    caplog.set_level(logging.INFO, logger='nolcat.SUSHI_call_and_response')  # For `make_SUSHI_call()` called in `self._harvest_R5_SUSHI()`
    caplog.set_level(logging.INFO, logger='nolcat.convert_JSON_dict_to_dataframe')  # For `create_dataframe()` called in `self._harvest_single_report()` called in `self._harvest_R5_SUSHI()`

    with client:
        logging_statement, flash_statements = AUCT_fixture_for_SUSHI.collect_annual_usage_statistics(bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS)
    log.debug(f"The `collect_annual_usage_statistics()` response is `{logging_statement}` and the logging statements are `{flash_statements}`.")
    method_response_match_object = load_data_into_database_success_regex().match(logging_statement)
    # The test fails at this point because a failing condition here raises errors below
    assert method_response_match_object is not None
    assert update_database_success_regex().search(logging_statement)
    assert isinstance(flash_statements, dict)

    database_update_check = query_database(
        query=f"SELECT collection_status FROM annualUsageCollectionTracking WHERE annualUsageCollectionTracking.AUCT_statistics_source={AUCT_fixture_for_SUSHI.AUCT_statistics_source} AND annualUsageCollectionTracking.AUCT_fiscal_year={AUCT_fixture_for_SUSHI.AUCT_fiscal_year};",
        engine=engine,
    )
    if isinstance(database_update_check, str):
        pytest.skip(database_function_skip_statements(database_update_check))
    database_update_check = extract_value_from_single_value_df(database_update_check, False)

    records_loaded_by_method = match_direct_SUSHI_harvest_result(engine, method_response_match_object.group(1), caplog)
    assert database_update_check == "Collection complete"
    assert_frame_equal(records_loaded_by_method, harvest_R5_SUSHI_result[records_loaded_by_method.columns.to_list()])


#Section: Upload and Download Nonstandard Usage File
@pytest.fixture
def sample_FileStorage_object(path_to_sample_file):
    """Creates a Werkzeug FileStorage object for use in testing the `AnnualUsageCollectionTracking.upload_nonstandard_usage_file()` method.
    
    The AnnualUsageCollectionTracking.upload_nonstandard_usage_file()` method takes a Werkzeug FileStorage object; the `mock_FileStorage_object` class was devised to simulate such objects.

    Args:
        path_to_sample_file (pathlib.Path): an absolute file path to a randomly selected file

    Yields:
        werkzeug.datastructures.FileStorage: a file in a Werkzeug FileStorage object
    """
    open_file_stream = open(path_to_sample_file, 'rb')  # Opening the JSON as text raises `TypeError: a bytes-like object is required, not 'str'` on the `werkzeug.datastructures.FileStorage.save()` method 
    yield FileStorage(
        stream=open_file_stream,
        filename=path_to_sample_file.absolute(),
    )
    open_file_stream.close()


@pytest.mark.dependency()
def test_upload_nonstandard_usage_file(engine, client, tmp_path, sample_FileStorage_object, non_COUNTER_AUCT_object_before_upload, path_to_sample_file, caplog):
    """Test uploading a file with non-COUNTER usage statistics to S3 and updating the AUCT relation accordingly."""
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `upload_file_to_S3_bucket()` and `query_database()`

    #Section: Make Function Call
    with client:
        upload_result = non_COUNTER_AUCT_object_before_upload.upload_nonstandard_usage_file(sample_FileStorage_object, bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS)

    #Section: Check Results with Assert Statements
    file_name = f"{non_COUNTER_AUCT_object_before_upload.AUCT_statistics_source}_{non_COUNTER_AUCT_object_before_upload.AUCT_fiscal_year}{Path(sample_FileStorage_object.filename).suffix}"
    
    #Subsection: Check Function Return Value
    log.debug(f"`AnnualUsageCollectionTracking.upload_nonstandard_usage_file()` return value is {upload_result} (type {type(upload_result)}).")
    upload_result = upload_nonstandard_usage_file_success_regex().fullmatch(upload_result)
    assert upload_result is not None
    assert upload_result.group(1) == file_name

    #Subsection: Check File Upload to S3
    list_objects_response = s3_client.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=PATH_WITHIN_BUCKET_FOR_TESTS,
    )
    log.debug(f"Raw contents of `{BUCKET_NAME}/{PATH_WITHIN_BUCKET_FOR_TESTS}` (type {type(list_objects_response)}):\n{format_list_for_stdout(list_objects_response)}.")
    bucket_contents = []
    for contents_dict in list_objects_response['Contents']:
        bucket_contents.append(contents_dict['Key'])
    bucket_contents = [file_name.replace(PATH_WITHIN_BUCKET_FOR_TESTS, "") for file_name in bucket_contents]
    log.info(f"List of `{BUCKET_NAME}/{PATH_WITHIN_BUCKET_FOR_TESTS}` contents:\n{format_list_for_stdout(bucket_contents)}")
    assert file_name in bucket_contents
    download_location = tmp_path / file_name
    s3_client.download_file(
        Bucket=BUCKET_NAME,
        Key=PATH_WITHIN_BUCKET_FOR_TESTS + file_name,
        Filename=download_location,
    )
    assert cmp(path_to_sample_file, download_location)
    
    #Subsection: Check Database Update
    usage_file_path_in_database = query_database(
        query=f"SELECT usage_file_path FROM annualUsageCollectionTracking WHERE AUCT_statistics_source={non_COUNTER_AUCT_object_before_upload.AUCT_statistics_source} AND AUCT_fiscal_year={non_COUNTER_AUCT_object_before_upload.AUCT_fiscal_year};",
        engine=engine,
    )
    if isinstance(usage_file_path_in_database, str):
        pytest.skip(database_function_skip_statements(usage_file_path_in_database))
    usage_file_path_in_database = extract_value_from_single_value_df(usage_file_path_in_database)
    log.debug(return_value_from_query_statement(usage_file_path_in_database))
    assert file_name == usage_file_path_in_database


def test_download_nonstandard_usage_file(non_COUNTER_AUCT_object_after_upload, non_COUNTER_file_to_download_from_S3, download_destination):
    """Test downloading a file in S3 to a local computer."""
    log.debug(f"Before `download_nonstandard_usage_file()`," + list_folder_contents_statement(download_destination, False))
    file_path = non_COUNTER_AUCT_object_after_upload.download_nonstandard_usage_file(
        download_destination,
        bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
        )
    log.debug(f"After `download_nonstandard_usage_file()`," + list_folder_contents_statement(download_destination, False))
    assert file_path.stem == f"{non_COUNTER_AUCT_object_after_upload.AUCT_statistics_source}_{non_COUNTER_AUCT_object_after_upload.AUCT_fiscal_year}"
    assert file_path.is_file()
    assert cmp(file_path, non_COUNTER_file_to_download_from_S3)  # The file uploaded to S3 for the test and the downloaded file are the same