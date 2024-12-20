"""Tests the routes in the `initialization` blueprint."""
########## Passing 2024-12-19 ##########

import pytest
import logging
from pathlib import Path
import os
import random
from shutil import copy
from bs4 import BeautifulSoup
import pandas as pd
from requests_toolbelt.multipart.encoder import MultipartEncoder
from pandas.testing import assert_frame_equal
from pandas.testing import assert_series_equal

# `conftest.py` fixtures are imported automatically
from nolcat.app import *
from nolcat.models import *
from nolcat.statements import *
from nolcat.initialization import *

log = logging.getLogger(__name__)


#Section: Fixtures
@pytest.fixture
def blank_annualUsageCollectionTracking_data_types():
    """Create a dictionary with the fields in the `annualUsageCollectionTracking` template and their associated data types.
    
    Yields:
        dict: the `astype` argument for `annualUsageCollectionTracking` and the primary keys corresponding to the parts of its composite key
    """
    yield {
        **AnnualUsageCollectionTracking.state_data_types(),  # The double asterisk is the dictionary unpacking operator
        "Statistics Source": StatisticsSources.state_data_types()['statistics_source_name'],
        "Fiscal Year": FiscalYears.state_data_types()['fiscal_year'],
    }


@pytest.fixture
def create_fiscalYears_CSV_file(tmp_path, fiscalYears_relation):
    """Create a CSV file with the test data for the `fiscalYears` relation, then removes the file at the end of the test.

    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        fiscalYears_relation (dataframe): a relation of test data
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    yield fiscalYears_relation.to_csv(
        tmp_path / 'fiscalYears_relation.csv',
        index_label="fiscal_year_ID",
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'fiscalYears_relation.csv')


@pytest.fixture
def create_annualStatistics_CSV_file(tmp_path, annualStatistics_relation):
    """Create a CSV file with the test data for the `annualStatistics` relation, then removes the file at the end of the test.

    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        annualStatistics_relation (dataframe): a relation of test data
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    yield annualStatistics_relation.to_csv(
        tmp_path / 'annualStatistics_relation.csv',
        index_label=["fiscal_year_ID", 'question'],
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'annualStatistics_relation.csv')


@pytest.fixture
def create_vendors_CSV_file(tmp_path, vendors_relation):
    """Create a CSV file with the test data for the `vendors` relation, then removes the file at the end of the test.
    
    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        vendors_relation (dataframe): a relation of test data
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    yield vendors_relation.to_csv(
        tmp_path / 'vendors_relation.csv',
        index_label="vendor_ID",
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'vendors_relation.csv')


@pytest.fixture
def create_vendorNotes_CSV_file(tmp_path, vendorNotes_relation):
    """Create a CSV file with the test data for the `vendorNotes_relation` relation, then removes the file at the end of the test.
    
    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        vendorNotes_relation (dataframe): a relation of test data
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    yield vendorNotes_relation.to_csv(
        tmp_path / 'vendorNotes_relation.csv',
        index_label=False,  # Index column not specified when this CSV is read in
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'vendorNotes_relation.csv')


@pytest.fixture
def create_statisticsSources_CSV_file(tmp_path, statisticsSources_relation):
    """Create a CSV file with the test data for the `statisticsSources_relation` relation, then removes the file at the end of the test.
    
    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        statisticsSources_relation (dataframe): a relation of test data
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    yield statisticsSources_relation.to_csv(
        tmp_path / 'statisticsSources_relation.csv',
        index_label="statistics_source_ID",
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'statisticsSources_relation.csv')


@pytest.fixture
def create_statisticsSourceNotes_CSV_file(tmp_path, statisticsSourceNotes_relation):
    """Create a CSV file with the test data for the `statisticsSourceNotes_relation` relation, then removes the file at the end of the test.
    
    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        statisticsSourceNotes_relation (dataframe): a relation of test data
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    yield statisticsSourceNotes_relation.to_csv(
        tmp_path / 'statisticsSourceNotes_relation.csv',
        index_label=False,  # Index column not specified when this CSV is read in
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'statisticsSourceNotes_relation.csv')


@pytest.fixture
def create_resourceSources_CSV_file(tmp_path, resourceSources_relation):
    """Create a CSV file with the test data for the `resourceSources_relation` relation, then removes the file at the end of the test.
    
    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        resourceSources_relation (dataframe): a relation of test data
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    yield resourceSources_relation.to_csv(
        tmp_path / 'resourceSources_relation.csv',
        index_label="resource_source_ID",
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'resourceSources_relation.csv')


@pytest.fixture
def create_resourceSourceNotes_CSV_file(tmp_path, resourceSourceNotes_relation):
    """Create a CSV file with the test data for the `resourceSourceNotes_relation` relation, then removes the file at the end of the test.
    
    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        resourceSourceNotes_relation (dataframe): a relation of test data
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    yield resourceSourceNotes_relation.to_csv(
        tmp_path / 'resourceSourceNotes_relation.csv',
        index_label=False,  # Index column not specified when this CSV is read in
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'resourceSourceNotes_relation.csv')


