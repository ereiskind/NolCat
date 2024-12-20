"""Tests the routes in the `annual_stats` blueprint."""
########## Passing 2024-12-19 ##########

import pytest
import logging
from pathlib import Path
import os
from bs4 import BeautifulSoup

# `conftest.py` fixtures are imported automatically
from nolcat.app import *
from nolcat.statements import *
from nolcat.annual_stats import *

log = logging.getLogger(__name__)


def test_GET_request_for_annual_stats_homepage(engine, client, caplog):
    """Tests that the homepage can be successfully GET requested and that the response matches the file being used."""
    caplog.set_level(logging.INFO, logger='nolcat.app')  # For `query_database()`
    
    page = client.get('/annual_stats/')
    GET_soup = BeautifulSoup(page.data, 'lxml')
    GET_response_title = GET_soup.head.title
    GET_response_page_title = GET_soup.body.h1
    # GET_select_field_options = []
    # for child in GET_soup.find(name='select', id='fiscal_year').children:
    #     GET_select_field_options.append((
    #         int(child['value']),
    #         str(child.string),
    #     ))

    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'annual_stats' / 'templates' / 'annual_stats' / 'index.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title
        HTML_file_page_title = file_soup.body.h1
    db_select_field_options = query_database(
        query="SELECT fiscal_year_ID, fiscal_year FROM fiscalYears;",
        engine=engine,
    )
    if isinstance(db_select_field_options, str):
        pytest.skip(database_function_skip_statements(db_select_field_options))
    db_select_field_options = list(db_select_field_options.itertuples(index=False, name=None))

    assert page.status == "200 OK"
    assert HTML_file_title == GET_response_title
    assert HTML_file_page_title == GET_response_page_title
    #ToDo: `assert GET_select_field_options == db_select_field_options` when "annual_stats/index.html" is finished


def test_GET_request_for_show_fiscal_year_details():
    """Tests that the page displays the data for the given year from the `fiscalYears` and `annualUsageCollectionTracking` relations as well as the `annual_stats.RunAnnualStatsMethodsForm`, `annual_stats.EditFiscalYearForm`, and `annual_stats.EditAUCTForm` forms."""
    #ToDo: Write test
    pass


def test_show_fiscal_year_details_submitting_RunAnnualStatsMethodsForm():
    """Tests requesting an annual report."""
    # caplog.set_level(logging.INFO, logger='nolcat.app')  # For annual statistics calculation methods
    #ToDo: Write test
    pass


def test_show_fiscal_year_details_submitting_EditFiscalYearForm():
    """Tests changing the values in the fields of the displayed fiscal year."""
    #ToDo: Write test
    pass


def test_show_fiscal_year_details_submitting_EditAUCTForm():
    """Tests changing the values in the fields of one of the AUCT records being displayed."""
    #ToDo: Write test
    pass