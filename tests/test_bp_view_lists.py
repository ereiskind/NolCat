"""Tests the routes in the `view_lists` blueprint."""
########## No tests written 2024-12-19 ##########

import pytest
import logging
from bs4 import BeautifulSoup

# `conftest.py` fixtures are imported automatically
from nolcat.app import *
from nolcat.view_lists import *

log = logging.getLogger(__name__)


def test_view_lists_homepage(client):
    """Tests that the homepage can be successfully GET requested and that the response matches the file being used."""
    #ToDo: Either randomly choose from or iterate through the route options = ["resources", "statistics", "vendors"]

    #page = client.get('/view_lists/')  #ToDo: Add variable route element
    #GET_soup = BeautifulSoup(page.data, 'lxml')
    #GET_response_title = GET_soup.head.title
    #GET_response_page_title = GET_soup.body.h1

    #with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'view_lists' / 'templates' / 'view_lists' / 'index.html', 'br') as HTML_file:
    #    file_soup = BeautifulSoup(HTML_file, 'lxml')
    #    HTML_file_title = file_soup.head.title  #ToDo: Replace `{{ title }}` with value from route function corresponding to the string in the homepage route
    #    HTML_file_page_title = file_soup.body.h1  #ToDo: Replace `{{ title }}` with value from route function corresponding to the string in the homepage route

    #assert page.status == "200 OK"
    #assertHTML_file_title == GET_response_title
    #assertHTML_file_page_title == GET_response_page_title
    pass


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