@pytest.fixture
def create_statisticsResourceSources_CSV_file(tmp_path, statisticsResourceSources_relation):
    """Create a CSV file with the test data for the `statisticsResourceSources_relation` relation, then removes the file at the end of the test.
    
    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        statisticsResourceSources_relation (dataframe): a relation of test data
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    yield statisticsResourceSources_relation.to_csv(
        tmp_path / 'statisticsResourceSources_relation.csv',
        index_label=["SRS_statistics_source", "SRS_resource_source"],
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'statisticsResourceSources_relation.csv')


@pytest.fixture
def create_blank_annualUsageCollectionTracking_CSV_file(tmp_path, blank_annualUsageCollectionTracking_data_types):
    """Create a CSV file with the test data resulting from the Cartesian join creating the AUCT template, then removes the file at the end of the test.
    
    The `annualUsageCollectionTracking_relation` fixture represents the aforementioned relation when completely filled out with data. The dataframe and subsequent CSV created from the Cartesian join in the `collect_AUCT_and_historical_COUNTER_data()` route function contains null values in the relation's non-index fields, extra fields for the statistics source and fiscal year name, and records for statistics source and fiscal year combinations that don't actually exist. To test the CSV creation, a new dataframe meeting those criteria needed to be created for conversion to the CSV. This dataframe is ordered by the `AUCT_statistics_source` field followed by the `AUCT_fiscal_year` field to match the order that results from the Cartesian join.

    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        blank_annualUsageCollectionTracking_data_types (dict): the `astype` argument for `annualUsageCollectionTracking` and the primary keys corresponding to the parts of its composite key
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    multiindex = pd.DataFrame(
        [
            [0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5],
            [1, 0], [1, 1], [1, 2], [1, 3], [1, 4], [1, 5],
            [2, 0], [2, 1], [2, 2], [2, 3], [2, 4], [2, 5],
            [3, 0], [3, 1], [3, 2], [3, 3], [3, 4], [3, 5],
            [4, 0], [4, 1], [4, 2], [4, 3], [4, 4], [4, 5],
            [5, 0], [5, 1], [5, 2], [5, 3], [5, 4], [5, 5],
            [6, 0], [6, 1], [6, 2], [6, 3], [6, 4], [6, 5],
            [7, 0], [7, 1], [7, 2], [7, 3], [7, 4], [7, 5],
            [8, 0], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5],
            [9, 0], [9, 1], [9, 2], [9, 3], [9, 4], [9, 5],
            [10, 0], [10, 1], [10, 2], [10, 3], [10, 4], [10, 5],
            [11, 0], [11, 1], [11, 2], [11, 3], [11, 4], [11, 5],
        ],
        columns=["AUCT_statistics_source", "AUCT_fiscal_year"],
    )
    multiindex = pd.MultiIndex.from_frame(multiindex)
    df = pd.DataFrame(
        [
            ["ProQuest", "2017", None, None, None, None, None, None, None],
            ["ProQuest", "2018", None, None, None, None, None, None, None],
            ["ProQuest", "2019", None, None, None, None, None, None, None],
            ["ProQuest", "2020", None, None, None, None, None, None, None],
            ["ProQuest", "2021", None, None, None, None, None, None, None],
            ["ProQuest", "2022", None, None, None, None, None, None, None],
            ["EBSCOhost", "2017", None, None, None, None, None, None, None],
            ["EBSCOhost", "2018", None, None, None, None, None, None, None],
            ["EBSCOhost", "2019", None, None, None, None, None, None, None],
            ["EBSCOhost", "2020", None, None, None, None, None, None, None],
            ["EBSCOhost", "2021", None, None, None, None, None, None, None],
            ["EBSCOhost", "2022", None, None, None, None, None, None, None],
            ["Gale Cengage Learning", "2017", None, None, None, None, None, None, None],
            ["Gale Cengage Learning", "2018", None, None, None, None, None, None, None],
            ["Gale Cengage Learning", "2019", None, None, None, None, None, None, None],
            ["Gale Cengage Learning", "2020", None, None, None, None, None, None, None],
            ["Gale Cengage Learning", "2021", None, None, None, None, None, None, None],
            ["Gale Cengage Learning", "2022", None, None, None, None, None, None, None],
            ["Duke UP", "2017", None, None, None, None, None, None, None],
            ["Duke UP", "2018", None, None, None, None, None, None, None],
            ["Duke UP", "2019", None, None, None, None, None, None, None],
            ["Duke UP", "2020", None, None, None, None, None, None, None],
            ["Duke UP", "2021", None, None, None, None, None, None, None],
            ["Duke UP", "2022", None, None, None, None, None, None, None],
            ["iG Library/Business Expert Press (BEP)", "2017", None, None, None, None, None, None, None],
            ["iG Library/Business Expert Press (BEP)", "2018", None, None, None, None, None, None, None],
            ["iG Library/Business Expert Press (BEP)", "2019", None, None, None, None, None, None, None],
            ["iG Library/Business Expert Press (BEP)", "2020", None, None, None, None, None, None, None],
            ["iG Library/Business Expert Press (BEP)", "2021", None, None, None, None, None, None, None],
            ["iG Library/Business Expert Press (BEP)", "2022", None, None, None, None, None, None, None],
            ["DemographicsNow", "2017", None, None, None, None, None, None, None],
            ["DemographicsNow", "2018", None, None, None, None, None, None, None],
            ["DemographicsNow", "2019", None, None, None, None, None, None, None],
            ["DemographicsNow", "2020", None, None, None, None, None, None, None],
            ["DemographicsNow", "2021", None, None, None, None, None, None, None],
            ["DemographicsNow", "2022", None, None, None, None, None, None, None],
            ["Ebook Central", "2017", None, None, None, None, None, None, None],
            ["Ebook Central", "2018", None, None, None, None, None, None, None],
            ["Ebook Central", "2019", None, None, None, None, None, None, None],
            ["Ebook Central", "2020", None, None, None, None, None, None, None],
            ["Ebook Central", "2021", None, None, None, None, None, None, None],
            ["Ebook Central", "2022", None, None, None, None, None, None, None],
            ["Peterson's Career Prep", "2017", None, None, None, None, None, None, None],
            ["Peterson's Career Prep", "2018", None, None, None, None, None, None, None],
            ["Peterson's Career Prep", "2019", None, None, None, None, None, None, None],
            ["Peterson's Career Prep", "2020", None, None, None, None, None, None, None],
            ["Peterson's Career Prep", "2021", None, None, None, None, None, None, None],
            ["Peterson's Career Prep", "2022", None, None, None, None, None, None, None],
            ["Peterson's Test Prep", "2017", None, None, None, None, None, None, None],
            ["Peterson's Test Prep", "2018", None, None, None, None, None, None, None],
            ["Peterson's Test Prep", "2019", None, None, None, None, None, None, None],
            ["Peterson's Test Prep", "2020", None, None, None, None, None, None, None],
            ["Peterson's Test Prep", "2021", None, None, None, None, None, None, None],
            ["Peterson's Test Prep", "2022", None, None, None, None, None, None, None],
            ["Peterson's Prep", "2017", None, None, None, None, None, None, None],
            ["Peterson's Prep", "2018", None, None, None, None, None, None, None],
            ["Peterson's Prep", "2019", None, None, None, None, None, None, None],
            ["Peterson's Prep", "2020", None, None, None, None, None, None, None],
            ["Peterson's Prep", "2021", None, None, None, None, None, None, None],
            ["Peterson's Prep", "2022", None, None, None, None, None, None, None],
            ["Pivot", "2017", None, None, None, None, None, None, None],
            ["Pivot", "2018", None, None, None, None, None, None, None],
            ["Pivot", "2019", None, None, None, None, None, None, None],
            ["Pivot", "2020", None, None, None, None, None, None, None],
            ["Pivot", "2021", None, None, None, None, None, None, None],
            ["Pivot", "2022", None, None, None, None, None, None, None],
            ["Ulrichsweb", "2017", None, None, None, None, None, None, None],
            ["Ulrichsweb", "2018", None, None, None, None, None, None, None],
            ["Ulrichsweb", "2019", None, None, None, None, None, None, None],
            ["Ulrichsweb", "2020", None, None, None, None, None, None, None],
            ["Ulrichsweb", "2021", None, None, None, None, None, None, None],
            ["Ulrichsweb", "2022", None, None, None, None, None, None, None],
        ],
        index=multiindex,
        columns=["Statistics Source", "Fiscal Year", "usage_is_being_collected", "manual_collection_required", "collection_via_email", "is_COUNTER_compliant", "collection_status", "usage_file_path", "notes"],
    )
    df = df.astype(blank_annualUsageCollectionTracking_data_types)
    yield df.to_csv(
        tmp_path / 'annualUsageCollectionTracking_relation.csv',
        index_label=["AUCT_statistics_source", "AUCT_fiscal_year"],
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'annualUsageCollectionTracking_relation.csv')


