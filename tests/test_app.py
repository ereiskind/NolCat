"""This module contains the tests for setting up the Flask web app, which roughly correspond to the functions in `nolcat\\app.py`. Each blueprint's own `views.py` module has a corresponding test module."""
########## Passing 2024-12-19 ##########

import pytest
import logging
from datetime import date
from datetime import datetime
from random import choice
from filecmp import cmp
from bs4 import BeautifulSoup
import pandas as pd
from pandas.testing import assert_frame_equal
from pandas.testing import assert_series_equal
import sqlalchemy
import flask

# `conftest.py` fixtures are imported automatically
from conftest import prepare_HTML_page_for_comparison
from nolcat.app import *
from nolcat.models import *
from nolcat.statements import *

log = logging.getLogger(__name__)


#Section: Test Flask Factory Pattern
def test_flask_app_creation(app):
    """Tests that the fixture for creating the Flask web app object returns a Flask object for `nolcat.app`."""
    assert isinstance(app, flask.app.Flask)
    assert app.__dict__['name'] == 'nolcat.app'


def test_flask_client_creation(client):
    """Tests that the fixture for creating the Flask client returned a FlaskClient object for `nolcat.app`."""
    assert isinstance(client, flask.testing.FlaskClient)
    assert isinstance(client.__dict__['application'], flask.app.Flask)
    assert client.__dict__['application'].__dict__['name'] == 'nolcat.app'


def test_SQLAlchemy_engine_creation(engine):
    """Tests that the fixture for creating the SQLAlchemy engine returned an engine object for connecting to the NoLCAT database."""
    assert isinstance(engine, sqlalchemy.engine.base.Engine)
    assert isinstance(engine.__dict__['url'], sqlalchemy.engine.url.URL)
    assert str(engine.__dict__['url']) == f'mysql://{DATABASE_USERNAME}:***@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_SCHEMA_NAME}'  # The `sqlalchemy.engine.url.URL` changes the password to `***` for stdout


def test_homepage(client):
    """Tests that the homepage can be successfully GET requested and that the response matches the file being used."""
    page = client.get('/')
    GET_soup = BeautifulSoup(page.data, 'lxml')
    GET_response_title = GET_soup.head.title
    GET_response_page_title = GET_soup.body.h1
    
    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'templates' / 'index.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title
        HTML_file_page_title = file_soup.body.h1
    
    assert page.status == "200 OK"
    assert HTML_file_title == GET_response_title
    assert HTML_file_page_title == GET_response_page_title


def test_404_page(client):
    """Tests that the unassigned route '/404' goes to the 404 page."""
    nonexistent_page = client.get('/404')
    GET_soup = BeautifulSoup(nonexistent_page.data, 'lxml')
    GET_response_title = GET_soup.head.title
    GET_response_page_title = GET_soup.body.h1
    
    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'templates' / '404.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title
        HTML_file_page_title = file_soup.body.h1
    
    assert nonexistent_page.status == "404 NOT FOUND"
    assert HTML_file_title == GET_response_title
    assert HTML_file_page_title == GET_response_page_title


@pytest.mark.dependency()
def test_load_data_into_database(engine, vendors_relation):
    """Tests loading data into a relation.

    Testing the helper function for loading data into the database also confirms that the database and program are connected.
    """
    result = load_data_into_database(
        df=vendors_relation,
        relation='vendors',
        engine=engine,
        index_field_name='vendor_ID',
    )
    regex_match_object = load_data_into_database_success_regex().fullmatch(result)
    assert regex_match_object is not None
    assert int(regex_match_object.group(1)) == 8
    assert regex_match_object.group(2) == "vendors"


@pytest.mark.dependency(depends=['test_load_data_into_database'])
def test_query_database(engine, vendors_relation):
    """Tests getting data from the database through a SQL query.

    This test performs a `SELECT *` query on the relation that had data loaded into it in the previous test, confirming that the function works and that the database and program are connected to allow CRUD operations.
    """
    retrieved_vendors_data = query_database(
        query="SELECT * FROM vendors;",
        engine=engine,
        index='vendor_ID',
    )
    retrieved_vendors_data = retrieved_vendors_data.astype(Vendors.state_data_types())
    assert_frame_equal(vendors_relation, retrieved_vendors_data)


