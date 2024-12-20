"""Tests the routes in the `ingest_usage` blueprint."""
########## Passing 2024-12-19 ##########

import pytest
import logging
from random import choice
from pathlib import Path
import os
import re
from ast import literal_eval
from filecmp import cmp
from bs4 import BeautifulSoup
import pandas as pd
from pandas.testing import assert_frame_equal
from requests_toolbelt.multipart.encoder import MultipartEncoder

# `conftest.py` fixtures are imported automatically
from conftest import match_direct_SUSHI_harvest_result
from conftest import prepare_HTML_page_for_comparison
from nolcat.app import *
from nolcat.models import *
from nolcat.statements import *
from nolcat.ingest_usage import *

log = logging.getLogger(__name__)


def test_ingest_usage_homepage(client):
    """Tests that the homepage can be successfully GET requested and that the response matches the file being used."""
    page = client.get('/ingest_usage/')
    GET_soup = BeautifulSoup(page.data, 'lxml')
    GET_response_title = GET_soup.head.title
    GET_response_page_title = GET_soup.body.h1

    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'ingest_usage' / 'templates' / 'ingest_usage' / 'index.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title
        HTML_file_page_title = file_soup.body.h1

    assert page.status == "200 OK"
    assert HTML_file_title == GET_response_title
    assert HTML_file_page_title == GET_response_page_title


@pytest.mark.dependency()
@pytest.mark.slow
def test_upload_COUNTER_data_via_Excel(engine, client, header_value, COUNTERData_relation, create_COUNTERData_workbook_iterdir_list, caplog):
    """Tests adding data to the `COUNTERData` relation by uploading files with the `ingest_usage.COUNTERReportsForm` form."""
    caplog.set_level(logging.INFO, logger='nolcat.upload_COUNTER_reports')  # For `create_dataframe()`
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `first_new_PK_value()` and `query_database()`
    
    form_submissions = {'COUNTER_data': [open(file, 'rb') for file in create_COUNTERData_workbook_iterdir_list]}
    log.debug(f"The files being uploaded to the database are:\n{format_list_for_stdout(form_submissions)}")
    header_value['Content-Type'] = 'multipart/form-data'
    POST_response = client.post(
        '/ingest_usage/upload-COUNTER',
        follow_redirects=True,
        headers=header_value,
        data=form_submissions,
    )

    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'ingest_usage' / 'templates' / 'ingest_usage' / 'index.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title.string.encode('utf-8')
        HTML_file_page_title = file_soup.body.h1.string.encode('utf-8')
    df = query_database(
        query=f"SELECT * FROM COUNTERData ORDER BY COUNTER_data_ID ASC LIMIT {COUNTERData_relation.shape[0]};",
        engine=engine,
        index='COUNTER_data_ID',
    )
    if isinstance(df, str):
        pytest.skip(database_function_skip_statements(df))
    df = df.astype(COUNTERData.state_data_types())
    df = df.drop(columns=['report_creation_date'])

    assert POST_response.history[0].status == "302 FOUND"  # This confirms there was a redirect
    assert POST_response.status == "200 OK"
    assert HTML_file_title in POST_response.data
    assert HTML_file_page_title in POST_response.data
    assert load_data_into_database_success_regex().search(prepare_HTML_page_for_comparison(POST_response.data))  # This confirms the flash message indicating success appears; if there's an error, the error message appears instead, meaning this statement will fail
    assert_frame_equal(df, COUNTERData_relation[df.columns.tolist()], check_index_type=False)  # `check_index_type` argument allows test to pass if indexes aren't the same dtype