@pytest.fixture
def create_annualUsageCollectionTracking_CSV_file(tmp_path, annualUsageCollectionTracking_relation):
    """Create a CSV file with the test data for the `annualUsageCollectionTracking_relation` relation, then removes the file at the end of the test.
    
    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        annualUsageCollectionTracking_relation (dataframe): a relation of test data
    
    Yields:
        CSV: a CSV file corresponding to a relation in the test data
    """
    yield annualUsageCollectionTracking_relation.to_csv(
        tmp_path / 'annualUsageCollectionTracking_relation.csv',
        index_label=["AUCT_statistics_source", "AUCT_fiscal_year"],
        encoding='utf-8',
        errors='backslashreplace',
    )
    os.remove(tmp_path / 'annualUsageCollectionTracking_relation.csv')


#Section: Tests
def test_GET_request_for_collect_FY_and_vendor_data(client):
    """Tests that the homepage can be successfully GET requested and that the response matches the file being used."""
    page = client.get('/initialization/')
    GET_soup = BeautifulSoup(page.data, 'lxml')
    GET_response_title = GET_soup.head.title
    GET_response_page_title = GET_soup.body.h1

    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'initialization' / 'templates' / 'initialization' / 'index.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title
        HTML_file_page_title = file_soup.body.h1

    assert page.status == "200 OK"
    assert HTML_file_title == GET_response_title
    assert HTML_file_page_title == GET_response_page_title