@pytest.mark.dependency(depends=['test_query_database'])
def test_loading_connected_data_into_other_relation(engine, statisticsSources_relation):
    """Tests loading data into a second relation connected with foreign keys and performing a joined query.

    This test uses second dataframe to load data into a relation that has a foreign key field that corresponds to the primary keys of the relation loaded with data in `test_load_data_into_database`, then tests that the data load and the primary key-foreign key connection worked by performing a `JOIN` query and comparing it to a manually constructed dataframe containing that same data.
    """
    df_dtypes = {
        "statistics_source_name": StatisticsSources.state_data_types()['statistics_source_name'],
        "statistics_source_retrieval_code": StatisticsSources.state_data_types()['statistics_source_retrieval_code'],
        "vendor_name": Vendors.state_data_types()['vendor_name'],
        "alma_vendor_code": Vendors.state_data_types()['alma_vendor_code'],
    }

    check = load_data_into_database(
        df=statisticsSources_relation,
        relation='statisticsSources',
        engine=engine,
        index_field_name='statistics_source_ID',
    )
    if not load_data_into_database_success_regex().fullmatch(check):
        pytest.skip(database_function_skip_statements(check))
    retrieved_data = query_database(
        query="""
            SELECT
                statisticsSources.statistics_source_ID,
                statisticsSources.statistics_source_name,
                statisticsSources.statistics_source_retrieval_code,
                vendors.vendor_name,
                vendors.alma_vendor_code
            FROM statisticsSources
            JOIN vendors ON statisticsSources.vendor_ID=vendors.vendor_ID
            ORDER BY statisticsSources.statistics_source_ID;
        """,
        engine=engine,
        index='statistics_source_ID'
        # Each stats source appears only once, so the PKs can still be used--remember that pandas doesn't have a problem with duplication in the index
    )
    if isinstance(retrieved_data, str):
        pytest.skip(database_function_skip_statements(retrieved_data))
    retrieved_data = retrieved_data.astype(df_dtypes)

    expected_output_data = pd.DataFrame(
        [
            ["ProQuest", "1", "ProQuest", None],
            ["EBSCOhost", "2", "EBSCO", None],
            ["Gale Cengage Learning", None, "Gale", None],
            ["Duke UP", "3", "Duke UP", None],
            ["iG Library/Business Expert Press (BEP)", None, "iG Publishing/BEP", None],
            ["DemographicsNow", None, "Gale", None],
            ["Ebook Central", None, "ProQuest", None],
            ["Peterson's Career Prep", None, "Gale", None],
            ["Peterson's Test Prep", None, "Gale", None],
            ["Peterson's Prep", None, "Gale", None],
            ["Pivot", None, "ProQuest", None],
            ["Ulrichsweb", None, "ProQuest", None],
        ],
        columns=["statistics_source_name", "statistics_source_retrieval_code", "vendor_name", "alma_vendor_code"],
    )
    expected_output_data.index.name = "statistics_source_ID"
    expected_output_data = expected_output_data.astype(df_dtypes)
    assert_frame_equal(retrieved_data, expected_output_data)


def test_download_file(client, path_to_sample_file):  #ToDo: If method for interacting with host workstation's file system can be established, add `default_download_folder`
    """Tests the route enabling file downloads."""
    page = client.get(
        f'/download/{path_to_sample_file}',
        follow_redirects=True,
    )
    #ToDo: If method for interacting with host workstation's file system can be established, `with Path(default_download_folder, path_to_sample_file.name) as file: downloaded_file = file.read()`

    assert page.status == "200 OK"
    assert page.history[0].status == "308 PERMANENT REDIRECT"
    assert page.headers.get('Content-Disposition') == f'attachment; filename={path_to_sample_file.name}'
    assert page.headers.get('Content-Type') == file_extensions_and_mimetypes()[path_to_sample_file.suffix]
    #ToDo: If method for interacting with host workstation's file system can be established, `assert path_to_sample_file.name in [file_name for file_name in default_download_folder.iterdir()]
    #ToDo: If method for interacting with host workstation's file system can be established,
    #if "bin" in path_to_sample_file.parts:
    #    with path_to_sample_file.open('rb') as file:
    #        assert file.read() == downloaded_file
    #else:
    #    with path_to_sample_file.open('rt') as file:
    #        assert file.read() == downloaded_file