@pytest.mark.dependency(depends=['test_upload_COUNTER_data_via_Excel'])
def test_upload_COUNTER_data_via_SQL_insert(engine, client, header_value):
    """Tests updating the `COUNTERData` relation with insert statements in an uploaded SQL file.
    
    This test is a dependency of `test_upload_COUNTER_data_via_Excel()` because the SQL files contains hardcoded primary key values based off the number of records that should be loaded by that test. The reason these tests aren't reversed is because if this test was first, and thus loading data into an empty database, it wouldn't be able to confirm that existing data isn't dropped upon file upload, as there would be no data to potentially drop.
    """
    SQL_file_path = TOP_NOLCAT_DIRECTORY / 'tests' / 'data' / 'insert_statements_test_file.sql'
    form_submissions = MultipartEncoder(
        fields={
            'COUNTER_data': (SQL_file_path.name, open(SQL_file_path, 'rb'), 'application/sql'),
        },
        encoding='utf-8',
    )
    header_value['Content-Type'] = form_submissions.content_type
    POST_response = client.post(
        '/ingest_usage/upload-COUNTER',
        follow_redirects=True,
        headers=header_value,
        data=form_submissions,
    )

    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'ingest_usage' / 'templates' / 'ingest_usage' / 'index.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title.string.encode('utf-8')
        HTML_file_page_title = file_soup.body.h1.string.encode('utf-8')
    check_relation_size = query_database(
        query=f"SELECT COUNT(*) FROM COUNTERData;",
        engine=engine,
    )
    if isinstance(check_relation_size, str):
        pytest.skip(database_function_skip_statements(check_relation_size))
    df = query_database(
        query="SELECT * FROM COUNTERData ORDER BY COUNTER_data_ID DESC LIMIT 7;",
        engine=engine,
    )
    if isinstance(df, str):
        pytest.skip(database_function_skip_statements(df))
    df = df.astype(COUNTERData.state_data_types())
    df = df.drop(columns='COUNTER_data_ID')
    insert_statement_data = pd.DataFrame(
        [  # These records are in reverse order from the SQL file because getting the last seven records requires a SQL query that places the most recently loaded (aka last) records at the top
            [3, "IR", "Winners and Losers: Some Paradoxes in Monetary History Resolved and Some Lessons Unlearned", "Duke University Press", None, "Duke University Press", "Will E. Mason", "1977-11-01", "VoR", "10.1215/00182702-9-4-476", "Silverchair:12922", None, None, None, None, "Article", None, 1977, "Controlled", "Regular", "History of Political Economy", None, None, None, "Journal", None, "Silverchair:1000052", None, "0018-2702", "1527-1919", None, "Total_Item_Investigations", "2020-07-01", 6, None],
            [3, "PR", None, None, None, "Duke University Press", None, None, None, None, None, None, None, None, None, "Book", None, None, None, "Regular", None, None, None, None, None, None, None, None, None, None, None, "Unique_Title_Requests", "2020-07-01", 2, None],
            [2, "TR", "Library Journal", "Library Journals, LLC", None, "Gale", None, None, None, None, "Gale:1273", None, "0363-0277", None, None, "Journal", "Article", 1998, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Unique_Item_Requests", "2020-07-01", 3, None],
            [1, "TR", "The Yellow Wallpaper", "Open Road Media", None, "EBSCOhost", None, None, None, None, "EBSCOhost:KBID:8016659", None, None, None, None, "Book", "Book", 2016, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Unique_Item_Investigations", "2020-07-01", 4, None],
            [1, "TR", "The Yellow Wallpaper", "Open Road Media", None, "EBSCOhost", None, None, None, None, "EBSCOhost:KBID:8016659", None, None, None, None, "Book", "Book", 2016, "Controlled", "Regular", None, None, None, None, None, None, None, None, None, None, None, "Total_Item_Investigations", "2020-07-01", 3, None],
            [0, "IR", "Where Function Meets Fabulous", "MSI Information Services", None, "ProQuest", "LJ", "2019-11-01", None, None, "ProQuest:2309469258", None, "0363-0277", None, None, "Journal", None, 2019, "Controlled", "Regular", "Library Journal", None, None, None, "Journal", None, "ProQuest:40955", None, "0363-0277", None, None, "Unique_Item_Investigations", "2020-07-01", 3, None],
            [0, "PR", None, None, None, "ProQuest", None, None, None, None, None, None, None, None, None, "Other", None, None, None, "Regular", None, None, None, None, None, None, None, None, None, None, None, "Unique_Item_Investigations", "2020-07-01", 77, None], 
        ],
        columns=["statistics_source_ID", "report_type", "resource_name", "publisher", "publisher_ID", "platform", "authors", "publication_date", "article_version", "DOI", "proprietary_ID", "ISBN", "print_ISSN", "online_ISSN", "URI", "data_type", "section_type", "YOP", "access_type", "access_method",  "parent_title", "parent_authors", "parent_publication_date", "parent_article_version", "parent_data_type", "parent_DOI", "parent_proprietary_ID", "parent_ISBN", "parent_print_ISSN", "parent_online_ISSN", "parent_URI", "metric_type", "usage_date", "usage_count", "report_creation_date"],
    )
    insert_statement_data = insert_statement_data.astype(COUNTERData.state_data_types())
    insert_statement_data["publication_date"] = pd.to_datetime(insert_statement_data["publication_date"])
    insert_statement_data["parent_publication_date"] = pd.to_datetime(insert_statement_data["parent_publication_date"])
    insert_statement_data["usage_date"] = pd.to_datetime(insert_statement_data["usage_date"])
    insert_statement_data["report_creation_date"] = pd.to_datetime(insert_statement_data["report_creation_date"])

    assert POST_response.status == "200 OK"
    assert HTML_file_title in POST_response.data
    assert HTML_file_page_title in POST_response.data
    assert extract_value_from_single_value_df(check_relation_size) > 7  # This confirms the table wasn't dropped and recreated, which would happen if all SQL in the test file was executed
    assert_frame_equal(df, insert_statement_data)


def test_match_direct_SUSHI_harvest_result(engine, caplog):
    """Tests pulling a set number of records from the `COUNTERData` relation and modifying them so they match the output of the `StatisticsSources._harvest_R5_SUSHI()` method.
    
    This function's call of a class method from `nolcat.models` means it's in `tests.conftest`, which lacks its own test module. The function is tested here because the immediately preceding test function loads exactly seven records into the `COUNTERData` relation, and so if it passes, the won't fail due to the last records in `COUNTERData` not containing the expected data.
    """
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()`
    df = match_direct_SUSHI_harvest_result(engine, 7, caplog)
    match_result_df = pd.DataFrame(
        [
            [0, "PR", None, None, "ProQuest", None, None, None, None, None, None, "Other", None, None, None, "Regular", None, None, None, None, None, "Unique_Item_Investigations", "2020-07-01", 77],
            [0, "IR", "Where Function Meets Fabulous", "MSI Information Services", "ProQuest", "LJ", "2019-11-01", None, None, "ProQuest:2309469258", "0363-0277", "Journal", None, 2019, "Controlled", "Regular", "Library Journal", "Journal", "ProQuest:40955", "0363-0277", None, "Unique_Item_Investigations", "2020-07-01", 3],
            [1, "TR", "The Yellow Wallpaper", "Open Road Media", "EBSCOhost", None, None, None, None, "EBSCOhost:KBID:8016659", None, "Book", "Book", 2016, "Controlled", "Regular", None, None, None, None, None, "Total_Item_Investigations", "2020-07-01", 3],
            [1, "TR", "The Yellow Wallpaper", "Open Road Media", "EBSCOhost", None, None, None, None, "EBSCOhost:KBID:8016659", None, "Book", "Book", 2016, "Controlled", "Regular", None, None, None, None, None, "Unique_Item_Investigations", "2020-07-01", 4],
            [2, "TR", "Library Journal", "Library Journals, LLC", "Gale", None, None, None, None, "Gale:1273", "0363-0277", "Journal", "Article", 1998, "Controlled", "Regular", None, None, None, None, None, "Unique_Item_Requests", "2020-07-01", 3],
            [3, "PR", None, None, "Duke University Press", None, None, None, None, None, None, "Book", None, None, None, "Regular", None, None, None, None, None, "Unique_Title_Requests", "2020-07-01", 2],
            [3, "IR", "Winners and Losers: Some Paradoxes in Monetary History Resolved and Some Lessons Unlearned", "Duke University Press", "Duke University Press", "Will E. Mason", "1977-11-01", "VoR", "10.1215/00182702-9-4-476", "Silverchair:12922", None, "Article", None, 1977, "Controlled", "Regular", "History of Political Economy", "Journal", "Silverchair:1000052", "0018-2702", "1527-1919", "Total_Item_Investigations", "2020-07-01", 6],
        ],
        columns=["statistics_source_ID", "report_type", "resource_name", "publisher", "platform", "authors", "publication_date", "article_version", "DOI", "proprietary_ID", "print_ISSN", "data_type", "section_type", "YOP", "access_type", "access_method", "parent_title", "parent_data_type", "parent_proprietary_ID", "parent_print_ISSN", "parent_online_ISSN", "metric_type", "usage_date", "usage_count"],
    )
    match_result_df = match_result_df.astype({k: v for (k, v) in COUNTERData.state_data_types().items() if k in match_result_df.columns.tolist()})
    match_result_df['usage_date'] = pd.to_datetime(match_result_df['usage_date'])
    match_result_df["publication_date"] = pd.to_datetime(
        match_result_df["publication_date"],
        errors='coerce',  # Changes the null values to the date dtype's null value `NaT`
    )
    assert_frame_equal(match_result_df, df)


def test_GET_request_for_harvest_SUSHI_statistics(engine, client, caplog):
    """Tests that the page for making custom SUSHI calls can be successfully GET requested and that the response properly populates with the requested data."""
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()`
    
    page = client.get(
        '/ingest_usage/harvest',
        follow_redirects=True,
    )
    GET_soup = BeautifulSoup(page.data, 'lxml')
    GET_response_title = GET_soup.head.title
    GET_response_page_title = GET_soup.body.h1
    GET_select_field_options = []
    for child in GET_soup.find(name='select', id='statistics_source').children:
        GET_select_field_options.append((
            int(child['value']),
            str(child.string),
        ))

    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'ingest_usage' / 'templates' / 'ingest_usage' / 'make-SUSHI-call.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title
        HTML_file_page_title = file_soup.body.h1
    df = query_database(
        query="SELECT statistics_source_ID, statistics_source_name FROM statisticsSources WHERE statistics_source_retrieval_code IS NOT NULL ORDER BY statistics_source_name;",
        engine=engine,
    )
    if isinstance(df, str):
        pytest.skip(database_function_skip_statements(df))
    db_select_field_options = list(df.itertuples(index=False, name=None))

    assert page.status == "200 OK"
    assert HTML_file_title == GET_response_title
    assert HTML_file_page_title == GET_response_page_title
    assert GET_select_field_options == db_select_field_options


def test_harvest_SUSHI_statistics(engine, client, most_recent_month_with_usage, header_value, caplog):
    """Tests making a SUSHI API call based on data entered into the `ingest_usage.SUSHIParametersForm` form.
    
    The SUSHI API has no test values, so testing SUSHI calls requires using actual SUSHI credentials. Since the data in the form being submitted with the POST request is ultimately used to make a SUSHI call, the `StatisticsSources.statistics_source_retrieval_code` values used in the test data--`1`, `2`, and `3`--must correspond to values in the SUSHI credentials JSON; for testing purposes, these values don't need to make SUSHI calls to the statistics source designated by the test data's StatisticsSources record--any valid credential set will work. Ultimately, this test only checks that the POST action is successful, not that the SUSHI harvest is; testing that functionality is covered by the `tests.test_SUSHICallAndResponse` module.
    """
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `first_new_PK_value()` called in `StatisticsSources.collect_usage_statistics()` and for `query_database()`
    caplog.set_level(logging.INFO, logger='nolcat.SUSHI_call_and_response')  # For `make_SUSHI_call()` called in `StatisticsSources._harvest_R5_SUSHI()` called in `StatisticsSources.collect_usage_statistics()`
    caplog.set_level(logging.INFO, logger='nolcat.convert_JSON_dict_to_dataframe')  # For `create_dataframe()` called in `StatisticsSources._harvest_single_report()` called in `StatisticsSources._harvest_R5_SUSHI()` called in `StatisticsSources.collect_usage_statistics()`
    
    df = query_database(
        query="SELECT statistics_source_ID FROM statisticsSources WHERE statistics_source_retrieval_code IS NOT NULL;",
        engine=engine,
    )
    if isinstance(df, str):
        pytest.skip(database_function_skip_statements(df))
    primary_key_list = change_single_field_dataframe_into_series(df).astype('string').to_list()
    form_input = {
        'statistics_source': choice(primary_key_list),
        'begin_date': most_recent_month_with_usage[0],
        'end_date': most_recent_month_with_usage[1],
    }
    POST_response = client.post(
        f'/ingest_usage/harvest/test',
        follow_redirects=True,
        headers=header_value,
        data=form_input,
    )

    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'ingest_usage' / 'templates' / 'ingest_usage' / 'index.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title.string.encode('utf-8')
        HTML_file_page_title = file_soup.body.h1.string.encode('utf-8')
    assert POST_response.history[0].status == "302 FOUND"  # This confirms there was a redirect
    assert POST_response.status == "200 OK"
    assert HTML_file_title in POST_response.data
    assert HTML_file_page_title in POST_response.data


def test_GET_request_for_upload_non_COUNTER_reports(engine, client, caplog):
    """Tests that the page for uploading and saving non-COUNTER compliant files can be successfully GET requested and that the response properly populates with the requested data."""
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `change_single_field_dataframe_into_series()` and `query_database()`
    
    page = client.get(
        '/ingest_usage/upload-non-COUNTER',
        follow_redirects=True,
    )
    GET_soup = BeautifulSoup(page.data, 'lxml')
    GET_response_title = GET_soup.head.title
    GET_response_page_title = GET_soup.body.h1
    GET_select_field_options = []
    for child in GET_soup.find(name='select', id='AUCT_option').children:
        GET_select_field_options.append((
            literal_eval(child['value']),
            str(child.string),
        ))

    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'ingest_usage' / 'templates' / 'ingest_usage' / 'upload-non-COUNTER-usage.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title
        HTML_file_page_title = file_soup.body.h1
    df = query_database(
        query=f"""
            SELECT
                annualUsageCollectionTracking.AUCT_statistics_source,
                annualUsageCollectionTracking.AUCT_fiscal_year,
                statisticsSources.statistics_source_name,
                fiscalYears.fiscal_year
            FROM annualUsageCollectionTracking
            JOIN statisticsSources ON statisticsSources.statistics_source_ID=annualUsageCollectionTracking.AUCT_statistics_source
            JOIN fiscalYears ON fiscalYears.fiscal_year_ID=annualUsageCollectionTracking.AUCT_fiscal_year
            WHERE
                annualUsageCollectionTracking.usage_is_being_collected=true AND
                annualUsageCollectionTracking.is_COUNTER_compliant=false AND
                annualUsageCollectionTracking.usage_file_path IS NULL AND
                (
                    annualUsageCollectionTracking.collection_status='Collection not started' OR
                    annualUsageCollectionTracking.collection_status='Collection in process (see notes)' OR
                    annualUsageCollectionTracking.collection_status='Collection issues requiring resolution'
                );
        """,
        engine=engine,
    )
    if isinstance(df, str):
        pytest.skip(database_function_skip_statements(df))
    db_select_field_options = create_AUCT_SelectField_options(df)

    assert page.status == "200 OK"
    assert HTML_file_title == GET_response_title
    assert HTML_file_page_title == GET_response_page_title
    assert GET_select_field_options == db_select_field_options


def test_upload_non_COUNTER_reports(engine, client, header_value, tmp_path, non_COUNTER_AUCT_object_before_upload, path_to_sample_file, caplog):
    """Tests saving files uploaded to `ingest_usage.UsageFileForm` and updating the corresponding AUCT record."""
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `upload_file_to_S3_bucket()`

    #Section: Create Form Submission
    if path_to_sample_file.suffix == '.json':
        mimetype = 'application/json'
    else:
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    form_submissions = MultipartEncoder(
        fields={
            'AUCT_option': f"({non_COUNTER_AUCT_object_before_upload.AUCT_statistics_source}, {non_COUNTER_AUCT_object_before_upload.AUCT_fiscal_year})",  # The string of a tuple is what gets returned by the actual form submission in Flask; trial and error determined that for tests to pass, that was also the value that needed to be passed to the POST method
            'usage_file': (path_to_sample_file.name, open(path_to_sample_file, 'rb'), mimetype),
        },
        encoding='utf-8',
    )

    #Section: Confirm HTTP POST
    #Subsection: Perform Test Actions
    header_value['Content-Type'] = form_submissions.content_type
    POST_response = client.post(
        f'/ingest_usage/upload-non-COUNTER/test',
        follow_redirects=True,
        headers=header_value,
        data=form_submissions,
    )

    #Subsection: Assert Statements
    file_name = f"{non_COUNTER_AUCT_object_before_upload.AUCT_statistics_source}_{non_COUNTER_AUCT_object_before_upload.AUCT_fiscal_year}{path_to_sample_file.suffix}"
    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'ingest_usage' / 'templates' / 'ingest_usage' / 'index.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title.string.encode('utf-8')
        HTML_file_page_title = file_soup.body.h1.string.encode('utf-8')
    assert POST_response.history[0].status == "302 FOUND"  # This confirms there was a redirect
    assert POST_response.status == "200 OK"
    assert HTML_file_title in POST_response.data
    assert HTML_file_page_title in POST_response.data
    assert re.search(r"Usage file for .+--FY \d{4} uploaded successfully\.", prepare_HTML_page_for_comparison(POST_response.data))
    
    #Section: Confirm Successful Database Update
    df = query_database(
        query=f"SELECT collection_status, usage_file_path FROM annualUsageCollectionTracking WHERE AUCT_statistics_source = {non_COUNTER_AUCT_object_before_upload.AUCT_statistics_source} AND AUCT_fiscal_year = {non_COUNTER_AUCT_object_before_upload.AUCT_fiscal_year};",
        engine=engine,
    )
    assert df.at[0,'collection_status'] == 'Collection complete'
    assert df.at[0,'usage_file_path'] == file_name

    #Section: Confirm Successful S3 Upload
    list_objects_response = s3_client.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=f"{PATH_WITHIN_BUCKET_FOR_TESTS}{non_COUNTER_AUCT_object_before_upload.AUCT_statistics_source}_{non_COUNTER_AUCT_object_before_upload.AUCT_fiscal_year}",
    )
    log.debug(f"Raw contents of `{BUCKET_NAME}/{PATH_WITHIN_BUCKET_FOR_TESTS}{non_COUNTER_AUCT_object_before_upload.AUCT_statistics_source}_{non_COUNTER_AUCT_object_before_upload.AUCT_fiscal_year}` (type {type(list_objects_response)}):\n{format_list_for_stdout(list_objects_response)}.")
    files_in_bucket = []
    bucket_contents = list_objects_response.get('Contents')
    if bucket_contents:
        for contents_dict in bucket_contents:
            files_in_bucket.append(contents_dict['Key'])
        files_in_bucket = [name.replace(f"{PATH_WITHIN_BUCKET_FOR_TESTS}", "") for name in files_in_bucket]
        assert file_name in files_in_bucket
    else:
        assert False  # Nothing in bucket
    download_location = tmp_path / file_name
    s3_client.download_file(
        Bucket=BUCKET_NAME,
        Key=PATH_WITHIN_BUCKET_FOR_TESTS + file_name,
        Filename=download_location,
    )
    assert cmp(path_to_sample_file, download_location)