@pytest.mark.dependency()
def test_collect_FY_and_vendor_data(engine, client, tmp_path, header_value, create_fiscalYears_CSV_file, fiscalYears_relation, create_annualStatistics_CSV_file, annualStatistics_relation, create_vendors_CSV_file, vendors_relation, create_vendorNotes_CSV_file, vendorNotes_relation, caplog):  # CSV creation fixture names aren't invoked, but without them, the files yielded by those fixtures aren't available in the test function
    """Tests uploading CSVs with data in the `fiscalYears`, `annualStatistics`, `vendors`, and `vendorNotes` relations and loading that data into the database."""
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()`
    
    #Section: Submit Forms via HTTP POST
    CSV_files = MultipartEncoder(
        fields={
            'fiscalYears_CSV': ('fiscalYears_relation.csv', open(tmp_path / 'fiscalYears_relation.csv', 'rb'), 'text/csv'),
            'annualStatistics_CSV': ('annualStatistics_relation.csv', open(tmp_path / 'annualStatistics_relation.csv', 'rb'), 'text/csv'),
            'vendors_CSV': ('vendors_relation.csv', open(tmp_path / 'vendors_relation.csv', 'rb'), 'text/csv'),
            'vendorNotes_CSV': ('vendorNotes_relation.csv', open(tmp_path / 'vendorNotes_relation.csv', 'rb'), 'text/csv'),
        },
        encoding='utf-8',
    )
    header_value['Content-Type'] = CSV_files.content_type
    POST_response = client.post(
        '/initialization/',
        follow_redirects=True,
        headers=header_value,
        data=CSV_files,
    )

    #Section: Get Relations from Database for Comparison
    fiscalYears_relation_data = query_database(
        query="SELECT * FROM fiscalYears;",
        engine=engine,
        index='fiscal_year_ID',
    )
    if isinstance(fiscalYears_relation_data, str):
        pytest.skip(database_function_skip_statements(fiscalYears_relation_data))
    fiscalYears_relation_data = fiscalYears_relation_data.astype(FiscalYears.state_data_types())
    fiscalYears_relation_data["start_date"] = pd.to_datetime(fiscalYears_relation_data["start_date"])
    fiscalYears_relation_data["end_date"] = pd.to_datetime(fiscalYears_relation_data["end_date"])

    annualStatistics_relation_data = query_database(  # This creates a dataframe with a multiindex and a single field, requiring the conversion below
        query="SELECT * FROM annualStatistics ORDER BY question DESC;",  # The ORDER BY puts the records in the same order as in the test data
        engine=engine,
        index=['fiscal_year_ID', 'question'],
    )
    if isinstance(annualStatistics_relation_data, str):
        pytest.skip(database_function_skip_statements(annualStatistics_relation_data))
    annualStatistics_relation_data = change_single_field_dataframe_into_series(annualStatistics_relation_data)
    annualStatistics_relation_data = annualStatistics_relation_data.astype(AnnualStatistics.state_data_types())

    vendors_relation_data = query_database(
        query="SELECT * FROM vendors;",
        engine=engine,
        index='vendor_ID',
    )
    if isinstance(vendors_relation_data, str):
        pytest.skip(database_function_skip_statements(vendors_relation_data))
    vendors_relation_data = vendors_relation_data.astype(Vendors.state_data_types())

    vendorNotes_relation_data = query_database(
        query="SELECT * FROM vendorNotes;",
        engine=engine,
        index='vendor_notes_ID',
    )
    if isinstance(vendorNotes_relation_data, str):
        pytest.skip(database_function_skip_statements(vendorNotes_relation_data))
    vendorNotes_relation_data = vendorNotes_relation_data.astype(VendorNotes.state_data_types())
    vendorNotes_relation_data["date_written"] = pd.to_datetime(vendorNotes_relation_data["date_written"])

    #Section: Assert Statements
    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'initialization' / 'templates' / 'initialization' / 'initial-data-upload-2.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title.string.encode('utf-8')
        HTML_file_page_title = file_soup.body.h1.string.encode('utf-8')
    assert POST_response.history[0].status == "302 FOUND"  # This confirms there was a redirect
    assert POST_response.status == "200 OK"
    assert HTML_file_title in POST_response.data
    assert HTML_file_page_title in POST_response.data
    assert_frame_equal(fiscalYears_relation_data, fiscalYears_relation)
    assert_series_equal(annualStatistics_relation_data, annualStatistics_relation)
    assert_frame_equal(vendors_relation_data, vendors_relation)
    assert_frame_equal(vendorNotes_relation_data, vendorNotes_relation)


@pytest.mark.dependency(depends=['test_collect_FY_and_vendor_data'])  # Test will fail without primary keys in relations loaded in this test
def test_collect_sources_data(engine, client, tmp_path, header_value, create_statisticsSources_CSV_file, statisticsSources_relation, create_statisticsSourceNotes_CSV_file, statisticsSourceNotes_relation, create_resourceSources_CSV_file, resourceSources_relation, create_resourceSourceNotes_CSV_file, resourceSourceNotes_relation, create_statisticsResourceSources_CSV_file, statisticsResourceSources_relation, caplog):  # CSV creation fixture names aren't invoked, but without them, the files yielded by those fixtures aren't available in the test function
    """Tests uploading CSVs with data in the `statisticsSources`, `statisticsSourceNotes`, `resourceSources`, `resourceSourceNotes`, and `statisticsResourceSources` relations and loading that data into the database."""
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()`
    
    #Section: Submit Forms via HTTP POST
    CSV_files = MultipartEncoder(
        fields={
            'statisticsSources_CSV': ('statisticsSources_relation.csv', open(tmp_path / 'statisticsSources_relation.csv', 'rb'), 'text/csv'),
            'statisticsSourceNotes_CSV': ('statisticsSourceNotes_relation.csv', open(tmp_path / 'statisticsSourceNotes_relation.csv', 'rb'), 'text/csv'),
            'resourceSources_CSV': ('resourceSources_relation.csv', open(tmp_path / 'resourceSources_relation.csv', 'rb'), 'text/csv'),
            'resourceSourceNotes_CSV': ('resourceSourceNotes_relation.csv', open(tmp_path / 'resourceSourceNotes_relation.csv', 'rb'), 'text/csv'),
            'statisticsResourceSources_CSV': ('statisticsResourceSources_relation.csv', open(tmp_path / 'statisticsResourceSources_relation.csv', 'rb'), 'text/csv'),
        },
        encoding='utf-8',
    )
    header_value['Content-Type'] = CSV_files.content_type
    POST_response = client.post(
        '/initialization/initialization-page-2',
        follow_redirects=True,
        headers=header_value,
        data=CSV_files,
    )

    #Section: Get Relations from Database for Comparison
    statisticsSources_relation_data = query_database(
        query="SELECT * FROM statisticsSources;",
        engine=engine,
        index='statistics_source_ID',
    )
    if isinstance(statisticsSources_relation_data, str):
        pytest.skip(database_function_skip_statements(statisticsSources_relation_data))
    statisticsSources_relation_data = statisticsSources_relation_data.astype(StatisticsSources.state_data_types())
    statisticsSources_relation_data['statistics_source_retrieval_code'] = statisticsSources_relation_data['statistics_source_retrieval_code'].apply(lambda string_of_float: string_of_float.split(".")[0] if not pd.isnull(string_of_float) else string_of_float).astype('string')  # String created is of a float (aka `n.0`), so the decimal and everything after it need to be removed; the transformation changes the series dtype back to object, so it needs to be set to string again

    statisticsSourceNotes_relation_data = query_database(
        query="SELECT * FROM statisticsSourceNotes;",
        engine=engine,
        index='statistics_source_notes_ID',
    )
    if isinstance(statisticsSourceNotes_relation_data, str):
        pytest.skip(database_function_skip_statements(statisticsSourceNotes_relation_data))
    statisticsSourceNotes_relation_data = statisticsSourceNotes_relation_data.astype(StatisticsSourceNotes.state_data_types())
    statisticsSourceNotes_relation_data["date_written"] = pd.to_datetime(statisticsSourceNotes_relation_data["date_written"])

    resourceSources_relation_data = query_database(
        query="SELECT * FROM resourceSources;",
        engine=engine,
        index='resource_source_ID',
    )
    if isinstance(resourceSources_relation_data, str):
        pytest.skip(database_function_skip_statements(resourceSources_relation_data))
    resourceSources_relation_data = resourceSources_relation_data.astype(ResourceSources.state_data_types())
    resourceSources_relation_data["access_stop_date"] = pd.to_datetime(resourceSources_relation_data["access_stop_date"])

    resourceSourceNotes_relation_data = query_database(
        query="SELECT * FROM resourceSourceNotes;",
        engine=engine,
        index='resource_source_notes_ID',
    )
    if isinstance(resourceSourceNotes_relation_data, str):
        pytest.skip(database_function_skip_statements(resourceSourceNotes_relation_data))
    resourceSourceNotes_relation_data = resourceSourceNotes_relation_data.astype(ResourceSourceNotes.state_data_types())
    resourceSourceNotes_relation_data["date_written"] = pd.to_datetime(resourceSourceNotes_relation_data["date_written"])

    statisticsResourceSources_relation_data = query_database(  # This creates a dataframe with a multiindex and a single field, requiring the conversion below
        query="SELECT * FROM statisticsResourceSources;",
        engine=engine,
        index=['SRS_statistics_source', 'SRS_resource_source'],
    )
    if isinstance(statisticsResourceSources_relation_data, str):
        pytest.skip(database_function_skip_statements(statisticsResourceSources_relation_data))
    statisticsResourceSources_relation_data = change_single_field_dataframe_into_series(statisticsResourceSources_relation_data)
    statisticsResourceSources_relation_data = statisticsResourceSources_relation_data.astype(StatisticsResourceSources.state_data_types())

    #Section: Assert Statements
    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'initialization' / 'templates' / 'initialization' / 'initial-data-upload-3.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title.string.encode('utf-8')
        HTML_file_page_title = file_soup.body.h1.string.encode('utf-8')
    assert POST_response.history[0].status == "302 FOUND"  # This confirms there was a redirect
    assert POST_response.status == "200 OK"
    assert HTML_file_title in POST_response.data
    assert HTML_file_page_title in POST_response.data
    assert_frame_equal(statisticsSources_relation_data, statisticsSources_relation)
    assert_frame_equal(statisticsSourceNotes_relation_data, statisticsSourceNotes_relation)
    assert_frame_equal(resourceSources_relation_data, resourceSources_relation)
    assert_frame_equal(resourceSourceNotes_relation_data, resourceSourceNotes_relation)
    assert_series_equal(statisticsResourceSources_relation_data, statisticsResourceSources_relation)