# Testing of `nolcat.app.check_if_data_already_in_COUNTERData()` in `tests.test_StatisticsSources.test_check_if_data_already_in_COUNTERData()`


#Section: Test Helper Functions
@pytest.mark.dependency(depends=['test_load_data_into_database'])
def test_first_new_PK_value():
    """Tests the retrieval of a relation's next primary key value."""
    assert first_new_PK_value('vendors') == 8


def test_change_single_field_dataframe_into_series():
    """Tests the transformation of a dataframe with a single field into a series."""
    mx = pd.MultiIndex.from_frame(
        pd.DataFrame(
            [
                [0, "a"],
                [0, "b"],
                [1, "a"],
                [1, "c"],
            ],
            columns=["numbers", "letters"],
        )
    )
    df = pd.DataFrame(
        [[1], [2], [3], [4]],
        index=mx,
        dtype='int64',
        columns=["test"],
    )
    s = pd.Series(
        [1, 2, 3, 4],
        index=mx,
        dtype='int64',
        name="test",
    )
    assert_series_equal(change_single_field_dataframe_into_series(df), s)


def test_restore_boolean_values_to_boolean_field():
    """Tests the replacement of MySQL's single-bit int data type with pandas's `boolean` data type."""
    tinyint_s = pd.Series(
        [1, 0, pd.NA, 1],
        dtype='Int8',  # pandas' single-bit int data type is used because it allows nulls; using the Python data type raises an error
        name="boolean_values",
    )
    boolean_s = pd.Series(
        [True, False, pd.NA, True],
        dtype='boolean',
        name="boolean_values",
    )
    assert_series_equal(restore_boolean_values_to_boolean_field(tinyint_s), boolean_s)


def test_upload_file_to_S3_bucket(tmp_path, path_to_sample_file, remove_file_from_S3):  # `remove_file_from_S3()` not called but used to remove file loaded during test
    """Tests uploading files to a S3 bucket."""
    logging_message = upload_file_to_S3_bucket(
        path_to_sample_file,
        path_to_sample_file.name,
        bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
    )
    log.debug(logging_message)
    if not upload_file_to_S3_bucket_success_regex().fullmatch(logging_message):
        assert False  # Entering this block means the function that's being tested raised an error, so continuing with the test won't provide anything meaningful
    list_objects_response = s3_client.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=PATH_WITHIN_BUCKET_FOR_TESTS,
    )
    log.debug(f"Raw contents of `{BUCKET_NAME}/{PATH_WITHIN_BUCKET_FOR_TESTS}` (type {type(list_objects_response)}):\n{format_list_for_stdout(list_objects_response)}.")
    bucket_contents = []
    for contents_dict in list_objects_response['Contents']:
        bucket_contents.append(contents_dict['Key'])
    bucket_contents = [file_name.replace(f"{PATH_WITHIN_BUCKET_FOR_TESTS}", "") for file_name in bucket_contents]
    assert path_to_sample_file.name in bucket_contents
    download_location = tmp_path / path_to_sample_file.name
    s3_client.download_file(
        Bucket=BUCKET_NAME,
        Key=PATH_WITHIN_BUCKET_FOR_TESTS + path_to_sample_file.name,
        Filename=download_location,
    )
    assert cmp(path_to_sample_file, download_location)


