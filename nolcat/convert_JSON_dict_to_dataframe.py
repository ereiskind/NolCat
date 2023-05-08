import logging
import re
import datetime
from dateutil import parser
import json
from copy import deepcopy
import pandas as pd

from .app import return_string_of_dataframe_info


logging.basicConfig(level=logging.INFO, format="ConvertJSONDictToDataframe - - [%(asctime)s] %(message)s")


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
        create_dataframe: This method transforms the data from the dictionary derived from the SUSHI call response JSON into a single dataframe ready to be loaded into the `COUNTERData` relation.
        _serialize_dates: This method allows the `json.dumps()` method to serialize (convert) `datetime.datetime` and `datetime.date` attributes into strings.
    """
    # These field length constants allow the class to check that data in varchar fields without COUNTER-defined fixed vocabularies can be successfully uploaded to the `COUNTERData` relation; the constants are set here as class variables instead of in `models.py` to avoid a circular import
    RESOURCE_NAME_LENGTH = 2000
    PUBLISHER_LENGTH = 225
    PUBLISHER_ID_LENGTH = 50
    PLATFORM_LENGTH = 75
    AUTHORS_LENGTH = 1000
    DOI_LENGTH = 75
    PROPRIETARY_ID_LENGTH = 100
    URI_LENGTH = 250

    def __init__(self, SUSHI_JSON_dictionary):
        """The constructor method for `ConvertJSONDictToDataframe`, which instantiates the dictionary object.

        This constructor is not meant to be used alone; all class instantiations should have a `create_dataframe()` method call appended to it.

        Args:
            SUSHI_JSON_dictionary (dict): The dictionary created by converting the JSON returned by the SUSHI API call into Python data types
        """
        self.SUSHI_JSON_dictionary = SUSHI_JSON_dictionary
    

    def create_dataframe(self):
        """This method transforms the data from the dictionary derived from the SUSHI call response JSON into a single dataframe ready to be loaded into the `COUNTERData` relation.

        This method prepares the dictionaries containing all the data from the SUSHI API responses for upload into the database. The `statistics_source_ID` and `report_type` are added after the dataframe is returned to the `StatisticsSources._harvest_R5_SUSHI()` method: the former because that information is proprietary to the NoLCAT instance; the latter because adding it there is less computing-intensive.

        Returns:
            dataframe: COUNTER data ready to be loaded into the `COUNTERData` relation
        """
        logging.info("Starting `ConvertJSONDictToDataframe.create_dataframe()`")
        records_orient_list = []
        report_header_creation_date = parser.isoparse(self.SUSHI_JSON_dictionary['Report_Header']['Created']).date()  # Saving as datetime.date data type removes the time data
        logging.debug(f"Report creation date is {report_header_creation_date} of type {type(report_header_creation_date)}")

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
            logging.debug(f"Starting iteration for new JSON record {record}")
            record_dict = {"report_creation_date": report_header_creation_date}  # This resets the contents of `record_dict`, including removing any keys that might not get overwritten because they aren't included in the next iteration
            for key, value in record.items():

                #Subsection: Capture `resource_name` Value
                if key == "Database" or key == "Title" or key == "Item":
                    if value is None:  # This value handled first because `len()` of null value raises an error
                        record_dict['resource_name'] = value
                        logging.debug(f"Added `COUNTERData.resource_name` value {record_dict['resource_name']} to `record_dict`.")
                    elif len(value) > self.RESOURCE_NAME_LENGTH:
                        logging.error(f"Increase the `COUNTERData.resource_name` max field length to {int(len(value) + (len(value) * 0.1))}.")
                        return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                    else:
                        record_dict['resource_name'] = value
                        include_in_df_dtypes['resource_name'] = 'string'
                        logging.debug(f"Added `COUNTERData.resource_name` value {record_dict['resource_name']} to `record_dict`.")
                
                #Subsection: Capture `publisher` Value
                elif key == "Publisher":
                    if value is None:  # This value handled first because `len()` of null value raises an error
                        record_dict['publisher'] = value
                        logging.debug(f"Added `COUNTERData.publisher` value {record_dict['publisher']} to `record_dict`.")
                    elif len(value) > self.PUBLISHER_LENGTH:
                        logging.error(f"Increase the `COUNTERData.publisher` max field length to {int(len(value) + (len(value) * 0.1))}.")
                        return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                    else:
                        record_dict['publisher'] = value
                        include_in_df_dtypes['publisher'] = 'string'
                        logging.debug(f"Added `COUNTERData.publisher` value {record_dict['publisher']} to `record_dict`.")
                
                #Subsection: Capture `publisher_ID` Value
                elif key == "Publisher_ID":
                    if value is None:  # This value handled first because `len()` of null value raises an error
                        record_dict['publisher_ID'] = value
                        logging.debug(f"Added `COUNTERData.publisher_ID` value {record_dict['publisher_ID']} to `record_dict`.")
                    elif len(value) == 1:
                        if len(value[0]['Value']) > self.PUBLISHER_ID_LENGTH:
                            logging.error(f"Increase the `COUNTERData.publisher_ID` max field length to {int(len(value[0]['Value']) + (len(value[0]['Value']) * 0.1))}.")
                            return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                        else:
                            record_dict['publisher_ID'] = value[0]['Value']
                            include_in_df_dtypes['publisher_ID'] = 'string'
                            logging.debug(f"Added `COUNTERData.publisher_ID` value {record_dict['publisher_ID']} to `record_dict`.")
                    else:
                        for type_and_value in value:
                            if re.match(r'[Pp]roprietary(_ID)?', string=type_and_value['Type']):
                                if len(type_and_value['Value']) > self.PUBLISHER_ID_LENGTH:
                                    logging.error(f"Increase the `COUNTERData.publisher_ID` max field length to {int(len(type_and_value['Value']) + (len(type_and_value['Value']) * 0.1))}.")
                                    return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                                else:
                                    record_dict['publisher_ID'] = type_and_value['Value']
                                    include_in_df_dtypes['publisher_ID'] = 'string'
                                    logging.debug(f"Added `COUNTERData.publisher_ID` value {record_dict['publisher_ID']} to `record_dict`.")
                            else:
                                continue  # The `for type_and_value in value` loop
                
                #Subsection: Capture `platform` Value
                elif key == "Platform":
                    if value is None:  # This value handled first because `len()` of null value raises an error
                        record_dict['platform'] = value
                        logging.debug(f"Added `COUNTERData.platform` value {record_dict['platform']} to `record_dict`.")
                    elif len(value) > self.PLATFORM_LENGTH:
                        logging.error(f"Increase the `COUNTERData.platform` max field length to {int(len(value) + (len(value) * 0.1))}.")
                        return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                    else:
                        record_dict['platform'] = value
                        logging.debug(f"Added `COUNTERData.platform` value {record_dict['platform']} to `record_dict`.")
                
                #Subsection: Capture `authors` Value
                elif key == "Item_Contributors":  # `Item_Contributors` uses `Name` instead of `Value`
                    for type_and_value in value:
                        if re.match(r'[Aa]uthor', string=type_and_value['Type']):
                            if record_dict.get('authors'):  # If the author name value is null, this will never be true
                                if record_dict['authors'].endswith(" et al."):
                                    continue  # The `for type_and_value in value` loop
                                elif len(record_dict['authors']) + len(type_and_value['Name']) + 8 > self.AUTHORS_LENGTH:
                                    record_dict['authors'] = record_dict['authors'] + " et al."
                                    logging.debug(f"Updated `COUNTERData.authors` value to {record_dict['parent_authors']} in `record_dict`.")
                                else:
                                    record_dict['authors'] = record_dict['authors'] + "; " + type_and_value['Name']
                                    logging.debug(f"Added `COUNTERData.authors` value {record_dict['authors']} to `record_dict`.")
                            
                            else:
                                if type_and_value['Name'] is None:  # This value handled first because `len()` of null value raises an error
                                    record_dict['authors'] = type_and_value['Name']
                                    logging.debug(f"Added `COUNTERData.authors` value {record_dict['authors']} to `record_dict`.")
                                elif len(type_and_value['Name']) > self.AUTHORS_LENGTH:
                                    logging.error(f"Increase the `COUNTERData.authors` max field length to {int(len(type_and_value['Name']) + (len(type_and_value['Name']) * 0.1))}.")
                                    return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                                else:
                                    record_dict['authors'] = type_and_value['Name']
                                    include_in_df_dtypes['authors'] = 'string'
                                    logging.debug(f"Added `COUNTERData.authors` value {record_dict['authors']} to `record_dict`.")
                
                #Subsection: Capture `publication_date` Value
                elif key == "Item_Dates":
                    for type_and_value in value:
                        if type_and_value['Value'] == "1000-01-01" or type_and_value['Value'] == "1753-01-01" or type_and_value['Value'] == "1900-01-01":
                            continue  # The `for type_and_value in value` loop; these dates are common RDBMS/spreadsheet minimum date data type values and are generally placeholders for null values or bad data
                        if type_and_value['Type'] == "Publication_Date":  # Unlikely to be more than one; if there is, the field's date/datetime64 data type prevent duplicates from being preserved
                            try:
                                record_dict['publication_date'] = datetime.date.fromisoformat(type_and_value['Value'])
                                include_in_df_dtypes['publication_date'] = True
                                logging.debug(f"Added `COUNTERData.publication_date` value {record_dict['publication_date']} to `record_dict`.")
                            except:  # In case `type_and_value['Value']` is null, which would cause the conversion to a datetime data type to return a TypeError
                                continue  # The `for type_and_value in value` loop
                
                #Subsection: Capture `article_version` Value
                elif key == "Item_Attributes":
                    for type_and_value in value:
                        if type_and_value['Type'] == "Article_Version":  # Very unlikely to be more than one
                            record_dict['article_version'] = type_and_value['Value']
                            include_in_df_dtypes['article_version'] = 'string'
                            logging.debug(f"Added `COUNTERData.article_version` value {record_dict['article_version']} to `record_dict`.")
                
                #Subsection: Capture Standard Identifiers
                # Null value handling isn't needed because all null values are removed
                elif key == "Item_ID":
                    for type_and_value in value:
                        
                        #Subsection: Capture `DOI` Value
                        if type_and_value['Type'] == "DOI":
                            if len(type_and_value['Value']) > self.DOI_LENGTH:
                                logging.error(f"Increase the `COUNTERData.DOI` max field length to {int(len(type_and_value['Value']) + (len(type_and_value['Value']) * 0.1))}.")
                                return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                            else:
                                record_dict['DOI'] = type_and_value['Value']
                                include_in_df_dtypes['DOI'] = 'string'
                                logging.debug(f"Added `COUNTERData.DOI` value {record_dict['DOI']} to `record_dict`.")
                        
                        #Subsection: Capture `proprietary_ID` Value
                        elif re.match(r'[Pp]roprietary(_ID)?', string=type_and_value['Type']):
                            if len(type_and_value['Value']) > self.PROPRIETARY_ID_LENGTH:
                                logging.error(f"Increase the `COUNTERData.proprietary_ID` max field length to {int(len(type_and_value['Value']) + (len(type_and_value['Value']) * 0.1))}.")
                                return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                            else:
                                record_dict['proprietary_ID'] = type_and_value['Value']
                                include_in_df_dtypes['proprietary_ID'] = 'string'
                                logging.debug(f"Added `COUNTERData.proprietary_ID` value {record_dict['proprietary_ID']} to `record_dict`.")
                        
                        #Subsection: Capture `ISBN` Value
                        elif type_and_value['Type'] == "ISBN":
                            record_dict['ISBN'] = str(type_and_value['Value'])
                            include_in_df_dtypes['ISBN'] = 'string'
                            logging.debug(f"Added `COUNTERData.ISBN` value {record_dict['ISBN']} to `record_dict`.")
                        
                        #subsection: Capture `print_ISSN` Value
                        elif type_and_value['Type'] == "Print_ISSN":
                            if re.match(r'\d{4}\-\d{3}[\dxX]\s*', string=type_and_value['Value']):
                                record_dict['print_ISSN'] = type_and_value['Value'].strip()
                                include_in_df_dtypes['print_ISSN'] = 'string'
                                logging.debug(f"Added `COUNTERData.print_ISSN` value {record_dict['print_ISSN']} to `record_dict`.")
                            else:
                                record_dict['print_ISSN'] = str(type_and_value['Value'])[:5] + "-" + str(type_and_value['Value']).strip()[-4:]
                                include_in_df_dtypes['print_ISSN'] = 'string'
                                logging.debug(f"Added `COUNTERData.print_ISSN` value {record_dict['print_ISSN']} to `record_dict`.")
                        
                        #Subsection: Capture `online_ISSN` Value
                        elif type_and_value['Type'] == "Online_ISSN":
                            if re.match(r'\d{4}\-\d{3}[\dxX]\s*', string=type_and_value['Value']):
                                record_dict['online_ISSN'] = type_and_value['Value'].strip()
                                include_in_df_dtypes['online_ISSN'] = 'string'
                                logging.debug(f"Added `COUNTERData.online_ISSN` value {record_dict['online_ISSN']} to `record_dict`.")
                            else:
                                record_dict['online_ISSN'] = str(type_and_value['Value'])[:5] + "-" + str(type_and_value['Value']).strip()[-4:]
                                include_in_df_dtypes['online_ISSN'] = 'string'
                                logging.debug(f"Added `COUNTERData.online_ISSN` value {record_dict['online_ISSN']} to `record_dict`.")
                        
                        #Subsection: Capture `URI` Value
                        elif type_and_value['Type'] == "URI":
                            if len(type_and_value['Value']) > self.URI_LENGTH:
                                logging.error(f"Increase the `COUNTERData.URI` max field length to {int(len(type_and_value['Value']) + (len(type_and_value['Value']) * 0.1))}.")
                                return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                            else:
                                record_dict['URI'] = type_and_value['Value']
                                include_in_df_dtypes['URI'] = 'string'
                                logging.debug(f"Added `COUNTERData.URI` value {record_dict['URI']} to `record_dict`.")
                        else:
                            continue  # The `for type_and_value in value` loop
                
                #Subsection: Capture `data_type` Value
                elif key == "Data_Type":
                    record_dict['data_type'] = value
                    include_in_df_dtypes['data_type'] = 'string'
                    logging.debug(f"Added `COUNTERData.data_type` value {record_dict['data_type']} to `record_dict`.")
                
                #Subsection: Capture `section_Type` Value
                elif key == "Section_Type":
                    record_dict['section_type'] = value
                    include_in_df_dtypes['section_type'] = 'string'
                    logging.debug(f"Added `COUNTERData.section_type` value {record_dict['section_type']} to `record_dict`.")

                #Subsection: Capture `YOP` Value
                elif key == "YOP":
                    try:
                        record_dict['YOP'] = int(value)  # The Int64 dtype doesn't have a constructor, so this value is saved as an int for now and transformed when when the dataframe is created
                        include_in_df_dtypes['YOP'] = 'Int64'  # `smallint` in database; using the pandas data type here because it allows null values
                    except:
                        record_dict['YOP'] = None  # The dtype conversion that occurs when this becomes a dataframe will change this to pandas' `NA`
                    logging.debug(f"Added `COUNTERData.YOP` value {record_dict['YOP']} to `record_dict`.")
                
                #Subsection: Capture `access_type` Value
                elif key == "Access_Type":
                    record_dict['access_type'] = value
                    include_in_df_dtypes['access_type'] = 'string'
                    logging.debug(f"Added `COUNTERData.access_type` value {record_dict['access_type']} to `record_dict`.")
                
                #Subsection: Capture `access_method` Value
                elif key == "Access_Method":
                    record_dict['access_method'] = value
                    include_in_df_dtypes['access_method'] = 'string'
                    logging.debug(f"Added `COUNTERData.access_method` value {record_dict['access_method']} to `record_dict`.")
                
                #Subsection: Capture Parent Resource Metadata
                # Null value handling isn't needed because all null values are removed
                elif key == "Item_Parent":
                    if repr(type(value)) == "<class 'list'>" and len(value) == 1:  # The `Item_Parent` value should be a dict, but sometimes that dict is within a one-item list; this removes the outer list
                        value = value[0]
                    for key_for_parent, value_for_parent in value.items():

                        #Subsection: Capture `parent_title` Value
                        if key_for_parent == "Item_Name":
                            if len(value_for_parent) > self.RESOURCE_NAME_LENGTH:
                                logging.error(f"Increase the `COUNTERData.parent_title` max field length to {int(len(value_for_parent) + (len(value_for_parent) * 0.1))}.")
                                return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                            else:
                                record_dict['parent_title'] = value_for_parent
                                include_in_df_dtypes['parent_title'] = 'string'
                                logging.debug(f"Added `COUNTERData.parent_title` value {record_dict['parent_title']} to `record_dict`.")
                        
                        #Subsection: Capture `parent_authors` Value
                        elif key_for_parent == "Item_Contributors":  # `Item_Contributors` uses `Name` instead of `Value`
                            for type_and_value in value_for_parent:
                                if re.match(r'[Aa]uthor', string=type_and_value['Type']):
                                    if record_dict.get('parent_authors'):
                                        if record_dict['parent_authors'].endswith(" et al."):
                                            continue  # The `for type_and_value in value_for_parent` loop
                                        elif len(record_dict['parent_authors']) + len(type_and_value['Name']) + 8 > self.AUTHORS_LENGTH:
                                            record_dict['parent_authors'] = record_dict['parent_authors'] + " et al."
                                            logging.debug(f"Updated `COUNTERData.parent_authors` value to {record_dict['parent_authors']} in `record_dict`.")
                                        else:
                                            record_dict['parent_authors'] = record_dict['parent_authors'] + "; " + type_and_value['Name']
                                            logging.debug(f"Updated `COUNTERData.parent_authors` value to {record_dict['parent_authors']} in `record_dict`.")
                                    else:
                                        if len(type_and_value['Name']) > self.AUTHORS_LENGTH:
                                            logging.error(f"Increase the `COUNTERData.authors` max field length to {int(len(type_and_value['Name']) + (len(type_and_value['Name']) * 0.1))}.")
                                            return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                                        else:
                                            record_dict['parent_authors'] = type_and_value['Name']
                                            include_in_df_dtypes['parent_authors'] = 'string'
                                            logging.debug(f"Added `COUNTERData.parent_authors` value {record_dict['parent_authors']} to `record_dict`.")
                        
                        #Subsection: Capture `parent_publication_date` Value
                        elif key_for_parent == "Item_Dates":
                            for type_and_value in value_for_parent:
                                if type_and_value['Value'] == "1000-01-01" or type_and_value['Value'] == "1753-01-01" or type_and_value['Value'] == "1900-01-01":
                                    continue  # The `for type_and_value in value` loop; these dates are common RDBMS/spreadsheet minimum date data type values and are generally placeholders for null values or bad data
                                if type_and_value['Type'] == "Publication_Date":  # Unlikely to be more than one; if there is, the field's date/datetime64 data type prevent duplicates from being preserved
                                    record_dict['parent_publication_date'] = datetime.date.fromisoformat(type_and_value['Value'])
                                    include_in_df_dtypes['parent_publication_date'] = True
                                    logging.debug(f"Added `COUNTERData.parent_publication_date` value {record_dict['parent_publication_date']} to `record_dict`.")
                        
                        #Subsection: Capture `parent_article_version` Value
                        elif key_for_parent == "Item_Attributes":
                            for type_and_value in value_for_parent:
                                if type_and_value['Type'] == "Article_Version":  # Very unlikely to be more than one
                                    record_dict['parent_article_version'] = type_and_value['Value']
                                    include_in_df_dtypes['parent_article_version'] = 'string'
                                    logging.debug(f"Added `COUNTERData.parent_article_version` value {record_dict['parent_article_version']} to `record_dict`.")

                        #Subsection: Capture `parent_data_type` Value
                        elif key_for_parent == "Data_Type":
                            record_dict['parent_data_type'] = value_for_parent
                            include_in_df_dtypes['parent_data_type'] = 'string'
                            logging.debug(f"Added `COUNTERData.parent_data_type` value {record_dict['parent_data_type']} to `record_dict`.")
                        
                        elif key_for_parent == "Item_ID":
                            for type_and_value in value_for_parent:
                                
                                #Subsection: Capture `parent_DOI` Value
                                if type_and_value['Type'] == "DOI":
                                    if len(type_and_value['Value']) > self.DOI_LENGTH:
                                        logging.error(f"Increase the `COUNTERData.parent_DOI` max field length to {int(len(type_and_value['Value']) + (len(type_and_value['Value']) * 0.1))}.")
                                        return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                                    else:
                                        record_dict['parent_DOI'] = type_and_value['Value']
                                        include_in_df_dtypes['parent_DOI'] = 'string'
                                        logging.debug(f"Added `COUNTERData.parent_DOI` value {record_dict['parent_DOI']} to `record_dict`.")

                                #Subsection: Capture `parent_proprietary_ID` Value
                                elif re.match(r'[Pp]roprietary(_ID)?', string=type_and_value['Type']):
                                    if len(type_and_value['Value']) > self.PROPRIETARY_ID_LENGTH:
                                        logging.error(f"Increase the `COUNTERData.parent_proprietary_ID` max field length to {int(len(type_and_value['Value']) + (len(type_and_value['Value']) * 0.1))}.")
                                        return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                                    else:
                                        record_dict['parent_proprietary_ID'] = type_and_value['Value']
                                        include_in_df_dtypes['parent_proprietary_ID'] = 'string'
                                        logging.debug(f"Added `COUNTERData.parent_proprietary_ID` value {record_dict['parent_proprietary_ID']} to `record_dict`.")

                                #Subsection: Capture `parent_ISBN` Value
                                elif type_and_value['Type'] == "ISBN":
                                    record_dict['parent_ISBN'] = str(type_and_value['Value'])
                                    include_in_df_dtypes['parent_ISBN'] = 'string'
                                    logging.debug(f"Added `COUNTERData.parent_ISBN` value {record_dict['parent_ISBN']} to `record_dict`.")

                                #Subsection: Capture `parent_print_ISSN` Value
                                elif type_and_value['Type'] == "Print_ISSN":
                                    if re.match(r'\d{4}\-\d{3}[\dxX]\s*', string=type_and_value['Value']):
                                        record_dict['parent_print_ISSN'] = type_and_value['Value'].strip()
                                        include_in_df_dtypes['parent_print_ISSN'] = 'string'
                                        logging.debug(f"Added `COUNTERData.parent_print_ISSN` value {record_dict['parent_print_ISSN']} to `record_dict`.")
                                    else:
                                        record_dict['parent_print_ISSN'] = str(type_and_value['Value'])[:5] + "-" + str(type_and_value['Value']).strip()[-4:]
                                        include_in_df_dtypes['parent_print_ISSN'] = 'string'
                                        logging.debug(f"Added `COUNTERData.parent_print_ISSN` value {record_dict['parent_print_ISSN']} to `record_dict`.")

                                #Subsection: Capture `parent_online_ISSN` Value
                                elif type_and_value['Type'] == "Online_ISSN":
                                    if re.match(r'\d{4}\-\d{3}[\dxX]\s*', string=type_and_value['Value']):
                                        record_dict['parent_online_ISSN'] = type_and_value['Value'].strip()
                                        include_in_df_dtypes['parent_online_ISSN'] = 'string'
                                        logging.debug(f"Added `COUNTERData.parent_online_ISSN` value {record_dict['parent_online_ISSN']} to `record_dict`.")
                                    else:
                                        record_dict['parent_online_ISSN'] = str(type_and_value['Value'])[:5] + "-" + str(type_and_value['Value']).strip()[-4:]
                                        include_in_df_dtypes['parent_online_ISSN'] = 'string'
                                        logging.debug(f"Added `COUNTERData.parent_online_ISSN` value {record_dict['parent_online_ISSN']} to `record_dict`.")

                                #Subsection: Capture `parent_URI` Value
                                elif type_and_value['Type'] == "URI":
                                    if len(type_and_value['Value']) > self.URI_LENGTH:
                                        logging.error(f"Increase the `COUNTERData.parent_URI` max field length to {int(len(type_and_value['Value']) + (len(type_and_value['Value']) * 0.1))}.")
                                        return pd.DataFrame()  # Returning an empty dataframe tells `StatisticsSources._harvest_R5_SUSHI()` that this report can't be loaded
                                    else:
                                        record_dict['parent_URI'] = type_and_value['Value']
                                        include_in_df_dtypes['parent_URI'] = 'string'
                                        logging.debug(f"Added `COUNTERData.parent_URI` value {record_dict['parent_URI']} to `record_dict`.")

                        else:
                            continue  # The `for key_for_parent, value_for_parent in value.items()` loop

                elif key == "Performance":
                    record_dict['temp'] = value

                else:
                    logging.warning(f"The unexpected key `{key}` was found in the JSON response to a SUSHI API call.")
                    pass
            
            #Section: Create Records by Iterating Through `Performance` Section of SUSHI JSON
            performance = record_dict.pop('temp')
            for period_grouping in performance:
                record_dict['usage_date'] = datetime.date.fromisoformat(period_grouping['Period']['Begin_Date'])
                for instance in period_grouping['Instance']:
                    record_dict['metric_type'] = instance['Metric_Type']
                    record_dict['usage_count'] = instance['Count']
                    records_orient_list.append(deepcopy(record_dict))  # Appending `record_dict` directly adds a reference to that variable, which changes with each iteration of the loop, meaning all the records for a given set of metadata have the `usage_date`, `metric_type`, and `usage_count` values of `record_dict` during the final iteration
                    logging.debug(f"Added record {record_dict} to `COUNTERData` relation.")  # Set to logging level debug because when all these logging statements are sent to AWS stdout, the only pytest output visible is the error summary statements

        #Section: Create Dataframe
        logging.info(f"Unfiltered `include_in_df_dtypes`: {include_in_df_dtypes}")
        include_in_df_dtypes = {k: v for (k, v) in include_in_df_dtypes.items() if v is not False}  # Using `is` for comparison because `1 != False` returns `True` in Python
        logging.debug(f"Filtered `include_in_df_dtypes`: {include_in_df_dtypes}")
        df_dtypes = {k: v for (k, v) in include_in_df_dtypes.items() if v is not True}
        df_dtypes['platform'] = 'string'
        df_dtypes['metric_type'] = 'string'
        df_dtypes['usage_count'] = 'int'
        logging.info(f"`df_dtypes`: {df_dtypes}")

        records_orient_list = json.dumps(records_orient_list, default=ConvertJSONDictToDataframe._serialize_dates)  # `pd.read_json` takes a string, conversion done before method for ease in handling type conversions
        logging.debug(f"JSON as a string:\n{records_orient_list}")
        df = pd.read_json(
            records_orient_list,
            orient='records',
            dtype=df_dtypes,  # This only sets numeric data types
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        logging.info(f"Dataframe info immediately after dataframe creation:\n{return_string_of_dataframe_info(df)}")

        df = df.astype(df_dtypes)  # This sets the string data types
        logging.debug(f"Dataframe info after `astype`:\n{return_string_of_dataframe_info(df)}")
        if include_in_df_dtypes.get('publication_date'):  # Meaning the value was changed to `True`
            df['publication_date'] = pd.to_datetime(
                df['publication_date'],
                errors='coerce',  # Changes the null values to the date dtype's null value `NaT`
                infer_datetime_format=True,
            )
        if include_in_df_dtypes.get('parent_publication_date'):  # Meaning the value was changed to `True`
            df['parent_publication_date'] = pd.to_datetime(
                df['parent_publication_date'],
                errors='coerce',  # Changes the null values to the date dtype's null value `NaT`
                infer_datetime_format=True,
            )
        df['usage_date'] = pd.to_datetime(df['usage_date'])
        df['report_creation_date'] = pd.to_datetime(df['report_creation_date'])#.dt.tz_localize(None)

        logging.info(f"Dataframe info:\n{return_string_of_dataframe_info(df)}\n")
        return df
    

    def _serialize_dates(dates):
        """This method allows the `json.dumps()` method to serialize (convert) `datetime.datetime` and `datetime.date` attributes into strings.

        This method and its use in are adapted from https://stackoverflow.com/a/22238613.

        Args:
            dates (datetime.datetime or datetime.date): A date or timestamp with a data type from Python's datetime library

        Returns:
            str: the date or timestamp in ISO format
        """
        if isinstance(dates,(datetime.date, datetime.datetime)):
            return dates.isoformat()
        else:
            raise TypeError  # So any unexpected non-serializable data types raise a type error