@pytest.mark.dependency(depends=['test_collect_FY_and_vendor_data', 'test_collect_sources_data'])  # Test will fail without primary keys found in the `fiscalYears` and `statisticsSources` relations; this test passes only if those relations are successfully loaded into the database
def test_GET_request_for_collect_AUCT_and_historical_COUNTER_data(client, tmp_path, create_blank_annualUsageCollectionTracking_CSV_file, blank_annualUsageCollectionTracking_data_types):
    """Test creating the AUCT relation template CSV."""
    page = client.get('/initialization/initialization-page-3')
    AUCT_template_df = pd.read_csv(
        TOP_NOLCAT_DIRECTORY / 'nolcat' / 'initialization' / 'initialize_annualUsageCollectionTracking.csv',
        index_col=["AUCT_statistics_source", "AUCT_fiscal_year"],
        dtype=blank_annualUsageCollectionTracking_data_types,
        encoding='utf-8',
        encoding_errors='backslashreplace',
    )
    AUCT_fixture_df = pd.read_csv(
        Path(tmp_path / 'annualUsageCollectionTracking_relation.csv'),
        index_col=["AUCT_statistics_source", "AUCT_fiscal_year"],
        dtype=blank_annualUsageCollectionTracking_data_types,
        encoding='utf-8',
        encoding_errors='backslashreplace',
    )
    assert_frame_equal(AUCT_template_df, AUCT_fixture_df)  #ToDo: Does this work in lieu of a direct comparison between the text file contents?