def test_create_AUCT_SelectField_options():
    """Tests the transformation of a dataframe with four fields into a list for the `SelectField.choices` attribute with the characteristics described in the docstring of the function being tested."""
    df = pd.DataFrame(
        [
            [1, 1, "First Statistics Source", "2017"],
            [2, 1, "Second Statistics Source", "2017"],
            [1, 2, "First Statistics Source", "2018"],
            [3, 2, "Third Statistics Source", "2018"],
        ],
        columns=["AUCT_statistics_source", "AUCT_fiscal_year", "statistics_source_name", "fiscal_year"],
    )
    result_list = [
        (
            (1, 1),
            "First Statistics Source--FY 2017",
        ),
        (
            (2, 1),
            "Second Statistics Source--FY 2017",
        ),
        (
            (1, 2),
            "First Statistics Source--FY 2018",
        ),
        (
            (3, 2),
            "Third Statistics Source--FY 2018",
        ),
    ]
    assert create_AUCT_SelectField_options(df) == result_list


# `test_check_if_data_already_in_COUNTERData()` and its related fixtures are in `tests.test_StatisticsSources` because the test requires the test data to be loaded into the `COUNTERData` relation while every other test function in this module relies upon the test suite starting with an empty database.


def test_truncate_longer_lines():
    """Tests truncating aly string longer than 50 characters to just 50 characters including the ellipsis at the end."""
    assert truncate_longer_lines("This is shorter than 50 characters.") == "This is shorter than 50 characters."
    assert truncate_longer_lines("This is muuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuch longer than 50 characters.") == "This is muuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuch lon..."


@pytest.fixture
def vendors_relation_after_test_update_database():
    """The test data for the `vendors` relation featuring the change to be made in the `test_update_database()` test.

    Yields:
        dataframe: data matching the updated `vendors` relation
    """
    df = pd.DataFrame(
        [
            ["ProQuest", None],
            ["EBSCO", None],
            ["Gale", "CODE"],
            ["iG Publishing/BEP", None],
            ["Ebook Library", None],
            ["Ebrary", None],
            ["MyiLibrary", None],
            ["Duke UP", None],
        ],
        columns=["vendor_name", "alma_vendor_code"],
    )
    df.index.name = "vendor_ID"
    df = df.astype(Vendors.state_data_types())
    yield df


@pytest.mark.dependency(depends=['test_load_data_into_database'])
def test_update_database(engine, vendors_relation_after_test_update_database):
    """Tests updating data in the database through a SQL update statement."""
    update_result = update_database(
        update_statement=f"UPDATE vendors SET alma_vendor_code='CODE' WHERE vendor_ID=2;",
        engine=engine,
    )
    retrieved_updated_vendors_data = query_database(
        query="SELECT * FROM vendors;",
        engine=engine,
        index='vendor_ID',
    )
    if isinstance(retrieved_updated_vendors_data, str):
        pytest.skip(database_function_skip_statements(retrieved_updated_vendors_data))
    retrieved_updated_vendors_data = retrieved_updated_vendors_data.astype(Vendors.state_data_types())
    assert update_database_success_regex().fullmatch(update_result).group(0) == update_result
    assert_frame_equal(vendors_relation_after_test_update_database, retrieved_updated_vendors_data)


@pytest.fixture
def vendors_relation_after_test_update_database_with_insert_statement():
    """The test data for the `vendors` relation featuring the changes to be made in the `test_update_database_with_insert_statement()` test.

    Yields:
        dataframe: data matching the updated `vendors` relation
    """
    df = pd.DataFrame(
        [
            ["ProQuest", None],
            ["EBSCO", None],
            ["Gale", "CODE"],
            ["iG Publishing/BEP", None],
            ["Ebook Library", None],
            ["Ebrary", None],
            ["MyiLibrary", None],
            ["Duke UP", None],
            ["A Vendor", None],
            ["Another Vendor", "1"],
        ],
        columns=["vendor_name", "alma_vendor_code"],
    )
    df.index.name = "vendor_ID"
    df = df.astype(Vendors.state_data_types())
    yield df


