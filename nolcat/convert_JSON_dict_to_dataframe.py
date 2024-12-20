import logging
import re
from datetime import date
from datetime import datetime
from dateutil import parser
import json
from copy import deepcopy
import io
from math import ceil
import pandas as pd

from .app import *
# `from .models import *` to use `COUNTERData.state_data_types()` causes a circular import error

log = logging.getLogger(__name__)


class ConvertJSONDictToDataframe:
    """A class for transforming the Python dictionary versions of JSONs returned by a SUSHI API call into dataframes.

    SUSHI API calls return data in a JSON format, which is easily converted to a Python dictionary; this conversion is done in the `SUSHICallAndResponse.make_SUSHI_call()` method. The conversion from a heavily nested dictionary to a dataframe, however, is much more complicated, as none of the built-in dataframe constructors can be employed. This class exists to convert the SUSHI JSON-derived dictionaries into dataframes that can be loaded into the `COUNTERData` relation; since the desired behavior is more that of a function than a class, the would-be function becomes a class by dividing it into the traditional `__init__` method, which instantiates the dictionary as a class attribute, and the `create_dataframe()` method, which performs the actual transformation. This structure requires all instances of the class constructor to be prepended to a call to the `create_dataframe()` method, which means objects of the `ConvertJSONDictToDataframe` type are never instantiated.

    Attributes:
        self.RESOURCE_NAME_LENGTH (int): A class variable for the length of the `COUNTERData.resource_name` and `COUNTERData.parent_title` fields.
        self.PUBLISHER_LENGTH (int): A class variable for the length of the `COUNTERData.publisher` field.
        self.PUBLISHER_ID_LENGTH (int): A class variable for the length of the `COUNTERData.publisher_ID` field.
        self.PLATFORM_LENGTH (int): A class variable for the length of the `COUNTERData.platform` field.
        self.AUTHORS_LENGTH (int): A class variable for the length of the `COUNTERData.authors` and `COUNTERData.parent_authors` fields.
        self.DOI_LENGTH (int): A class variable for the length of the `COUNTERData.DOI` and `COUNTERData.parent_DOI` fields.
        self.PROPRIETARY_ID_LENGTH (int): A class variable for the length of the `COUNTERData.proprietary_ID` and `COUNTERData.parent_proprietary_ID` fields.
        self.URI_LENGTH (int): A class variable for the length of the `COUNTERData.URI` and `COUNTERData.parent_URI` fields.
        self.SUSHI_JSON_dictionary (dict): The constructor method for `ConvertJSONDictToDataframe`, which instantiates the dictionary object.

    Methods:
        create_dataframe: This method applies the appropriate private method to the dictionary derived from the SUSHI call response JSON to make it into a single dataframe ready to be loaded into the `COUNTERData` relation or saves the JSON as a file if it cannot be successfully converted into a dataframe.
        _transform_R5_JSON: This method transforms the data from the dictionary derived from a R5 SUSHI call response JSON into a single dataframe ready to be loaded into the `COUNTERData` relation.
        _transform_R5b1_JSON: This method transforms the data from the dictionary derived from a R5.1 SUSHI call response JSON into a single dataframe ready to be loaded into the `COUNTERData` relation.
        _serialize_dates: This method allows the `json.dumps()` method to serialize (convert) `datetime.datetime` and `datetime.date` attributes into strings.
        _extraction_start_logging_statement: This method creates the logging statement at the beginning of an attribute value extraction.
        _extraction_complete_logging_statement: This method creates the logging statement indicating a successful attribute value extraction.
        _increase_field_length_logging_statement: This method creates the logging statement indicating a field length needs to be increased.
    """
    # These field length constants allow the class to check that data in varchar fields without COUNTER-defined fixed vocabularies can be successfully uploaded to the `COUNTERData` relation; the constants are set here as class variables instead of in `models.py` to avoid a circular import
    RESOURCE_NAME_LENGTH = 3600
    PUBLISHER_LENGTH = 425
    PUBLISHER_ID_LENGTH = 150
    PLATFORM_LENGTH = 135
    AUTHORS_LENGTH = 4400
    DOI_LENGTH = 110
    PROPRIETARY_ID_LENGTH = 100
    URI_LENGTH = 450
    proprietary_ID_regex = re.compile(r"[Pp]roprietary(_ID)?")
    author_regex = re.compile("[Aa]uthor")

    def __init__(self, SUSHI_JSON_dictionary):
        """The constructor method for `ConvertJSONDictToDataframe`, which instantiates the dictionary object.

        This constructor is not meant to be used alone; all class instantiations should have a `create_dataframe()` method call appended to it.

        Args:
            SUSHI_JSON_dictionary (dict): The dictionary created by converting the JSON returned by the SUSHI API call into Python data types
        """
        self.SUSHI_JSON_dictionary = SUSHI_JSON_dictionary
    

    def create_dataframe(self):
        """This method applies the appropriate private method to the dictionary derived from the SUSHI call response JSON to make it into a single dataframe ready to be loaded into the `COUNTERData` relation or saves the JSON as a file if it cannot be successfully converted into a dataframe.

        This method is a wrapper that sends the JSON-like dictionaries containing all the data from the SUSHI API responses to either the `ConvertJSONDictToDataframe._transform_R5_JSON()` or the `ConvertJSONDictToDataframe._transform_R5b1_JSON()` methods depending on the release version of the API call. The `statistics_source_ID` and `report_type` fields are added after the dataframe is returned to the `StatisticsSources._harvest_R5_SUSHI()` method: the former because that information is proprietary to the NoLCAT instance; the latter because adding it there is less computing-intensive.

        Returns:
            dataframe: COUNTER data ready to be loaded into the `COUNTERData` relation
            str: the error message if the conversion fails
        """
        log.info("Starting `ConvertJSONDictToDataframe.create_dataframe()`.")
        try:
            report_header_creation_date = parser.isoparse(self.SUSHI_JSON_dictionary.get('Report_Header').get('Created')).date()  # Saving as datetime.date data type removes the time data  
        except Exception as error:
            log.warning(f"Parsing the `Created` field from the SUSHI report header into a Python date data type returned the error {error}. The current date, which is the likely value, is being substituted.")
            report_header_creation_date = date.today()
        log.debug(f"Report creation date is {report_header_creation_date} of type {type(report_header_creation_date)}.")
        COUNTER_release = self.SUSHI_JSON_dictionary['Report_Header']['Release']
        if COUNTER_release == "5":
            try:
                df = self._transform_R5_JSON(report_header_creation_date)
            except Exception as error:
                message = f"Attempting to convert the JSON-like dictionary created from a R5 SUSHI call unexpectedly raised the error {error}, meaning the data couldn't be loaded into the database. The JSON data is being saved instead."
                log.error(message)
                #ToDo: Save JSON as file
                return message
        elif COUNTER_release == "5.1":
            try:
                df = self._transform_R5b1_JSON(report_header_creation_date)
            except Exception as error:
                message = f"Attempting to convert the JSON-like dictionary created from a R5.1 SUSHI call unexpectedly raised the error {error}, meaning the data couldn't be loaded into the database. The JSON data is being saved instead."
                log.error(message)
                #ToDo: Save JSON as file
                return message
        else:
            message = f"The release of the JSON-like dictionary couldn't be identified, meaning the data couldn't be loaded into the database. The JSON data is being saved instead."
            log.error(message)
            #ToDo: Save JSON as file
            return message
        return df  # The method will only get here if one of the private harvest methods was successful


    def _transform_R5_JSON(self, report_creation_date):
        """This method transforms the data from the dictionary derived from a R5 SUSHI call response JSON into a single dataframe ready to be loaded into the `COUNTERData` relation.

        Args:
            report_creation_date (datetime.date): The date the report was created

        Returns:
            dataframe: COUNTER data ready to be loaded into the `COUNTERData` relation
            str: the error message if the conversion fails
        """
        log.info("Starting `ConvertJSONDictToDataframe._transform_R5_JSON()`.")
        records_orient_list = []

        #Section: Set Up Tracking of Fields to Include in `df_dtypes`
        include_in_df_dtypes = {  # Using `record_dict.get()` at the end doesn't work because any field with a null value in the last record won't be included
            'resource_name': False,
            'publisher': False,
            'publisher_ID': False,
            'authors': False,
            'publication_date': False,
            'article_version': False,
            'DOI': False,
            'proprietary_ID': False,
            'ISBN': False,
            'print_ISSN': False,
            'online_ISSN': False,
            'URI': False,
            'data_type': False,
            'section_type': False,
            'YOP': False,
            'access_type': False,
            'access_method': False,
            'parent_title': False,
            'parent_authors': False,
            'parent_publication_date': False,
            'parent_article_version': False,
            'parent_data_type': False,
            'parent_DOI': False,
            'parent_proprietary_ID': False,
            'parent_ISBN': False,
            'parent_print_ISSN': False,
            'parent_online_ISSN': False,
            'parent_URI': False,
        }

        #Section: Iterate Through JSON Records to Create Single-Level Dictionaries
        for record in self.SUSHI_JSON_dictionary['Report_Items']:
            log.debug(f"Starting iteration for new JSON record {record}.")
            record_dict = {"report_creation_date": report_creation_date}  # This resets the contents of `record_dict`, including removing any keys that might not get overwritten because they aren't included in the next iteration
            for key, value in record.items():

                #Subsection: Capture `resource_name` Value
                if key == "Database" or key == "Title" or key == "Item":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.resource_name`"))
                    if value is None or empty_string_regex().fullmatch(value):  # This value handled first because `len()` of null value raises an error
                        record_dict['resource_name'] = None
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("resource_name", record_dict['resource_name']))
                    elif len(value) > self.RESOURCE_NAME_LENGTH:
                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("resource_name", len(value))
                        log.critical(message)
                        return message
                    else:
                        record_dict['resource_name'] = value
                        include_in_df_dtypes['resource_name'] = 'string'
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("resource_name", record_dict['resource_name']))
                
                #Subsection: Capture `publisher` Value
                elif key == "Publisher":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.publisher`"))
                    if value is None or empty_string_regex().fullmatch(value):  # This value handled first because `len()` of null value raises an error
                        record_dict['publisher'] = None
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publisher", record_dict['publisher']))
                    elif len(value) > self.PUBLISHER_LENGTH:
                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("publisher", len(value))
                        log.critical(message)
                        return message
                    else:
                        record_dict['publisher'] = value
                        include_in_df_dtypes['publisher'] = 'string'
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publisher", record_dict['publisher']))
                
                #Subsection: Capture `publisher_ID` Value
                elif key == "Publisher_ID":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.publisher_ID`"))
                    if value is None or empty_string_regex().fullmatch(value):  # This value handled first because `len()` of null value raises an error
                        record_dict['publisher_ID'] = None
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publisher_ID", record_dict['publisher_ID']))
                    elif len(value) == 1:
                        if len(value[0]['Value']) > self.PUBLISHER_ID_LENGTH:
                            message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("publisher_ID", len(value[0]['Value']))
                            log.critical(message)
                            return message
                        else:
                            record_dict['publisher_ID'] = value[0]['Value']
                            include_in_df_dtypes['publisher_ID'] = 'string'
                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publisher_ID", record_dict['publisher_ID']))
                    else:
                        for type_and_value in value:
                            if self.proprietary_ID_regex.search(type_and_value['Type']):
                                if len(type_and_value['Value']) > self.PUBLISHER_ID_LENGTH:
                                    message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("publisher_ID", len(type_and_value['Value']))
                                    log.critical(message)
                                    return message
                                else:
                                    record_dict['publisher_ID'] = type_and_value['Value']
                                    include_in_df_dtypes['publisher_ID'] = 'string'
                                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publisher_ID", record_dict['publisher_ID']))
                            else:
                                continue  # The `for type_and_value in value` loop
                
                #Subsection: Capture `platform` Value
                elif key == "Platform":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.platform`"))
                    if value is None or empty_string_regex().fullmatch(value):  # This value handled first because `len()` of null value raises an error
                        record_dict['platform'] = None
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("platform", record_dict['platform']))
                    elif len(value) > self.PLATFORM_LENGTH:
                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("platform", len(value))
                        log.critical(message)
                        return message
                    else:
                        record_dict['platform'] = value
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("platform", record_dict['platform']))
                
                #Subsection: Capture `authors` Value
                elif key == "Item_Contributors":  # `Item_Contributors` uses `Name` instead of `Value`
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.authors`"))
                    for type_and_value in value:
                        if self.author_regex.search(type_and_value['Type']):
                            if record_dict.get('authors'):  # If the author name value is null, this will never be true
                                if record_dict['authors'].endswith(" et al."):
                                    continue  # The `for type_and_value in value` loop
                                elif len(record_dict['authors']) + len(type_and_value['Name']) + 8 > self.AUTHORS_LENGTH:
                                    record_dict['authors'] = record_dict['authors'] + " et al."
                                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("authors", record_dict['authors']))
                                else:
                                    record_dict['authors'] = record_dict['authors'] + "; " + type_and_value['Name']
                                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("authors", record_dict['authors']))
                            
                            else:
                                if type_and_value['Name'] is None or empty_string_regex().fullmatch(type_and_value['Name']):  # This value handled first because `len()` of null value raises an error
                                    record_dict['authors'] = None
                                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("authors", record_dict['authors']))
                                elif len(type_and_value['Name']) > self.AUTHORS_LENGTH:
                                    message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("authors", len(type_and_value['Name']))
                                    log.critical(message)
                                    return message
                                else:
                                    record_dict['authors'] = type_and_value['Name']
                                    include_in_df_dtypes['authors'] = 'string'
                                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("authors", record_dict['authors']))
                
                #Subsection: Capture `publication_date` Value
                elif key == "Item_Dates":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.publication_date`"))
                    for type_and_value in value:
                        if type_and_value['Value'] == "1000-01-01" or type_and_value['Value'] == "1753-01-01" or type_and_value['Value'] == "1900-01-01":
                            continue  # The `for type_and_value in value` loop; these dates are common RDBMS/spreadsheet minimum date data type values and are generally placeholders for null values or bad data
                        if type_and_value['Type'] == "Publication_Date":  # Unlikely to be more than one; if there is, the field's date/datetime64 data type prevent duplicates from being preserved
                            try:
                                record_dict['publication_date'] = date.fromisoformat(type_and_value['Value'])
                                include_in_df_dtypes['publication_date'] = True
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publication_date", record_dict['publication_date']))
                            except:  # In case `type_and_value['Value']` is null, which would cause the conversion to a datetime data type to return a TypeError
                                continue  # The `for type_and_value in value` loop
                
                #Subsection: Capture `article_version` Value
                elif key == "Item_Attributes":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.article_version`"))
                    for type_and_value in value:
                        if type_and_value['Type'] == "Article_Version":  # Very unlikely to be more than one
                            record_dict['article_version'] = type_and_value['Value']
                            include_in_df_dtypes['article_version'] = 'string'
                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("article_version", record_dict['article_version']))
                
                #Subsection: Capture Standard Identifiers
                # Null value handling isn't needed because all null values are removed
                elif key == "Item_ID":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "the proprietary ID fields"))
                    for type_and_value in value:
                        
                        #Subsection: Capture `DOI` Value
                        if type_and_value['Type'] == "DOI":
                            if len(type_and_value['Value']) > self.DOI_LENGTH:
                                message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("DOI", len(type_and_value['Value']))
                                log.critical(message)
                                return message
                            else:
                                record_dict['DOI'] = type_and_value['Value']
                                include_in_df_dtypes['DOI'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("DOI", record_dict['DOI']))
                        
                        #Subsection: Capture `proprietary_ID` Value
                        elif self.proprietary_ID_regex.search(type_and_value['Type']):
                            if len(type_and_value['Value']) > self.PROPRIETARY_ID_LENGTH:
                                message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("proprietary_ID", len(type_and_value['Value']))
                                log.critical(message)
                                return message
                            else:
                                record_dict['proprietary_ID'] = type_and_value['Value']
                                include_in_df_dtypes['proprietary_ID'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("proprietary_ID", record_dict['proprietary_ID']))
                        
                        #Subsection: Capture `ISBN` Value
                        elif type_and_value['Type'] == "ISBN":
                            record_dict['ISBN'] = str(type_and_value['Value'])
                            include_in_df_dtypes['ISBN'] = 'string'
                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("ISBN", record_dict['ISBN']))
                        
                        #Subsection: Capture `print_ISSN` Value
                        elif type_and_value['Type'] == "Print_ISSN":
                            if ISSN_regex().fullmatch(type_and_value['Value']):
                                record_dict['print_ISSN'] = type_and_value['Value'].strip()
                                include_in_df_dtypes['print_ISSN'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("print_ISSN", record_dict['print_ISSN']))
                            else:
                                record_dict['print_ISSN'] = str(type_and_value['Value'])[:5] + "-" + str(type_and_value['Value']).strip()[-4:]
                                include_in_df_dtypes['print_ISSN'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("print_ISSN", record_dict['print_ISSN']))
                        
                        #Subsection: Capture `online_ISSN` Value
                        elif type_and_value['Type'] == "Online_ISSN":
                            if ISSN_regex().fullmatch(type_and_value['Value']):
                                record_dict['online_ISSN'] = type_and_value['Value'].strip()
                                include_in_df_dtypes['online_ISSN'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("online_ISSN", record_dict['online_ISSN']))
                            else:
                                record_dict['online_ISSN'] = str(type_and_value['Value'])[:5] + "-" + str(type_and_value['Value']).strip()[-4:]
                                include_in_df_dtypes['online_ISSN'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("online_ISSN", record_dict['online_ISSN']))
                        
                        #Subsection: Capture `URI` Value
                        elif type_and_value['Type'] == "URI":
                            if len(type_and_value['Value']) > self.URI_LENGTH:
                                message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("URI", len(type_and_value['Value']))
                                log.critical(message)
                                return message
                            else:
                                record_dict['URI'] = type_and_value['Value']
                                include_in_df_dtypes['URI'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("URI", record_dict['URI']))
                        
                        else:
                            continue  # The `for type_and_value in value` loop
                
                #Subsection: Capture `data_type` Value
                elif key == "Data_Type":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.data_type`"))
                    record_dict['data_type'] = value
                    include_in_df_dtypes['data_type'] = 'string'
                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("data_type", record_dict['data_type']))
                
                #Subsection: Capture `section_Type` Value
                elif key == "Section_Type":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.section_type`"))
                    record_dict['section_type'] = value
                    include_in_df_dtypes['section_type'] = 'string'
                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("section_type", record_dict['section_type']))

                #Subsection: Capture `YOP` Value
                elif key == "YOP":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.YOP`"))
                    try:
                        record_dict['YOP'] = int(value)  # The Int16 dtype doesn't have a constructor, so this value is saved as an int for now and transformed when when the dataframe is created
                        include_in_df_dtypes['YOP'] = 'Int16'  # `smallint` in database; using the pandas data type here because it allows null values
                    except:
                        record_dict['YOP'] = None  # The dtype conversion that occurs when this becomes a dataframe will change this to pandas' `NA`
                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("YOP", record_dict['YOP']))
                
                #Subsection: Capture `access_type` Value
                elif key == "Access_Type":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.access_type`"))
                    record_dict['access_type'] = value
                    include_in_df_dtypes['access_type'] = 'string'
                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("access_type", record_dict['access_type']))
                
                #Subsection: Capture `access_method` Value
                elif key == "Access_Method":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.access_method`"))
                    record_dict['access_method'] = value
                    include_in_df_dtypes['access_method'] = 'string'
                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("access_method", record_dict['access_method']))
                
                #Subsection: Capture Parent Resource Metadata
                # Null value handling isn't needed because all null values are removed
                elif key == "Item_Parent":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "the parent metadata fields"))
                    if isinstance(value, list) and len(value) == 1:  # The `Item_Parent` value should be a dict, but sometimes that dict is within a one-item list; this removes the outer list
                        value = value[0]
                    for key_for_parent, value_for_parent in value.items():

                        #Subsection: Capture `parent_title` Value
                        if key_for_parent == "Item_Name":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value_for_parent, key_for_parent, "`COUNTERData.parent_title`"))
                            if len(value_for_parent) > self.RESOURCE_NAME_LENGTH:
                                message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("parent_title", len(value_for_parent))
                                log.critical(message)
                                return message
                            else:
                                record_dict['parent_title'] = value_for_parent
                                include_in_df_dtypes['parent_title'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_title", record_dict['parent_title']))
                        
                        #Subsection: Capture `parent_authors` Value
                        elif key_for_parent == "Item_Contributors":  # `Item_Contributors` uses `Name` instead of `Value`
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value_for_parent, key_for_parent, "`COUNTERData.parent_authors`"))
                            for type_and_value in value_for_parent:
                                if self.author_regex.search(type_and_value['Type']):
                                    if record_dict.get('parent_authors'):
                                        if record_dict['parent_authors'].endswith(" et al."):
                                            continue  # The `for type_and_value in value_for_parent` loop
                                        elif len(record_dict['parent_authors']) + len(type_and_value['Name']) + 8 > self.AUTHORS_LENGTH:
                                            record_dict['parent_authors'] = record_dict['parent_authors'] + " et al."
                                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_authors", record_dict['parent_authors']))
                                        else:
                                            record_dict['parent_authors'] = record_dict['parent_authors'] + "; " + type_and_value['Name']
                                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_authors", record_dict['parent_authors']))
                                    else:
                                        if len(type_and_value['Name']) > self.AUTHORS_LENGTH:
                                            message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("authors", len(type_and_value['Name']))
                                            log.critical(message)
                                            return message
                                        else:
                                            record_dict['parent_authors'] = type_and_value['Name']
                                            include_in_df_dtypes['parent_authors'] = 'string'
                                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_authors", record_dict['parent_authors']))
                        
                        #Subsection: Capture `parent_publication_date` Value
                        elif key_for_parent == "Item_Dates":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value_for_parent, key_for_parent, "`COUNTERData.parent_publication_date`"))
                            for type_and_value in value_for_parent:
                                if type_and_value['Value'] == "1000-01-01" or type_and_value['Value'] == "1753-01-01" or type_and_value['Value'] == "1900-01-01":
                                    continue  # The `for type_and_value in value` loop; these dates are common RDBMS/spreadsheet minimum date data type values and are generally placeholders for null values or bad data
                                if type_and_value['Type'] == "Publication_Date":  # Unlikely to be more than one; if there is, the field's date/datetime64 data type prevent duplicates from being preserved
                                    record_dict['parent_publication_date'] = date.fromisoformat(type_and_value['Value'])
                                    include_in_df_dtypes['parent_publication_date'] = True
                                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_publication_date", record_dict['parent_publication_date']))
                        
                        #Subsection: Capture `parent_article_version` Value
                        elif key_for_parent == "Item_Attributes":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value_for_parent, key_for_parent, "`COUNTERData.parent_article_version`"))
                            for type_and_value in value_for_parent:
                                if type_and_value['Type'] == "Article_Version":  # Very unlikely to be more than one
                                    record_dict['parent_article_version'] = type_and_value['Value']
                                    include_in_df_dtypes['parent_article_version'] = 'string'
                                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_article_version", record_dict['parent_article_version']))

                        #Subsection: Capture `parent_data_type` Value
                        elif key_for_parent == "Data_Type":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value_for_parent, key_for_parent, "`COUNTERData.parent_data_type`"))
                            record_dict['parent_data_type'] = value_for_parent
                            include_in_df_dtypes['parent_data_type'] = 'string'
                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_data_type", record_dict['parent_data_type']))
                        
                        #Subsection: Capture Parent Standard Identifiers
                        elif key_for_parent == "Item_ID":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value_for_parent, key_for_parent, "the parent proprietary ID fields"))
                            for type_and_value in value_for_parent:
                                
                                #Subsection: Capture `parent_DOI` Value
                                if type_and_value['Type'] == "DOI":
                                    if len(type_and_value['Value']) > self.DOI_LENGTH:
                                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("parent_DOI", len(type_and_value['Value']))
                                        log.critical(message)
                                        return message
                                    else:
                                        record_dict['parent_DOI'] = type_and_value['Value']
                                        include_in_df_dtypes['parent_DOI'] = 'string'
                                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_DOI", record_dict['parent_DOI']))

                                #Subsection: Capture `parent_proprietary_ID` Value
                                elif self.proprietary_ID_regex.search(type_and_value['Type']):
                                    if len(type_and_value['Value']) > self.PROPRIETARY_ID_LENGTH:
                                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("parent_proprietary_ID", len(type_and_value['Value']))
                                        log.critical(message)
                                        return message
                                    else:
                                        record_dict['parent_proprietary_ID'] = type_and_value['Value']
                                        include_in_df_dtypes['parent_proprietary_ID'] = 'string'
                                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_proprietary_ID", record_dict['parent_proprietary_ID']))

                                #Subsection: Capture `parent_ISBN` Value
                                elif type_and_value['Type'] == "ISBN":
                                    record_dict['parent_ISBN'] = str(type_and_value['Value'])
                                    include_in_df_dtypes['parent_ISBN'] = 'string'
                                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_ISBN", record_dict['parent_ISBN']))

                                #Subsection: Capture `parent_print_ISSN` Value
                                elif type_and_value['Type'] == "Print_ISSN":
                                    if ISSN_regex().fullmatch(type_and_value['Value']):
                                        record_dict['parent_print_ISSN'] = type_and_value['Value'].strip()
                                        include_in_df_dtypes['parent_print_ISSN'] = 'string'
                                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_print_ISSN", record_dict['parent_print_ISSN']))
                                    else:
                                        record_dict['parent_print_ISSN'] = str(type_and_value['Value'])[:5] + "-" + str(type_and_value['Value']).strip()[-4:]
                                        include_in_df_dtypes['parent_print_ISSN'] = 'string'
                                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_print_ISSN", record_dict['parent_print_ISSN']))

                                #Subsection: Capture `parent_online_ISSN` Value
                                elif type_and_value['Type'] == "Online_ISSN":
                                    if ISSN_regex().fullmatch(type_and_value['Value']):
                                        record_dict['parent_online_ISSN'] = type_and_value['Value'].strip()
                                        include_in_df_dtypes['parent_online_ISSN'] = 'string'
                                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_online_ISSN", record_dict['parent_online_ISSN']))
                                    else:
                                        record_dict['parent_online_ISSN'] = str(type_and_value['Value'])[:5] + "-" + str(type_and_value['Value']).strip()[-4:]
                                        include_in_df_dtypes['parent_online_ISSN'] = 'string'
                                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_online_ISSN", record_dict['parent_online_ISSN']))

                                #Subsection: Capture `parent_URI` Value
                                elif type_and_value['Type'] == "URI":
                                    if len(type_and_value['Value']) > self.URI_LENGTH:
                                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("parent_URI", len(type_and_value['Value']))
                                        log.critical(message)
                                        return message
                                    else:
                                        record_dict['parent_URI'] = type_and_value['Value']
                                        include_in_df_dtypes['parent_URI'] = 'string'
                                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("parent_URI", record_dict['parent_URI']))

                        else:
                            continue  # The `for key_for_parent, value_for_parent in value.items()` loop

                elif key == "Performance":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "the temporary key for date, metric type, and usage count values"))
                    record_dict['temp'] = value

                else:
                    log.warning(f"The unexpected key `{key}` was found in the JSON response to a SUSHI API call.")
                    pass
            
            #Section: Create Records by Iterating Through `Performance` Section of SUSHI JSON
            performance = record_dict.pop('temp')
            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(performance, "temp", "the `COUNTERData.usage_date`, `COUNTERData.metric_type`, and `COUNTERData.usage_count` fields"))
            for period_grouping in performance:
                record_dict['usage_date'] = date.fromisoformat(period_grouping['Period']['Begin_Date'])
                for instance in period_grouping['Instance']:
                    record_dict['metric_type'] = instance['Metric_Type']
                    record_dict['usage_count'] = instance['Count']
                    records_orient_list.append(deepcopy(record_dict))  # Appending `record_dict` directly adds a reference to that variable, which changes with each iteration of the loop, meaning all the records for a given set of metadata have the `usage_date`, `metric_type`, and `usage_count` values of `record_dict` during the final iteration
                    log.debug(f"Added record {record_dict} to `COUNTERData` relation.")  # Set to logging level debug because when all these logging statements are sent to AWS stdout, the only pytest output visible is the error summary statements

        #Section: Create Dataframe
        log.info(f"Unfiltered `include_in_df_dtypes`: {include_in_df_dtypes}")
        include_in_df_dtypes = {k: v for (k, v) in include_in_df_dtypes.items() if v is not False}  # Using `is` for comparison because `1 != False` returns `True` in Python
        log.debug(f"Filtered `include_in_df_dtypes`: {include_in_df_dtypes}")
        df_dtypes = {k: v for (k, v) in include_in_df_dtypes.items() if v is not True}
        df_dtypes['platform'] = 'string'
        df_dtypes['metric_type'] = 'string'
        df_dtypes['usage_count'] = 'int'
        log.info(f"`df_dtypes`: {df_dtypes}")

        log.debug(f"`records_orient_list` before `json.dumps()`  is type {type(records_orient_list)}.")
        records_orient_list = json.dumps(  # `pd.read_json` takes a string, conversion done before method for ease in handling type conversions
            records_orient_list,
            default=ConvertJSONDictToDataframe._serialize_dates,
        )
        if len(records_orient_list) > 1500:
            log.debug(f"`records_orient_list` after `json.dumps()` (type {type(records_orient_list)}) is too long to display.")
        else:
            log.debug(f"`records_orient_list` after `json.dumps()` (type {type(records_orient_list)}):\n{records_orient_list}")
        df = pd.read_json(
            io.StringIO(records_orient_list),  # Originally from https://stackoverflow.com/a/63655099 in `except` block; now only option due to `FutureWarning: Passing literal json to 'read_json' is deprecated and will be removed in a future version. To read from a literal string, wrap it in a 'StringIO' object.`
            orient='records',
            dtype=df_dtypes,  # This only sets numeric data types
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        log.info(f"Dataframe info immediately after dataframe creation:\n{return_string_of_dataframe_info(df)}")

        df = df.astype(df_dtypes)  # This sets the string data types
        log.debug(f"Dataframe dtypes after conversion:\n{return_string_of_dataframe_info(df)}")
        if include_in_df_dtypes.get('publication_date'):  # Meaning the value was changed to `True`
            df['publication_date'] = pd.to_datetime(
                df['publication_date'],
                errors='coerce',  # Changes the null values to the date dtype's null value `NaT`
            )
        if include_in_df_dtypes.get('parent_publication_date'):  # Meaning the value was changed to `True`
            df['parent_publication_date'] = pd.to_datetime(
                df['parent_publication_date'],
                errors='coerce',  # Changes the null values to the date dtype's null value `NaT`
            )
        df['usage_date'] = pd.to_datetime(df['usage_date'])
        df['report_creation_date'] = pd.to_datetime(df['report_creation_date'])#.dt.tz_localize(None)

        log.info(f"Dataframe info:\n{return_string_of_dataframe_info(df)}")
        return df


    def _transform_R5b1_JSON(self, report_creation_date):
        """This method transforms the data from the dictionary derived from a R5.1 SUSHI call response JSON into a single dataframe ready to be loaded into the `COUNTERData` relation.

        Args:
            report_creation_date (datetime.date): The date the report was created

        Returns:
            dataframe: COUNTER data ready to be loaded into the `COUNTERData` relation
            str: the error message if the conversion fails
        """
        log.info("Starting `ConvertJSONDictToDataframe._transform_R5b1_JSON()`.")
        report_type = self.SUSHI_JSON_dictionary['Report_Header']['Report_ID']
        records_orient_list = []
        
        #Section: Set Up Tracking of Fields to Include in `df_dtypes`
        include_in_df_dtypes = {
            'resource_name': False,
            'publisher': False,
            'publisher_ID': False,
            'authors': False,
            'publication_date': False,
            'article_version': False,
            'DOI': False,
            'proprietary_ID': False,
            'ISBN': False,
            'print_ISSN': False,
            'online_ISSN': False,
            'URI': False,
            'data_type': False,
            'section_type': False,
            'YOP': False,
            'access_type': False,
            'access_method': False,
            'parent_title': False,
            'parent_authors': False,
            'parent_publication_date': False,
            'parent_article_version': False,
            'parent_data_type': False,
            'parent_DOI': False,
            'parent_proprietary_ID': False,
            'parent_ISBN': False,
            'parent_print_ISSN': False,
            'parent_online_ISSN': False,
            'parent_URI': False,
        }

        #Section: Iterate Through `Report_Items` of SUSHI JSON to Create Single-Level Dictionaries
        for record in self.SUSHI_JSON_dictionary['Report_Items']:
            log.debug(f"Starting iteration for new JSON record {record}.")
            report_items_dict = {"report_creation_date": report_creation_date}  # This resets the contents of `report_items_dict`, including removing any keys that might not get overwritten because they aren't included in the next iteration
            for key, value in record.items():
                second_iteration_keys = []

                #Subsection: Capture `resource_name` or `parent_title` Value
                if key == "Database" or key == "Title":
                    if report_type == "IR":
                        field = "parent_title"
                    else:
                        field = "resource_name"
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, f"`COUNTERData.{field}`"))
                    if value is None or empty_string_regex().fullmatch(value):  # This value handled first because `len()` of null value raises an error
                        report_items_dict[field] = None
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement(field, report_items_dict[field]))
                    elif len(value) > self.RESOURCE_NAME_LENGTH:
                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement(field, len(value))
                        log.critical(message)
                        return message
                    else:
                        report_items_dict[field] = value
                        include_in_df_dtypes[field] = 'string'
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement(field, report_items_dict[field]))

                #Subsection: Capture `publisher` Value
                elif key == "Publisher":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.publisher`"))
                    if value is None or empty_string_regex().fullmatch(value):  # This value handled first because `len()` of null value raises an error
                        report_items_dict['publisher'] = None
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publisher", report_items_dict['publisher']))
                    elif len(value) > self.PUBLISHER_LENGTH:
                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("publisher", len(value))
                        log.critical(message)
                        return message
                    else:
                        report_items_dict['publisher'] = value
                        include_in_df_dtypes['publisher'] = 'string'
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publisher", report_items_dict['publisher']))

                #Subsection: Capture `publisher_ID` Value
                elif key == "Publisher_ID":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.publisher_ID`"))
                    pass

                #Subsection: Capture `platform` Value
                elif key == "Platform":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.platform`"))
                    if value is None or empty_string_regex().fullmatch(value):  # This value handled first because `len()` of null value raises an error
                        report_items_dict['platform'] = None
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("platform", report_items_dict['platform']))
                    elif len(value) > self.PLATFORM_LENGTH:
                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("platform", len(value))
                        log.critical(message)
                        return message
                    else:
                        report_items_dict['platform'] = value
                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("platform", report_items_dict['platform']))

                #Subsection: Capture `authors` or `parent_authors` Value
                elif key == "Item_Contributors":  # `Item_Contributors` uses `Name` instead of `Value`
                    if report_type == "IR":
                        field = "parent_authors"
                    else:
                        field = "authors"
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, f"`COUNTERData.{field}`"))
                    pass

                #Subsection: Capture `publication_date` or `parent_publication_date` Value
                elif key == "Item_Dates":
                    if report_type == "IR":
                        field = "parent_publication_date"
                    else:
                        field = "publication_date"
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, f"`COUNTERData.{field}`"))
                    pass

                #Subsection: Capture `article_version` or `parent_article_version` Value
                elif key == "Item_Attributes":
                    if report_type == "IR":
                        field = "parent_article_version"
                    else:
                        field = "article_version"
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, f"`COUNTERData.{field}`"))
                    pass

                #Subsection: Capture Standard Identifiers or Parent Standard Identifiers
                # Null value handling isn't needed because all null values are removed
                elif key == "Item_ID":
                    if report_type == "DR" or report_type == "TR":
                        log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "the standard ID fields"))
                    else:
                        log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "the parent standard ID fields"))
                    for ID_type, ID_value in value.items():

                        #Subsection: Capture `DOI` or `parent_DOI` Value
                        if ID_type == "DOI":
                            if report_type == "IR":
                                field = "parent_DOI"
                            else:
                                field = "DOI"
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, f"`COUNTERData.{field}`"))
                            if len(ID_value) > self.DOI_LENGTH:
                                message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("DOI", len(ID_value))
                                log.critical(message)
                                return message
                            else:
                                report_items_dict[field] = ID_value
                                include_in_df_dtypes[field] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement(field, report_items_dict[field]))

                        #Subsection: Capture `proprietary_ID` or `parent_proprietary_ID` Value
                        elif self.proprietary_ID_regex.search(ID_type):
                            if report_type == "IR":
                                field = "parent_proprietary_ID"
                            else:
                                field = "proprietary_ID"
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, f"`COUNTERData.{field}`"))
                            if len(ID_value) > self.PROPRIETARY_ID_LENGTH:
                                message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("proprietary_ID", len(ID_value))
                                log.critical(message)
                                return message
                            else:
                                report_items_dict[field] = ID_value
                                include_in_df_dtypes[field] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement(field, report_items_dict[field]))

                        #Subsection: Capture `ISBN` or `parent_ISBN` Value
                        elif ID_type == "ISBN":
                            if report_type == "IR":
                                field = "parent_ISBN"
                            else:
                                field = "ISBN"
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, f"`COUNTERData.{field}`"))
                            pass

                        #Subsection: Capture `print_ISSN` or `parent_print_ISSN` Value
                        elif ID_type == "Print_ISSN":
                            if report_type == "IR":
                                field = "parent_print_ISSN"
                            else:
                                field = "print_ISSN"
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, f"`COUNTERData.{field}`"))
                            if ISSN_regex().fullmatch(ID_value):
                                report_items_dict[field] = ID_value.strip()
                                include_in_df_dtypes[field] = 'string'
                            else:
                                report_items_dict[field] = str(ID_value)[:5] + "-" + str(ID_value).strip()[-4:]
                                include_in_df_dtypes[field] = 'string'
                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement(field, report_items_dict[field]))

                        #Subsection: Capture `online_ISSN` or `parent_online_ISSN` Value
                        elif ID_type == "Online_ISSN":
                            if report_type == "IR":
                                field = "parent_online_ISSN"
                            else:
                                field = "online_ISSN"
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, f"`COUNTERData.{field}`"))
                            pass

                        #Subsection: Capture `URI` or `parent_URI` Value
                        elif ID_type == "URI":
                            if report_type == "IR":
                                field = "parent_URI"
                            else:
                                field = "URI"
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, f"`COUNTERData.{field}`"))
                            pass

                #Subsection: Capture `data_type` or `parent_data_type` Value
                elif key == "Data_Type":
                    if report_type == "IR":
                        field = "parent_data_type"
                    else:
                        field = "data_type"
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, f"`COUNTERData.{field}`"))
                    report_items_dict[field] = value
                    include_in_df_dtypes[field] = 'string'
                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("data_type", report_items_dict[field]))

                #Subsection: Capture `YOP` Value
                elif key == "YOP":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.YOP`"))
                    pass

                #Subsection: Capture `access_type` Value
                elif key == "Access_Type":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.access_type`"))
                    pass

                #Subsection: Capture `access_method` Value
                elif key == "Access_Method":
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "`COUNTERData.access_method`"))
                    pass

                else:
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(value, key, "a placeholder for later unpacking"))
                    report_items_dict[key] = value
                    second_iteration_keys.append(key)

            #Section: Iterate Through `Items` Sections of IR SUSHI JSON
            if "Items" in second_iteration_keys and report_type == "IR":
                for i_item in report_items_dict['Items']:
                    items_dict = {k: v for (k, v) in report_items_dict.items() if k not in second_iteration_keys}
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(i_item, "Items", "keys at the top level of the JSON"))
                    for i_key, i_value in i_item.items():

                        #Subsection: Capture `resource_name` Value
                        if i_key == "Item":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(i_value, i_key, "`COUNTERData.resource_name`"))
                            if i_value is None or empty_string_regex().fullmatch(i_value):  # This value handled first because `len()` of null value raises an error
                                items_dict['resource_name'] = None
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("resource_name", items_dict['resource_name']))
                            elif len(value) > self.RESOURCE_NAME_LENGTH:
                                message = ConvertJSONDictToDataframe._increase_field_length_logging_statement(field, len(i_value))
                                log.critical(message)
                                return message
                            else:
                                items_dict['resource_name'] = i_value
                                include_in_df_dtypes['resource_name'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("resource_name", items_dict['resource_name']))

                        #Subsection: Capture `publisher` Value
                        elif i_key == "Publisher":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(i_value, i_key, "`COUNTERData.publisher`"))
                            if i_value is None or empty_string_regex().fullmatch(i_value):  # This value handled first because `len()` of null value raises an error
                                items_dict['publisher'] = None
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publisher", items_dict['publisher']))
                            elif len(i_value) > self.PUBLISHER_LENGTH:
                                message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("publisher", len(i_value))
                                log.critical(message)
                                return message
                            else:
                                items_dict['publisher'] = i_value
                                include_in_df_dtypes['publisher'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publisher", items_dict['publisher']))

                        #Subsection: Capture `publisher_ID` Value
                        elif i_key == "Publisher_ID":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(i_value, i_key, "`COUNTERData.publisher_ID`"))
                            pass

                        #Subsection: Capture `platform` Value
                        elif i_key == "Platform":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(i_value, i_key, "`COUNTERData.platform`"))
                            if i_value is None or empty_string_regex().fullmatch(i_value):  # This value handled first because `len()` of null value raises an error
                                items_dict['platform'] = None
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("platform", items_dict['platform']))
                            elif len(i_value) > self.PLATFORM_LENGTH:
                                message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("platform", len(i_value))
                                log.critical(message)
                                return message
                            else:
                                items_dict['platform'] = i_value
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("platform", items_dict['platform']))

                        #Subsection: Capture `authors` Value
                        elif i_key == "Authors":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(i_value, i_key, "`COUNTERData.authors`"))
                            number_of_authors = len(i_value)
                            for type_and_value in i_value:
                                if number_of_authors > 1:  # Multiple authors
                                    for name in type_and_value.values():
                                        if items_dict['authors'].endswith(" et al."):
                                            break  # The loop of adding author names
                                        elif len(items_dict['authors']) + len(name) + 10 < self.AUTHORS_LENGTH:
                                            items_dict['authors'] = items_dict['authors'] + ", " + name.strip()
                                        else:
                                            items_dict['authors'] = items_dict['authors'] + " et al."
                                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("authors", items_dict['authors']))  #ALERT: Original update statement used "Updated" instead of "Added"; does that change need to be preserved?
                                else:
                                    if type_and_value['Name'] is None or empty_string_regex().fullmatch(type_and_value['Name']):  # This value handled first because `len()` of null value raises an error
                                        items_dict['authors'] = None
                                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("authors", items_dict['authors']))
                                    elif len(type_and_value['Name']) > self.AUTHORS_LENGTH:
                                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("authors", len(type_and_value['Name']))
                                        log.critical(message)
                                        return message
                                    else:
                                        items_dict['authors'] = type_and_value['Name']
                                        include_in_df_dtypes['authors'] = 'string'
                                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("authors", items_dict['authors']))

                        #Subsection: Capture `publication_date` Value
                        elif i_key == "Publication_Date":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(i_value, i_key, "`COUNTERData.resource_name`"))
                            if i_value == "1000-01-01" or i_value == "1753-01-01" or i_value == "1900-01-01":
                                pass  # These dates are common RDBMS/spreadsheet minimum date data type values and are generally placeholders for null values or bad data
                            try:
                                items_dict['publication_date'] = date.fromisoformat(i_value)
                                include_in_df_dtypes['publication_date'] = True
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("publication_date", items_dict['publication_date']))
                            except:
                                pass  # If the key-value pair is present but the value is null or a blank string, the conversion to a datetime data type would return a TypeError

                        #Subsection:  Capture `article_version` Value
                        elif i_key == "Item_Attributes":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(i_value, i_key, "`COUNTERData.article_version`"))
                            pass

                        #Subsection: Capture Standard Identifiers
                        elif i_key == "Item_ID":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(i_value, i_key, "the standard ID fields"))
                            for ID_type, ID_value in i_value.items():

                                #Subsection: Capture `DOI` Value
                                if ID_type == "DOI":
                                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, "`COUNTERData.DOI`"))
                                    pass

                                #Subsection: Capture `proprietary_ID` Value
                                elif self.proprietary_ID_regex.search(ID_type):
                                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, "`COUNTERData.proprietary_ID`"))
                                    if len(ID_value) > self.PROPRIETARY_ID_LENGTH:
                                        message = ConvertJSONDictToDataframe._increase_field_length_logging_statement("proprietary_ID", len(ID_value))
                                        log.critical(message)
                                        return message
                                    else:
                                        items_dict['proprietary_ID'] = ID_value
                                        include_in_df_dtypes['proprietary_ID'] = 'string'
                                        log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("proprietary_ID", items_dict['proprietary_ID']))

                                #Subsection: Capture `ISBN` Value
                                elif ID_type == "ISBN":
                                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, "`COUNTERData.ISBN`"))
                                    pass

                                #Subsection: Capture `print_ISSN` Value
                                elif ID_type == "Print_ISSN":
                                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, "`COUNTERData.print_ISSN`"))
                                    if ISSN_regex().fullmatch(ID_value):
                                        items_dict['print_ISSN'] = ID_value.strip()
                                        include_in_df_dtypes['print_ISSN'] = 'string'
                                    else:
                                        items_dict['print_ISSN'] = str(ID_value)[:5] + "-" + str(ID_value).strip()[-4:]
                                        include_in_df_dtypes['print_ISSN'] = 'string'
                                    log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("print_ISSN", items_dict['print_ISSN']))

                                #Subsection: Capture `online_ISSN` Value
                                elif ID_type == "Online_ISSN":
                                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, "`COUNTERData.online_ISSN`"))
                                    pass

                                #Subsection: Capture `URI` Value
                                elif ID_type == "URI":
                                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ID_value, ID_type, "`COUNTERData.URI`"))
                                    pass

                        else:
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(i_value, i_key, "a placeholder for later unpacking"))
                            items_dict[i_key] = i_value

                    #Section: Iterate Through `Attribute_Performance` Section of IR SUSHI JSON
                    for ap_item in items_dict['Attribute_Performance']:
                        attribute_performance_dict = {k: v for (k, v) in items_dict.items() if k != "Attribute_Performance"}
                        log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_item, "Attribute_Performance", "keys at the top level of the JSON"))
                        for ap_key, ap_value in ap_item.items():

                            #Subsection: Capture `authors` Value
                            if ap_key == "Item_Contributors":  # `Item_Contributors` uses `Name` instead of `Value`
                                log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.authors`"))
                                pass

                            #Subsection: Capture `article_version` Value
                            elif ap_key == "Item_Attributes":
                                log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.article_version`"))
                                pass

                            #Subsection: Capture Standard Identifiers
                            # Null value handling isn't needed because all null values are removed
                            elif ap_key == "Item_ID":  #ToDo: Are standard identifiers in the `Attribute_Performance` section?
                                log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "the standard ID fields"))
                                for ID_type, ID_value in ap_value.items():

                                    #Subsection: Capture `DOI` Value
                                    if ID_type == "DOI":
                                        log.warning("DOI in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                        pass

                                    #Subsection: Capture `proprietary_ID` Value
                                    elif self.proprietary_ID_regex.search(ID_type):
                                        log.warning("Proprietary ID in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                        pass

                                    #Subsection: Capture `ISBN` Value
                                    elif ID_type == "ISBN":
                                        log.warning("ISBN in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                        pass

                                    #Subsection: Capture `print_ISSN` Value
                                    elif ID_type == "Print_ISSN":
                                        log.warning("Print ISSN in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                        pass

                                    #Subsection: Capture `online_ISSN` Value
                                    elif ID_type == "Online_ISSN":
                                        log.warning("Online ISSN in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                        pass

                                    #Subsection: Capture `URI` Value
                                    elif ID_type == "URI":
                                        log.warning("URI in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                        pass

                            #Subsection: Capture `data_type` Value
                            elif ap_key == "Data_Type":
                                log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.data_type`"))
                                attribute_performance_dict['data_type'] = ap_value
                                include_in_df_dtypes['data_type'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("data_type", attribute_performance_dict['data_type']))

                            #Subsection: Capture `YOP` Value
                            elif ap_key == "YOP":
                                log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.YOP`"))
                                try:
                                    attribute_performance_dict['YOP'] = int(ap_value)  # The Int16 dtype doesn't have a constructor, so this value is saved as an int for now and transformed when when the dataframe is created
                                    include_in_df_dtypes['YOP'] = 'Int16'  # `smallint` in database; using the pandas data type here because it allows null values
                                except:
                                    attribute_performance_dict['YOP'] = None  # The dtype conversion that occurs when this becomes a dataframe will change this to pandas' `NA`
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("YOP", attribute_performance_dict['YOP']))

                            #Subsection: Capture `access_type` Value
                            elif ap_key == "Access_Type":
                                log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.access_type`"))
                                attribute_performance_dict['access_type'] = ap_value
                                include_in_df_dtypes['access_type'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("access_type", attribute_performance_dict['access_type']))

                            #Subsection: Capture `access_method` Value
                            elif ap_key == "Access_Method":
                                log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.access_method`"))
                                attribute_performance_dict['access_method'] = ap_value
                                include_in_df_dtypes['access_method'] = 'string'
                                log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("access_method", attribute_performance_dict['access_method']))

                            #Section: Iterate Through `Performance` Section of SUSHI JSON to Create Dataframe Lines
                            elif ap_key == "Performance":
                                for p_key, p_value in ap_value.items():
                                    performance_dict = deepcopy(attribute_performance_dict)
                                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(p_key, p_key, "`COUNTERData.metric_type`"))
                                    performance_dict['metric_type'] = p_key
                                    for usage_date, usage_count in p_value.items():
                                        log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(p_value, p_key, "the `COUNTERData.usage_date` and `COUNTERData.usage_count` fields"))
                                        final_dict = {
                                            **deepcopy(performance_dict),
                                            'usage_date': datetime.strptime(usage_date, '%Y-%m').date(),
                                            'usage_count': usage_count,
                                        }
                                        records_orient_list.append(final_dict)
                                        log.debug(f"Added record {final_dict} to `COUNTERData` relation.")  # Set to logging level debug because when all these logging statements are sent to AWS stdout, the only pytest output visible is the error summary statements

            #Section: Iterate Through `Attribute_Performance` Section of PR/DR/TR SUSHI JSON
            elif report_type == "PR" or report_type == "DR" or report_type == "TR":
                for ap_item in report_items_dict['Attribute_Performance']:
                    attribute_performance_dict = {k: v for (k, v) in report_items_dict.items() if k != "Attribute_Performance"}
                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_item, "Attribute_Performance", "keys at the top level of the JSON"))
                    for ap_key, ap_value in ap_item.items():

                        #Subsection: Capture `authors` Value
                        if ap_key == "Item_Contributors":  # `Item_Contributors` uses `Name` instead of `Value`
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.authors`"))
                            pass

                        #Subsection: Capture Standard Identifiers
                        # Null value handling isn't needed because all null values are removed
                        elif ap_key == "Item_ID":  #ToDo: Are standard identifiers in the `Attribute_Performance` section?
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "the standard ID fields"))
                            for ID_type, ID_value in ap_value.items():

                                #Subsection: Capture `DOI` Value
                                if ID_type == "DOI":
                                    log.warning("DOI in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                    pass

                                #Subsection: Capture `proprietary_ID` Value
                                elif self.proprietary_ID_regex.search(ID_type):
                                    log.warning("Proprietary ID in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                    pass

                                #Subsection: Capture `ISBN` Value
                                elif ID_type == "ISBN":
                                    log.warning("ISBN in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                    pass

                                #Subsection: Capture `print_ISSN` Value
                                elif ID_type == "Print_ISSN":
                                    log.warning("Print ISSN in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                    pass

                                #Subsection: Capture `online_ISSN` Value
                                elif ID_type == "Online_ISSN":
                                    log.warning("Online ISSN in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                    pass

                                #Subsection: Capture `URI` Value
                                elif ID_type == "URI":
                                    log.warning("URI in the `Attribute_Performance` section")  # Replace with capture if ever output to logging
                                    pass

                        #Subsection: Capture `data_type` Value
                        elif ap_key == "Data_Type":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.data_type`"))
                            attribute_performance_dict['data_type'] = ap_value
                            include_in_df_dtypes['data_type'] = 'string'
                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("data_type", attribute_performance_dict['data_type']))

                        #Subsection: Capture `YOP` Value
                        elif ap_key == "YOP":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.YOP`"))
                            try:
                                attribute_performance_dict['YOP'] = int(ap_value)  # The Int16 dtype doesn't have a constructor, so this value is saved as an int for now and transformed when when the dataframe is created
                                include_in_df_dtypes['YOP'] = 'Int16'  # `smallint` in database; using the pandas data type here because it allows null values
                            except:
                                attribute_performance_dict['YOP'] = None  # The dtype conversion that occurs when this becomes a dataframe will change this to pandas' `NA`
                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("YOP", attribute_performance_dict['YOP']))

                        #Subsection: Capture `access_type` Value
                        elif ap_key == "Access_Type":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.access_type`"))
                            attribute_performance_dict['access_type'] = ap_value
                            include_in_df_dtypes['access_type'] = 'string'
                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("access_type", attribute_performance_dict['access_type']))

                        #Subsection: Capture `access_method` Value
                        elif ap_key == "Access_Method":
                            log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(ap_value, ap_key, "`COUNTERData.access_method`"))
                            attribute_performance_dict['access_method'] = ap_value
                            include_in_df_dtypes['access_method'] = 'string'
                            log.debug(ConvertJSONDictToDataframe._extraction_complete_logging_statement("access_method", attribute_performance_dict['access_method']))

                        #Section: Iterate Through `Performance` Section of SUSHI JSON to Create Dataframe Lines
                        elif ap_key == "Performance":
                            for p_key, p_value in ap_value.items():
                                performance_dict = deepcopy(attribute_performance_dict)
                                log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(p_key, p_key, "`COUNTERData.metric_type`"))
                                performance_dict['metric_type'] = p_key
                                for usage_date, usage_count in p_value.items():
                                    log.debug(ConvertJSONDictToDataframe._extraction_start_logging_statement(p_value, p_key, "the `COUNTERData.usage_date` and `COUNTERData.usage_count` fields"))
                                    final_dict = {
                                        **deepcopy(performance_dict),
                                        'usage_date': datetime.strptime(usage_date, '%Y-%m').date(),
                                        'usage_count': usage_count,
                                    }
                                    records_orient_list.append(final_dict)
                                    log.debug(f"Added record {final_dict} to `COUNTERData` relation.")  # Set to logging level debug because when all these logging statements are sent to AWS stdout, the only pytest output visible is the error summary statements

            else:
                message = "The IR expected `Items` key was missing; the JSON cannot be converted into a dataframe."
                log.critical(message)
                return message

        #Section: Create Dataframe
        log.info(f"Unfiltered `include_in_df_dtypes`: {include_in_df_dtypes}")
        include_in_df_dtypes = {k: v for (k, v) in include_in_df_dtypes.items() if v is not False}  # Using `is` for comparison because `1 != False` returns `True` in Python
        log.debug(f"Filtered `include_in_df_dtypes`: {include_in_df_dtypes}")
        df_dtypes = {k: v for (k, v) in include_in_df_dtypes.items() if v is not True}
        df_dtypes['platform'] = 'string'
        df_dtypes['metric_type'] = 'string'
        df_dtypes['usage_count'] = 'int'
        log.info(f"`df_dtypes`: {df_dtypes}")

        log.debug(f"`records_orient_list` before `json.dumps()`  is type {type(records_orient_list)}.")
        records_orient_list = json.dumps(  # `pd.read_json` takes a string, conversion done before method for ease in handling type conversions
            records_orient_list,
            default=ConvertJSONDictToDataframe._serialize_dates,
        )
        if len(records_orient_list) > 1500:
            log.debug(f"`records_orient_list` after `json.dumps()` (type {type(records_orient_list)}) is too long to display.")
        else:
            log.debug(f"`records_orient_list` after `json.dumps()` (type {type(records_orient_list)}):\n{records_orient_list}")
        df = pd.read_json(
            io.StringIO(records_orient_list),  # Originally from https://stackoverflow.com/a/63655099 in `except` block; now only option due to `FutureWarning: Passing literal json to 'read_json' is deprecated and will be removed in a future version. To read from a literal string, wrap it in a 'StringIO' object.`
            orient='records',
            dtype=df_dtypes,  # This only sets numeric data types
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        log.info(f"Dataframe info immediately after dataframe creation:\n{return_string_of_dataframe_info(df)}")

        df = df.astype(df_dtypes)  # This sets the string data types
        log.debug(f"Dataframe dtypes after conversion:\n{return_string_of_dataframe_info(df)}")
        if include_in_df_dtypes.get('publication_date'):  # Meaning the value was changed to `True`
            df['publication_date'] = pd.to_datetime(
                df['publication_date'],
                errors='coerce',  # Changes the null values to the date dtype's null value `NaT`
            )
        if include_in_df_dtypes.get('parent_publication_date'):  # Meaning the value was changed to `True`
            df['parent_publication_date'] = pd.to_datetime(
                df['parent_publication_date'],
                errors='coerce',  # Changes the null values to the date dtype's null value `NaT`
            )
        df['usage_date'] = pd.to_datetime(df['usage_date'])
        df['report_creation_date'] = pd.to_datetime(df['report_creation_date'])#.dt.tz_localize(None)

        log.info(f"Dataframe info:\n{return_string_of_dataframe_info(df)}")
        return df
    

    @staticmethod
    def _serialize_dates(dates):
        """This method allows the `json.dumps()` method to serialize (convert) `datetime.datetime` and `datetime.date` attributes into strings.

        This method and its use in are adapted from https://stackoverflow.com/a/22238613.

        Args:
            dates (datetime.datetime or datetime.date): A date or timestamp with a data type from Python's datetime library

        Returns:
            str: the date or timestamp in ISO format
        """
        if isinstance(dates,(date, datetime)):
            return dates.isoformat()
        else:
            raise TypeError  # So any unexpected non-serializable data types raise a type error
    

    @staticmethod
    def _extraction_start_logging_statement(value, key, field):
        """This method creates the logging statement at the beginning of an attribute value extraction.

        Args:
            value (str): the value being extracted
            key (str): the dictionary key of the value being extracted
            field (str): the `nolcat.methods.COUNTERData` field the value is being assigned to

        Returns:
            str: the logging statement
        """
        return f"Preparing to move '{value}' from the key '{key}' to {field}."
    

    @staticmethod
    def _extraction_complete_logging_statement(field, value):
        """This method creates the logging statement indicating a successful attribute value extraction.

        Args:
            field (str): the `nolcat.methods.COUNTERData` field the value is assigned to
            value (str): the extracted value

        Returns:
            str: the logging statement
        """
        return f"Added `COUNTERData.{field}` value '{value}' to the row dictionary."
    

    @staticmethod
    def _increase_field_length_logging_statement(field, length):
        """This method creates the logging statement indicating a field length needs to be increased.

        Args:
            field (str): the `nolcat.methods.COUNTERData` field to adjust
            length (int): the length of the field

        Returns:
            str: the logging statement
        """
        return f"Increase the `COUNTERData.{field}` max field length to {ceil(length * 1.1)}."