@pytest.mark.dependency(depends=['test_collect_FY_and_vendor_data', 'test_collect_sources_data'])  # Test will fail without primary keys found in the `fiscalYears` and `statisticsSources` relations; this test passes only if those relations are successfully loaded into the database
@pytest.mark.slow
def test_collect_AUCT_and_historical_COUNTER_data(engine, client, tmp_path, header_value, create_COUNTERData_workbook_iterdir_list, create_annualUsageCollectionTracking_CSV_file, annualUsageCollectionTracking_relation, COUNTERData_relation, caplog):  # CSV creation fixture name isn't invoked, but without it, the file yielded by that fixture isn't available in the test function
    """Tests uploading the AUCT relation CSV and historical tabular COUNTER reports and loading that data into the database."""
    caplog.set_level(logging.INFO, logger='nolcat.upload_COUNTER_reports')  # For `create_dataframe()`
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `first_new_pk_value()` and `query_database()`
    
    #Section: Submit Forms via HTTP POST
    form_submissions = {
        'annualUsageCollectionTracking_CSV': open(tmp_path / 'annualUsageCollectionTracking_relation.csv', 'rb'),
        'COUNTER_reports': [open(file, 'rb') for file in create_COUNTERData_workbook_iterdir_list],
    }
    header_value['Content-Type'] = 'multipart/form-data'
    POST_response = client.post(
        '/initialization/initialization-page-3',
        follow_redirects=True,
        headers=header_value,
        data=form_submissions,
    )

    #Section: Get Relations from Database for Comparison
    annualUsageCollectionTracking_relation_data = query_database(
        query="SELECT * FROM annualUsageCollectionTracking;",
        engine=engine,
        index=["AUCT_statistics_source", "AUCT_fiscal_year"],
    )
    if isinstance(annualUsageCollectionTracking_relation_data, str):
        pytest.skip(database_function_skip_statements(annualUsageCollectionTracking_relation_data))
    annualUsageCollectionTracking_relation_data = annualUsageCollectionTracking_relation_data.astype(AnnualUsageCollectionTracking.state_data_types())

    COUNTERData_relation_data = query_database(
        query="SELECT * FROM COUNTERData;",
        engine=engine,
        index="COUNTER_data_ID",
    )
    if isinstance(COUNTERData_relation_data, str):
        pytest.skip(database_function_skip_statements(COUNTERData_relation_data))
    COUNTERData_relation_data = COUNTERData_relation_data.astype(COUNTERData.state_data_types())
    COUNTERData_relation_data = COUNTERData_relation_data.drop(columns=['report_creation_date'])
    COUNTERData_relation_data["publication_date"] = pd.to_datetime(COUNTERData_relation_data["publication_date"])
    COUNTERData_relation_data["parent_publication_date"] = pd.to_datetime(COUNTERData_relation_data["parent_publication_date"])
    COUNTERData_relation_data["usage_date"] = pd.to_datetime(COUNTERData_relation_data["usage_date"])

    #Section: Assert Statements
    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'initialization' / 'templates' / 'initialization' / 'initial-data-upload-4.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title.string.encode('utf-8')
        HTML_file_page_title = file_soup.body.h1.string.encode('utf-8')
    assert POST_response.history[0].status == "302 FOUND"  # This confirms there was a redirect
    assert POST_response.status == "200 OK"
    assert HTML_file_title in POST_response.data
    assert HTML_file_page_title in POST_response.data
    assert_frame_equal(annualUsageCollectionTracking_relation_data, annualUsageCollectionTracking_relation)
    assert_frame_equal(COUNTERData_relation_data, COUNTERData_relation[COUNTERData_relation_data.columns.tolist()], check_index_type=False)  # `check_index_type` argument allows test to pass if indexes aren't the same dtype