@pytest.mark.dependency(depends=['test_load_data_into_database'])
def test_update_database_with_insert_statement(engine, vendors_relation_after_test_update_database_with_insert_statement):
    """Tests adding records to the database through a SQL insert statement."""
    update_result = update_database(
        update_statement=f"INSERT INTO vendors VALUES (8, 'A Vendor', NULL), (9, 'Another Vendor', '1');",
        engine=engine,
    )
    retrieved_updated_vendors_data = query_database(
        query="SELECT * FROM vendors;",
        engine=engine,
        index='vendor_ID',
    )
    if isinstance(retrieved_updated_vendors_data, str):
        pytest.skip(database_function_skip_statements(retrieved_updated_vendors_data))
    retrieved_updated_vendors_data = retrieved_updated_vendors_data.astype(Vendors.state_data_types())
    assert update_database_success_regex().fullmatch(update_result).group(0) == update_result
    assert_frame_equal(vendors_relation_after_test_update_database_with_insert_statement, retrieved_updated_vendors_data)


def test_prepare_HTML_page_for_comparison():
    """Tests creating an Unicode string from HTML page data."""
    assert prepare_HTML_page_for_comparison(b'<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta http-equiv="X-UA-Compatible" content="IE=edge">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Ingest Usage</title>\n</head>\n<body>\n    <h1>Ingest Usage Homepage</h1>\n\n    \n        \n            <p>[{&#39;DR&#39;: [], &#39;IR&#39;: [], &#39;PR&#39;: [], &#39;reports&#39;: [], &#39;status&#39;: []}]</p>\n        \n    \n\n    <ul>\n        <li>To upload a tabular COUNTER report, <a href="/ingest_usage/upload-COUNTER">click here</a>.</li>\n        <li>To make a SUSHI call, <a href="/ingest_usage/harvest">click here</a>.</li>\n        <li>To save a non-COUNTER usage file, <a href="/ingest_usage/upload-non-COUNTER">click here</a>.</li>\n    </ul>\n\n    <p>To return to the homepage, <a href="/">click here</a>.</p>\n</body>\n</html>') == '<!DOCTYPE html>\\n<html lang="en">\\n<head>\\n    <meta charset="UTF-8">\\n    <meta http-equiv="X-UA-Compatible" content="IE=edge">\\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\\n    <title>Ingest Usage</title>\\n</head>\\n<body>\\n    <h1>Ingest Usage Homepage</h1>\\n\\n    \\n        \\n            <p>[{\'DR\': [], \'IR\': [], \'PR\': [], \'reports\': [], \'status\': []}]</p>\\n        \\n    \\n\\n    <ul>\\n        <li>To upload a tabular COUNTER report, <a href="/ingest_usage/upload-COUNTER">click here</a>.</li>\\n        <li>To make a SUSHI call, <a href="/ingest_usage/harvest">click here</a>.</li>\\n        <li>To save a non-COUNTER usage file, <a href="/ingest_usage/upload-non-COUNTER">click here</a>.</li>\\n    </ul>\\n\\n    <p>To return to the homepage, <a href="/">click here</a>.</p>\\n</body>\\n</html>'


