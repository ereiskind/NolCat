"""Tests the routes in the `login` blueprint."""
########## Passing 2024-12-19 ##########

import pytest
import logging
from pathlib import Path
import os
from bs4 import BeautifulSoup

# `conftest.py` fixtures are imported automatically
from nolcat.app import *
from nolcat.login import *

log = logging.getLogger(__name__)


def test_login_homepage(client):
    """Tests that the homepage can be successfully GET requested and that the response matches the file being used."""
    page = client.get('/login/')
    GET_soup = BeautifulSoup(page.data, 'lxml')
    GET_response_title = GET_soup.head.title
    GET_response_page_title = GET_soup.body.h1

    with open(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'login' / 'templates' / 'login' / 'index.html', 'br') as HTML_file:
        file_soup = BeautifulSoup(HTML_file, 'lxml')
        HTML_file_title = file_soup.head.title
        HTML_file_page_title = file_soup.body.h1

    assert page.status == "200 OK"
    assert HTML_file_title == GET_response_title
    assert HTML_file_page_title == GET_response_page_title


def test_logging_in():
    """Create a test for the function."""
    #ToDo: If this function is created, write test and docstring
    pass


def test_logging_in_as_admin():
    """Create a test for the function."""
    #ToDo: If this function is created, write test and docstring
    pass


def test_creating_an_account():
    """Create a test for the function."""
    #ToDo: If this function is created, write test and docstring
    pass