@pytest.mark.dependency(depends=['test_collect_AUCT_and_historical_COUNTER_data'])  # Test will fail without primary keys found in the `annualUsageCollectionTracking` relation; this test passes only if this relation is successfully loaded into the database
def test_GET_request_for_upload_historical_non_COUNTER_usage(client, caplog):
    """Tests creating a form with the option to upload a file for each statistics source and fiscal year combination that's not COUNTER-compliant."""
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()`

    page = client.get(
        '/initialization/initialization-page-4',
        follow_redirects=True,
    )
    GET_soup = BeautifulSoup(page.data, 'lxml')
    GET_response_title = GET_soup.head.title
    GET_response_page_title = GET_soup.body.h1
    number_of_file_fields = len(GET_soup.find_all(name='input', type='file'))
    
    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'initialization' / 'templates' / 'initialization' / 'initial-data-upload-4.html', 'br') as HTML_file:
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
        engine=db.engine,
    )
    if isinstance(df, str):
        pytest.skip(database_function_skip_statements(df))

    assert page.status == "200 OK"
    assert HTML_file_title == GET_response_title
    assert HTML_file_page_title == GET_response_page_title
    assert number_of_file_fields == df.shape[0]


@pytest.fixture
def files_for_test_upload_historical_non_COUNTER_usage(tmp_path, caplog):
    """A fixture which can be called multiple times capable of randomly selecting a file to use in testing `test_upload_historical_non_COUNTER_usage`, making a copy of that file with a name matching the naming convention, and returning the value appropriate for the file type for use in the `fields` dictionary of a MultipartEncoder instance.

    To test for a greater number of possible scenarios, the number and type of files uploaded when calling `test_upload_historical_non_COUNTER_usage` should vary; the "factory as fixture" pattern (https://docs.pytest.org/en/8.2.x/how-to/fixtures.html#factories-as-fixtures) makes that possible. Not only does iteration allow the test to call the fixture a variable number of times, it makes teardown much easier, as the pattern has that functionality explicitly modeled in the pytest instructions. The `sample_COUNTER_R4_reports` folder is used for binary data because all of the files within are under 30KB; there is no similar way to limit the file size for text data, as the files in `R5_COUNTER_JSONs_for_tests` can be over 6,000KB.

    Args:
        tmp_path (pathlib.Path): a temporary directory created just for running tests
        caplog (pytest.logging.caplog): changes the logging capture level of individual test modules during test runtime

    Yields:
        dict: a valid `MultipartEncoder.fields` argument using a randomly selected file
    """
    caplog.set_level(logging.INFO, logger='botocore')
    
    for_removal = []  # When invoked in a log statement before the yield statement, the list appears empty, but the teardown works as expected

    def _files_for_test_upload_historical_non_COUNTER_usage(AUCT_option):
        """An inner fixture function returning the value appropriate for the file type for use in the `fields` dictionary of a MultipartEncoder instance.

        The "factory as fixture" pattern uses an inner function which supplies a return value passed to the test function whenever the outer fixture function is called. Since the inner function uses a `return` statement, not a `yield` statement, teardown functionality must be in the outer function. To preserve the values returned by the inner function, the outer function has the `for_removal` list, and all values returned by the inner function must also be appended to that list for teardown.

    Args:
        AUCT_option (str): the result of the `nolcat.app.create_AUCT_SelectField_options()` function for the given field

        Returns:
            tuple: the file name and a FileIO object for the file
        """
        file_options = [file for file in Path(TOP_NOLCAT_DIRECTORY, 'tests', 'data', 'R5_COUNTER_JSONs_for_tests').iterdir()] + [file for file in Path(TOP_NOLCAT_DIRECTORY, 'tests', 'bin', 'COUNTER_workbooks_for_tests').iterdir()]
        file = random.choice(file_options)
        new_file = tmp_path / f"{AUCT_option[0][0]}_{AUCT_option[1][-4:]}{file.suffix}"
        copy(file, new_file)
        log.debug(check_if_file_exists_statement(new_file))
        for_removal.append(f"{AUCT_option[0][0]}_{AUCT_option[0][1]}{new_file.suffix}")  # `AnnualUsageCollectionTracking.upload_nonstandard_usage_file()` changes the file name to the instance record's primary keys separated by an underscore, so that file name is what needs to be saved for removal from S3 
        return (new_file.name, open(new_file, 'rb'))

    yield _files_for_test_upload_historical_non_COUNTER_usage

    for file in for_removal:
        try:
            s3_client.delete_object(
                Bucket=BUCKET_NAME,
                Key=PATH_WITHIN_BUCKET_FOR_TESTS + file
            )
        except botocore.exceptions as error:
            log.error(unable_to_delete_test_file_in_S3_statement(file.name, error))


@pytest.mark.dependency(depends=['test_collect_AUCT_and_historical_COUNTER_data'])  # Test will fail without primary keys found in the `annualUsageCollectionTracking` relation; this test passes only if this relation is successfully loaded into the database
def test_upload_historical_non_COUNTER_usage(engine, client, header_value, files_for_test_upload_historical_non_COUNTER_usage, caplog):
    """Tests uploading the files with non-COUNTER usage statistics."""
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()` and `create_AUCT_SelectField_options()`

    #Section: Create Form Submission
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
        engine=db.engine,
    )
    if isinstance(df, str):
        pytest.skip(database_function_skip_statements(df))
    list_of_AUCT_submission_fields = create_AUCT_SelectField_options(df)
    list_of_AUCT_submission_fields = {f"usage_files-{i}-usage_file": AUCT_options for (i, AUCT_options) in enumerate(list_of_AUCT_submission_fields)}
    log.debug(f"Uploads possible for the following fields:\n{format_list_for_stdout(list_of_AUCT_submission_fields)}")
    fields_being_uploaded = {k: list_of_AUCT_submission_fields[k] for k in random.sample(
        list(list_of_AUCT_submission_fields.keys()),  # Using brackets to type juggle causes the complete list of keys to be repeated k times
        k=random.randint(2, len(list_of_AUCT_submission_fields)),
    )}
    log.info(f"Uploading files into the following fields:\n{format_list_for_stdout(fields_being_uploaded)}")
    form_submissions_fields = {}
    for label_ID, AUCT_option in fields_being_uploaded.items():
        form_submissions_fields[label_ID] = files_for_test_upload_historical_non_COUNTER_usage(AUCT_option)
        # There's no check against duplication in the files used, but for file uploads, a given file can be uploaded multiple times without a problem
    log.info(f"Submitting the following field and form combinations:\n{format_list_for_stdout(form_submissions_fields)}")
    form_submissions = MultipartEncoder(
        fields=form_submissions_fields,
        encoding='utf-8',
    )

    #Section: Confirm HTTP POST
    #Subsection: Submit Files via HTTP POST
    header_value['Content-Type'] = form_submissions.content_type
    POST_response = client.post(
        '/initialization/initialization-page-4/test',
        follow_redirects=True,
        headers=header_value,
        data=form_submissions,
    )
    POST_soup = BeautifulSoup(POST_response.data, 'lxml')
    POST_response_title = POST_soup.head.title
    POST_response_page_title = POST_soup.body.h1
    #ToDo: Add searches for displayed loaded data when `nolcat.initialization.views.data_load_complete()`/'initialization/show-loaded-data.html' displays such data

    #Subsection: Assert Statements
    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'initialization' / 'templates' / 'initialization' / 'show-loaded-data.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title
        HTML_file_page_title = file_soup.body.h1
    assert POST_response.history[0].status == "302 FOUND"  # This confirms there was a redirect
    assert POST_response.status == "200 OK"
    assert HTML_file_title == POST_response_title
    assert HTML_file_page_title == POST_response_page_title
    #ToDo: Add assert statements to match searches in above to-do

    #Section: Confirm Successful Database Update
    collection_status_and_file_path = []
    for record in fields_being_uploaded.values():
        df = query_database(
            query=f"SELECT collection_status, usage_file_path FROM annualUsageCollectionTracking WHERE AUCT_statistics_source={record[0][0]} AND AUCT_fiscal_year={record[0][1]};",
            engine=db.engine,
        )
        if isinstance(df, str):
            pytest.skip(database_function_skip_statements(df))
        collection_status_and_file_path.append((
            df.at[0,'collection_status'],
            df.at[0,'usage_file_path'],
        ))
    log.info(f"The records of the submissions have the following `annualUsageCollectionTracking.collection_status` and `annualUsageCollectionTracking.usage_file_path` values:\n{format_list_for_stdout(collection_status_and_file_path)}")
    for record in collection_status_and_file_path:
        assert record[0] == 'Collection complete'
        assert re.fullmatch(r"\d+_\d+\.\w{3,4}", record[1]) is not None

    #Section: Confirm Successful S3 Upload
    list_of_files_in_S3 = [record[1] for record in collection_status_and_file_path]
    list_objects_response = s3_client.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=f"{PATH_WITHIN_BUCKET_FOR_TESTS}",
    )
    log.debug(f"Raw contents of `{BUCKET_NAME}/{PATH_WITHIN_BUCKET_FOR_TESTS}` (type {type(list_objects_response)}):\n{format_list_for_stdout(list_objects_response)}.")
    files_in_bucket = []
    bucket_contents = list_objects_response.get('Contents')
    if bucket_contents:
        for contents_dict in bucket_contents:
            files_in_bucket.append(contents_dict['Key'])
        files_in_bucket = [file_name.replace(f"{PATH_WITHIN_BUCKET_FOR_TESTS}", "") for file_name in files_in_bucket]
        assert files_in_bucket.sort() == list_of_files_in_S3.sort()
    else:
        assert False  # Nothing in bucket