@pytest.fixture(params=[
    {'Report_Header': {'Created': '2023-10-17T21:13:26Z','Created_By': 'ProQuest','Customer_ID': '0000','Report_ID': 'PR','Release': '5','Report_Name': 'Platform Master Report','Institution_Name': 'FLORIDA STATE UNIVERSITY','Institution_ID': [{'Type': 'Proprietary','Value': 'ProQuest:0000'}],'Report_Filters': [{'Name': 'Platform','Value': 'ProQuest'},{'Name': 'Begin_Date','Value': '2022-07-01'},{'Name': 'End_Date','Value': '2023-08-31'},{'Name': 'Data_Type','Value': 'Book|Journal'}],'Report_Attributes': [{'Name': 'Attributes_To_Show','Value': 'Data_Type|Access_Method'}]},'Report_Items': [{'Platform': 'ProQuest','Data_Type': 'Book','Access_Method': 'Regular','Performance': [{'Period': {'Begin_Date': '2022-07-01','End_Date': '2022-07-31'},'Instance': [{'Metric_Type': 'Total_Item_Investigations','Count': 8},{'Metric_Type': 'Total_Item_Requests','Count': 9}]},{'Period': {'Begin_Date': '2022-08-01','End_Date': '2022-08-31'},'Instance': [{'Metric_Type': 'Total_Item_Investigations','Count': 2},{'Metric_Type': 'Total_Item_Requests','Count': 12}]}]},{'Platform': 'ProQuest','Data_Type': 'Journal','Access_Method': 'Regular','Performance': [{'Period': {'Begin_Date': '2022-07-01','End_Date': '2022-07-31'},'Instance': [{'Metric_Type': 'Total_Item_Investigations','Count': 53},{'Metric_Type': 'Total_Item_Requests','Count': 89}]},{'Period': {'Begin_Date': '2022-08-01','End_Date': '2022-08-31'},'Instance': [{'Metric_Type': 'Total_Item_Investigations','Count': 77},{'Metric_Type': 'Total_Item_Requests','Count': 92}]}]}]},
    "{'Report_Header': {'Created': '2023-10-17T21:13:26Z','Created_By': 'ProQuest','Customer_ID': '0000','Report_ID': 'PR','Release': '5','Report_Name': 'Platform Master Report','Institution_Name': 'FLORIDA STATE UNIVERSITY','Institution_ID': [{'Type': 'Proprietary','Value': 'ProQuest:0000'}],'Report_Filters': [{'Name': 'Platform','Value': 'ProQuest'},{'Name': 'Begin_Date','Value': '2022-07-01'},{'Name': 'End_Date','Value': '2023-08-31'},{'Name': 'Data_Type','Value': 'Book|Journal'}],'Report_Attributes': [{'Name': 'Attributes_To_Show','Value': 'Data_Type|Access_Method'}]},'Report_Items': [{'Platform': 'ProQuest','Data_Type': 'Book','Access_Method': 'Regular','Performance': [{'Period': {'Begin_Date': '2022-07-01','End_Date': '2022-07-31'},'Instance': [{'Metric_Type': 'Total_Item_Investigations','Count': 8},{'Metric_Type': 'Total_Item_Requests','Count': 9}]},{'Period': {'Begin_Date': '2022-08-01','End_Date': '2022-08-31'},'Instance': [{'Metric_Type': 'Total_Item_Investigations','Count': 2},{'Metric_Type': 'Total_Item_Requests','Count': 12}]}]},{'Platform': 'ProQuest','Data_Type': 'Journal','Access_Method': 'Regular','Performance': [{'Period': {'Begin_Date': '2022-07-01','End_Date': '2022-07-31'},'Instance': [{'Metric_Type': 'Total_Item_Investigations','Count': 53},{'Metric_Type': 'Total_Item_Requests','Count': 89}]},{'Period': {'Begin_Date': '2022-08-01','End_Date': '2022-08-31'},'Instance': [{'Metric_Type': 'Total_Item_Investigations','Count': 77},{'Metric_Type': 'Total_Item_Requests','Count': 92}]}]}]}",
])
def file_name_stem_and_data(request, most_recent_month_with_usage):
    """Provides the contents and name stem for the file in `test_save_unconverted_data_via_upload()`, then removes that file from S3 after the test runs.

    Args:
        request (dict or str): the contents of the file that will be saved to S3

    Yields:
        tuple: the stem of the name under which the file will be saved in S3 (str); the data that will be in the file saved to S3 (dict or str)
    """
    data = request.param
    log.debug(f"In `remove_file_from_S3_with_yield()`, the `data` is {data}.")
    file_name_stem = f"{choice(('P', 'D', 'T', 'I'))}R_{most_recent_month_with_usage[0].strftime('%Y-%m')}_{most_recent_month_with_usage[1].strftime('%Y-%m')}_{datetime.now().strftime(S3_file_name_timestamp())}"  # This is the format used for usage reports, which are the most frequently type of saved report
    log.info(f"In `remove_file_from_S3_with_yield()`, the `file_name_stem` is {file_name_stem}.")
    yield (file_name_stem, data)
    if isinstance(data, dict):
        file_name = file_name_stem + '.json'
    else:
        file_name = file_name_stem + '.txt'
    try:
        s3_client.delete_object(
            Bucket=BUCKET_NAME,
            Key=PATH_WITHIN_BUCKET_FOR_TESTS + file_name
        )
    except botocore.exceptions as error:
        log.error(f"Trying to remove file `{file_name}` from the S3 bucket raised {error}.")


