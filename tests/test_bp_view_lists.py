"""Tests the routes in the `view_lists` blueprint."""
########## No tests written 2024-10-16 ##########

import pytest
import logging
from bs4 import BeautifulSoup

# `conftest.py` fixtures are imported automatically
from nolcat.app import *
from nolcat.view_lists import *

log = logging.getLogger(__name__)


@pytest.fixture(scope='module', params=["resources", "statistics", "vendors"])
def relation_and_record(request, engine):
    """A parameterized function providing a relation, the readable title for the relation, and a primary key for a record in the relation.

    Args:
        request (str): the relation whose records are being listed
        engine (sqlalchemy.engine.Engine): a SQLAlchemy engine

    Yields:
        tuple: the relation whose records are being listed, the readable title for that relation, and the primary key for a record in that relation
    """
    log.debug(f"Listing records in the {request} relation.")
    if request.param == "resources":
        query = "SELECT resource_source_ID FROM resourceSources;"
        readable_title = "Resource Sources"
    elif request.param == "statistics":
        query = "SELECT statistics_source_ID FROM statisticsSources;"
        readable_title = "Statistics Sources"
    elif request.param == "vendors":
        query = "SELECT vendor_ID FROM vendors;"
        readable_title = "Vendors"
    
    PKs = query_database(
        query=query,
        engine=engine,
    )
    if isinstance(PKs, str):
        pytest.skip(database_function_skip_statements(PKs))
    PK = extract_value_from_single_value_df(PKs.sample())
    log.debug(f"Viewing and editing record {PK}.")
    yield(request.param, readable_title, PK)


def test_view_lists_homepage(client, relation_and_record):
    """Tests that the homepage can be successfully GET requested and that the response matches the file being used."""
    relation, readable_title, record_PK = relation_and_record
    page = client.get(f'/view_lists/{relation}')
    GET_soup = BeautifulSoup(page.data, 'lxml')
    GET_response_title = GET_soup.head.title
    GET_response_page_title = GET_soup.body.h1
    log.warning(f"`GET_response_page_title` (type {type(GET_response_page_title)}):\n{GET_response_page_title}")  #TEST: temp

    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'view_lists' / 'templates' / 'view_lists' / 'index.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title.replace("{{ title }}", readable_title)
        HTML_file_page_title = file_soup.body.h1.replace("{{ title }}", readable_title)

    assert page.status == "200 OK"
    assert HTML_file_title == GET_response_title
    assert HTML_file_page_title == GET_response_page_title


def test_GET_request_for_view_list_record():
    """Tests that the page with a record's details and affiliated notes can be successfully GET requested."""
    #ToDo: Write test
    pass


def test_view_list_record():
    """Tests adding a record to the notes relation appropriate for the record the note is being added to.
    
    The function name derives from the fact that adding a note is the behavior after `validate_on_submit()` in the `view_list_record()` route.
    """
    #ToDo: Write test
    pass


def test_GET_request_for_edit_list_record_for_existing_record():
    """Tests rendering the page with the edit record form prefilled with values from an existing record."""
    #ToDo: Write test
    pass


def test_GET_request_for_edit_list_record_for_new_record():
    """Tests rendering a blank edit record form page."""
    #ToDo: Write test
    pass


def test_edit_list_record():
    """Tests changing values in a given record."""
    #ToDo: Write test
    pass