def test_save_unconverted_data_via_upload(file_name_stem_and_data):
    """Tests saving data that can't be transformed for loading into the database to a file in S3."""
    file_name_stem, data = file_name_stem_and_data
    logging_message = save_unconverted_data_via_upload(
        data=data,
        file_name_stem=file_name_stem,
        bucket_path=PATH_WITHIN_BUCKET_FOR_TESTS,
    )
    if not upload_file_to_S3_bucket_success_regex().fullmatch(logging_message):
        assert False  # Entering this block means the function that's being tested raised an error, so continuing with the test won't provide anything meaningful
    list_objects_response = s3_client.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=PATH_WITHIN_BUCKET_FOR_TESTS,
    )
    bucket_contents = []
    for contents_dict in list_objects_response['Contents']:
        bucket_contents.append(contents_dict['Key'])
    bucket_contents = [file_name.replace(PATH_WITHIN_BUCKET_FOR_TESTS, "") for file_name in bucket_contents]
    if isinstance(data, dict):
        assert f"{file_name_stem}.json" in bucket_contents
    else:
        assert f"{file_name_stem}.txt" in bucket_contents


def test_ISSN_regex():
    """Tests matching the regex object to ISSN strings."""
    assert ISSN_regex().fullmatch("1234-5678") is not None
    assert ISSN_regex().fullmatch("1123-000x") is not None
    assert ISSN_regex().fullmatch("0987-6543 ") is not None


def test_ISBN_regex():
    """Tests matching the regex object to ISBN strings."""
    assert ISBN_regex().fullmatch("978-1-56619-909-4") is not None
    assert ISBN_regex().fullmatch("1-56619-909-3") is not None
    assert ISBN_regex().fullmatch("1257561035") is not None
    assert ISBN_regex().fullmatch("9781566199094") is not None
    assert ISBN_regex().fullmatch("1-56619-909-3 ") is not None


def test_last_day_of_month():
    """Tests returning the last day of the given month."""
    assert last_day_of_month(date(2022, 1, 2)) == date(2022, 1, 31)
    assert last_day_of_month(date(2020, 2, 1)) == date(2020, 2, 29)
    assert last_day_of_month(date(2021, 2, 1)) == date(2021, 2, 28)


def test_extract_value_from_single_value_df():
    """Tests extracting the value from a dataframe containing a single value."""
    assert extract_value_from_single_value_df(pd.DataFrame([[10]])) == 10
    assert extract_value_from_single_value_df(pd.DataFrame([["hi"]])) == "hi"
    assert extract_value_from_single_value_df(pd.DataFrame([[10.0]])) == 10
    assert extract_value_from_single_value_df(pd.DataFrame([[None]])) == 0


def test_S3_file_name_timestamp():
    """Tests formatting a datetime value with the given format code."""
    assert datetime(2022, 1, 12, 23, 59, 59).strftime(S3_file_name_timestamp()) == "2022-01-12T23.59.59"
    assert datetime(2024, 7, 4, 2, 45, 8).strftime(S3_file_name_timestamp()) == "2024-07-04T02.45.08"
    assert datetime(1999, 11, 27, 13, 18, 27).strftime(S3_file_name_timestamp()) == "1999-11-27T13.18.27"


def test_non_COUNTER_file_name_regex():
    """Tests matching the regex object to file names."""
    assert non_COUNTER_file_name_regex().fullmatch("1_2020.csv") is not None
    assert non_COUNTER_file_name_regex().fullmatch("100_2021.xlsx") is not None
    assert non_COUNTER_file_name_regex().fullmatch("55_2016.pdf") is not None
    assert non_COUNTER_file_name_regex().fullmatch("99999_2030.json") is not None


def test_empty_string_regex():
    """Tests matching the regex object to empty and whitespace-only strings."""
    assert empty_string_regex().fullmatch("") is not None
    assert empty_string_regex().fullmatch(" ") is not None
    assert empty_string_regex().fullmatch("\n") is not None