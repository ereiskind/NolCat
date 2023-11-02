"""The repo features a wide variety of logging statements and log-like output statements. Many of these are consistent within a function or module, but others are standardized with a specific logging level and structure throughout the entire repository; to avoid repetition, such statements are established as functions here. All logging statements and log-like output statements are full sentences ending in periods.
"""

from pathlib import Path


#Section: Simple Helper Functions
# These are helper functions that don't work as well in `nolcat.app` for various reasons

def file_extensions_and_mimetypes():
    """A dictionary of the file extensions for the types of files that can be downloaded to S3 via NoLCAT and their mimetypes.
    
    This helper function is called in `create_app()` and thus must be before that function.
    """
    return {
        ".xlsx": "application/vnd.ms-excel",
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
        ".pdf": "application/pdf",
        ".docx": "application/msword",
        ".pptx": "application/vnd.ms-powerpoint",
        ".txt": "text/plain",
        ".jpeg": "image/jpeg",
        ".jpg":"image/jpeg",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".json": "application/json",
        ".html": "text/html",
        ".htm": "text/html",
        ".xml": "text/xml",
        ".zip": "application/zip",
    }


def format_list_for_stdout(stdout_list):
    """Changes a list into a string which places each item of the list on its own line.

    Using the list comprehension allows the function to accept generators, which are transformed into lists by the comprehension, and to handle both lists and generators with individual items that aren't strings by type juggling.

    Args:
        stdout_list (list or generator): a list for pretty printing to stdout
    
    Returns:
        str: the list contents with a line break between each item
    """
    return '\n'.join([str(file_path) for file_path in stdout_list])


#Section: General Statements
#Subsection: Logging/Output Statements
def initialize_relation_class_object_statement(relation_class_name, object_value):
    """This statement shows the value of a relation class object initialized using the values returned from a query.

    Args:
        relation_class_name (str): the name of the relation class
        object_value (nolcat.models): a relation class object

    Returns:
        str: the statement for outputting the arguments to logging
    """
    return f"The following {relation_class_name} object was initialized based on the query results:\n{object_value}"


def fixture_variable_value_declaration_statement(variable_name, variable_value):
    """This statement adds the value of any arguments used in fixture functions to the logging output for troubleshooting purposes.

    Args:
        variable_name (str): the name of the argument/variable
        variable_value (object): the argument/variable value
    
    Returns:
        str: the statement for outputting the arguments to logging
    """
    if isinstance(variable_value, Path):
        return f"The `{variable_name}` is {variable_value.resolve()}."
    else:
        return f"The `{variable_name}` is {variable_value}."


#Subsection: Error Statements
def unable_to_convert_SUSHI_data_to_dataframe_statement(error_message, report_type=None, statistics_source_name=None):
    """This statement indicates that the provided COUNTER data couldn't be converted into a dataframe.

    Args:
        error_message (str): the error message returned by the attempt to convert the COUNTER data to a dataframe
        report_type (str, optional): the type of report for a SUSHI call; default is `None`
        statistics_source_name (str, optional): the name of the statistics source for a SUSHI call; default is `None`

    Returns:
        str: the statement for outputting the arguments to logging
    """
    if report_type and statistics_source_name:
        return f"Changing the JSON-like dictionary of {report_type} for {statistics_source_name} into a dataframe raised the error {error_message}."
    else:
        return f"Changing the uploaded COUNTER data workbooks into a dataframe raised the error {error_message}."


def unable_to_get_updated_primary_key_values_statement(relation, error):
    """This statement prepares the error raised by `nolcat.app.first_new_PK_value()` for the logging output.

    Args:
        relation (str): the relation name
        error (Exception): the Python Exception raised by `nolcat.app.first_new_PK_value()`
    
    Returns:
        str: the statement for outputting the arguments to logging
    """
    return f"Running the function `first_new_PK_value()` for the relation `{relation}` raised the error {error}."


def Flask_error_statement(error_statement):
    """This statement provides details on why the form couldn't be successfully submitted.

    Args:
        error_statement (dict): the error(s) returned by the form submission

    Returns:
        str: the statement for outputting the arguments to logging
    """
    formatted_dict = '\n'.join([f"{k}: {v}" for k, v in error_statement.items()])
    return f"The form submission failed because of the following error(s):\n{formatted_dict}"


#Section: Files, File Organization, and File I/O
#Subsection: Logging/Output Statements
def file_IO_statement(name_of_file, origin_location, destination_location, upload=True):
    """This statement prepares the name of a file to be subject to an I/O process, plus its origin and destination, for the logging output.

    Args:
        name_of_file (str): the name the file will have after the I/O process
        origin_location (str or Path): the original file location with description
        destination_location (str or Path): the new file location with description
        upload (bool, optional): if the I/O operation is an upload (versus a download); default is `True`
    
    Returns:
        str: the statement for outputting the arguments to logging
    """
    if upload:
        return f"About to upload file '{name_of_file}' from {origin_location} to {destination_location}."
    else:
        return f"About to download file '{name_of_file}' from {origin_location} to {destination_location}."


def list_folder_contents_statement(file_path, alone=True):
    """This statement lists the contents of a folder for the logging output.

    Information about the logging statement's relative location in a function can be added at the very beginning of the statement.

    Args:
        file_path (pathlib.Path): the folder whose contents are being listed
        alone (bool, optional): indicates if any of the aforementioned information about the statement's location is included; default is `True`
    
    Returns:
        str: the statement for outputting the arguments to logging
    """
    main_value = f"he files in the folder {file_path.resolve()}\n{format_list_for_stdout(file_path.iterdir())}"
    if alone:
        return "T" + main_value
    else:
        return " t" + main_value


def check_if_folder_exists_statement(file_path, alone=True):
    """This statement indicates if there's a file at the given file path for the logging output.

   Information about the logging statement's relative location in a function can be added at the very beginning of the statement.

    Args:
        file_path (pathlib.Path): the path to the file being checked
        alone (bool, optional): indicates if any of the aforementioned information about the statement's location is included; default is `True`

    Returns:
        str: the statement for outputting the arguments to logging
    """
    main_value = f"here's a file at {file_path.resolve()}: {file_path.is_file()}"
    if alone:
        return "T" + main_value
    else:
        return " t" + main_value


#Subsection: Error Statements
def failed_upload_to_S3_statement(file_name, error_message):
    """This statement indicates that a call to `nolcat.app.upload_file_to_S3_bucket()` returned an error, meaning the file that should've been uploaded isn't being saved.

    Args:
        file_name (str): the name of the file that wasn't uploaded to S3
        error_message (str): the return statement indicating the failure of `nolcat.app.upload_file_to_S3_bucket()`
    
    Returns:
        str: the statement for outputting the arguments to logging
    """
    return f"Uploading the file {file_name} to S3 failed because {error_message[0].lower()}{error_message[1:]} NoLCAT HAS NOT SAVED THIS DATA IN ANY WAY!"


def unable_to_delete_test_file_in_S3_statement(file_name, error_message):
    """This statement indicates that a file uploaded to a S3 bucket as part of a test function couldn't be removed from the bucket.

    Args:
        file_name (str): the final part of the name of the file in S3
        error_message (str): the AWS error message returned by the attempt to delete the file

    Returns:
        str: the statement for outputting the arguments to logging
    """
    return f"Trying to remove file {file_name} from the S3 bucket raised the error {error_message}."


#Subsection: Success Regexes
def upload_file_to_S3_bucket_success_regex():
    '''For ##Check-upload_file_to_S3_bucket'''
    #ToDo: Create regex matching success return value for `nolcat.app.upload_file_to_S3_bucket()`
    pass


def upload_nonstandard_usage_file_success_regex():
    '''For ##Check-upload_nonstandard_usage_file'''
    #ToDo: Create regex matching success return value for `AnnualUsageCollectionTracking.upload_nonstandard_usage_file()`
    pass


#Section: Database Interactions
#Subsection: Logging/Output Statements
def return_value_from_query_statement(return_value, type_of_query=None):
    """This statement shows an individual value or sequence of values returned by a call to `nolcat.app.query_database()`.

    Args:
        return_value (str, int, or tuple): the value(s) returned by `nolcat.app.query_database()`
        type_of_query (str, optional): some descriptive information about the query; default is `None`

    Returns:
        str: the statement for outputting the arguments to logging
    """
    if type_of_query:
        main_value = f"The {type_of_query} query returned a dataframe from which "
    else:
        main_value = f"The query returned a dataframe from which "
    
    if isinstance(return_value, tuple):
        i = 0
        for value in return_value:
            if i==len(return_value)-1:
                main_value = main_value + "and "
            main_value = f"{main_value}{value} (type {type(value)}), "
            i += 1
        return f"{main_value[:-2]} were extracted."
    else:
        return f"{main_value}{return_value} (type {type(return_value)}) was extracted."


def return_dataframe_from_query_statement(query_subject, df):
    """This statement shows the dataframe returned by a call to `nolcat.app.query_database()`.

    Args:
        query_subject (str): a short summary of what the query was for
        df (dataframe): the dataframe returned by `nolcat.app.query_database()`

    Returns:
        str: the statement for outputting the arguments to logging
    """
    if df.shape[1] > 20:
        return f"The beginning and the end of the query for {query_subject}:\n{df.head(10)}\n...\n{df.tail(10)}"
    else:
        return f"The result of the query for {query_subject}:\n{df}"


#Subsection: Error Statements
def database_query_fail_statement(error_message, value_type="load requested page"):
    """This statement indicates the failure of a call to `nolcat.app.query_database()`.

    Args:
        error_message (str): the return statement indicating the failure of `nolcat.app.query_database()`
        value_type (str, optional): the type of value that the query should have returned; default is ``

    Returns:
        str: the statement for outputting the arguments to logging
    """
    if value_type == "load requested page":
        return f"Unable to {value_type} because {error_message[0].lower()}{error_message[1:].replace(' raised', ', which raised')}"
    else:
        return f"Unable to {value_type} because {error_message[0].lower()}{error_message[1:]}"


def database_update_fail_statement(update_statement):
    """This statement indicates the failure of a call to `nolcat.app.update_database()`.

    Args:
        update_statement (str): the SQL update statement

    Returns:
        str: the statement for outputting the arguments to logging
    """
    update_statement = update_statement.replace('\n', ' ')
    return f"Updating the {update_statement.split()[1]} relation automatically failed, so the SQL update statement needs to be submitted via the SQL command line:\n{update_statement}"


def add_data_success_and_update_database_fail_statement(load_data_response, update_statement):
    """This statement indicates that data was successfully loaded into the database or the S3 bucket, but the corresponding update to the database failed.

    Args:
        load_data_response (str): the return value indicating success from `nolcat.app.load_data_into_database()` or `nolcat.app.upload_file_to_S3_bucket()`
        update_statement (str): the SQL update statement

    Returns:
        str: the statement for outputting the arguments to logging
    """
    update_statement = update_statement.replace('\n', ' ')
    return f"{load_data_response[:-1]}, but updating the {update_statement.split()[1]} relation automatically failed, so the SQL update statement needs to be submitted via the SQL command line:\n{update_statement}"


def database_function_skip_statements(return_value, is_test_function=True, SUSHI_error=False, no_data=False):
    """This statement provides the logging output when a pytest skip is initiated after a `nolcat.app.query_database()`, `nolcat.app.load_data_into_database()`, or `nolcat.app.update_database()` function fails.
    
    Args:
        return_value (str): the error message returned by the database helper function
        is_test_function (bool, optional): indicates if this function is being called within a test function; default is `True`
        SUSHI_error (bool, optional): indicates if the skip is because a SUSHI call returned a SUSHI error; default is `False`
        no_data (bool, optional): indicates if the skip is because a SUSHI call returned no data; default is `False`
    
    Returns:
        str: the statement for outputting the arguments to logging
    """
    if is_test_function:
        if SUSHI_error:
            return f"Unable to run test because the API call raised a server-based SUSHI error, specifically {return_value[0].lower()}{return_value[1:]}"
        elif no_data:
            return f"Unable to run test because no SUSHI data was in the API call response, specifically raising {return_value[0].lower()}{return_value[1:]}"
        else:
            return f"Unable to run test because it relied on {return_value[0].lower()}{return_value[1:].replace(' raised', ', which raised')}"
    else:
        return f"Unable to create fixture because it relied on {return_value[0].lower()}{return_value[1:].replace(' raised', ', which raised')}"


#Subsection: Success Regexes
def load_data_into_database_success_regex():
    '''For ##Check-load_data_into_database'''
    #ToDo: Create regex matching success return value of `nolcat.app.load_data_into_database()`
    pass


def update_database_success_regex():
    '''For ##Check-update_database'''
    #ToDo: Create regex matching success return value of `nolcat.app.update_database()`
    pass


#Section: SUSHI API Calls
#Subsection: Logging/Output Statements
def successful_SUSHI_call_statement(call_path, statistics_source_name):
    """This statement indicates a successful call to `SUSHICallAndResponse.make_SUSHI_call()`.

    Args:
        call_path (str): the last element(s) of the API URL path before the parameters, which represent what is being requested by the API call
        statistics_source_name (str): the name of the statistics source
    
    Returns:
        str: the statement for outputting the arguments to logging
    """
    return f"The call to the `{call_path}` endpoint for {statistics_source_name} successful."


def harvest_R5_SUSHI_success_statement(statistics_source_name, number_of_records, fiscal_year=None):
    """This statement indicates a successful call to `StatisticsSources._harvest_R5_SUSHI()`.

    Args:
        statistics_source_name (str): the name of the statistics source
        number_of_records (int): the number of records found by `StatisticsSources._harvest_R5_SUSHI()`
        fiscal_year (str, optional): the fiscal year for the `StatisticsSources._harvest_R5_SUSHI()` call; default is `None`

    Returns:
        str: the statement for outputting the arguments to logging
    """
    if fiscal_year:
        return f"The SUSHI harvest for statistics source {statistics_source_name} for FY {fiscal_year} successfully found {number_of_records} records."
    else:
        return f"The SUSHI harvest for statistics source {statistics_source_name} successfully found {number_of_records} records."


#Subsection: Error Statements
def failed_SUSHI_call_statement_statement(call_path, statistics_source_name, error_messages, SUSHI_error=True, no_usage_data=False, stop_API_calls=False):
    """This statement indicates a failed call to `SUSHICallAndResponse.make_SUSHI_call()`.

    Args:
        call_path (str): the last element(s) of the API URL path before the parameters, which represent what is being requested by the API call
        statistics_source_name (str): the name of the statistics source
        error_messages (str): the message detailing the error(s) returned by `SUSHICallAndResponse.make_SUSHI_call()`
        SUSHI_error (bool, optional): indicates if the error is a SUSHI error handled by the program; default is `True`
        no_usage_data (bool, optional): indicates if the error indicates that there shouldn't be any usage data; default is `False`
        stop_API_calls (bool, optional): indicates if the error is stopping all SUSHI calls to the given statistics source; default is `False`

    Returns:
        str: the statement for outputting the arguments to logging
    """
    if '\n' in error_messages:
        error_messages = f"s\n{error_messages}\n"
    else:
        error_messages = f" {error_messages} "
    
    if SUSHI_error:
        main_value = f"The call to the `{call_path}` endpoint for {statistics_source_name} raised the SUSHI error{error_messages}"
    else:
        main_value = f"The call to the `{call_path}` endpoint for {statistics_source_name} raised the error{error_messages}"
    
    if no_usage_data:
        return f"{main_value[:-1]}, so the call returned no usage data."
    elif stop_API_calls:
        return main_value + f"API calls to {statistics_source_name} have stopped and no other calls will be made."
    else:
        return main_value


def no_data_returned_by_SUSHI_statement(call_path, statistics_source_name, is_empty_string=False, has_Report_Items=True):
    """This statement indicates a SUSHI call that returned no usage data but didn't contain a SUSHI error explaining the lack of data

    Args:
        call_path (str): the last element(s) of the API URL path before the parameters, which represent what is being requested by the API call
        statistics_source_name (str): the name of the statistics source
        is_empty_string (bool, optional): indicates if the SUSHI call returned an empty string; default is `False`
        has_Report_Items (bool, optional): indicates if the data returned by the SUSHI call had a `Report_Items` section; default is `True`

    Returns:
        str: the statement for outputting the arguments to logging
    """
    if is_empty_string:
        main_value = f"The call to the `{call_path}` endpoint for {statistics_source_name} returned no data"
    else:
        main_value = f"The call to the `{call_path}` endpoint for {statistics_source_name} returned no usage data"
    
    if has_Report_Items:
        return main_value + "."
    else:
        return main_value + " because the SUSHI data didn't have a `Report_Items` section."


def attempted_SUSHI_call_with_invalid_dates_statement(end_date, start_date):
    """This statement indicates an attempter SUSHI call with an invalid date range.

    Args:
        end_date (datetime.date): the given end date of the range
        start_date (datetime.date): the given start date of the range
    
    Returns:
        str: the statement for outputting the arguments to logging
    """
    return f"The given end date of {end_date.strftime('%Y-%m-%d')} is before the given start date of {start_date.strftime('%Y-%m-%d')}, which will cause any SUSHI API calls to return errors; as a result, no SUSHI calls were made. Please correct the dates and try again."


#Subsection: Success Regexes
def count_reports_with_no_usage_regex():
    '''For ##Check-count_reports_with_no_usage'''
    #ToDo: Create regex matching all statements in `no_data_returned_by_SUSHI_statement()` and the no usage data option in `failed_SUSHI_call_statement_statement()`
    pass


def pytest_skip_SUSHI_error_regex():
    '''For ##pytest.skip-SUSHI_error'''
    #ToDo: Create regex matching all possible results of `failed_SUSHI_call_statement_statement()`
    pass


def pytest_skip_no_data_regex():
    '''For ##pytest.skip-no_data'''
    #ToDo: Create regex matching all possible results of `no_data_returned_by_SUSHI_statement()`
    pass


"""Other standardized logging statements, including those in a single class:

* "Starting `function_name()`" statements
    * Info logging statement
    * At the beginning of all functions and methods except for test functions, test fixtures, and those returning a value within five statements
    * Structure: "Starting `<name of function/method>()` for <relevant parameters>."

* Adding to dictionary in the ``ConvertJSONDictToDataframe.create_dataframe()`` method
    * Debug logging statement
    * Structure:
        * Before: "Preparing to add <dictionary key> value `<dictionary value>` to the record."
        * After: "Added `COUNTERData.<dictionary key>` value <dictionary value> to `<name of dict>`."

* Finding values for a given field are longer than the field's max length
    * Critical logging statement
    * In the ``ConvertJSONDictToDataframe`` class
    * Structure: "Increase the `<attribute name>` max field length to <length of the value found + 10%>."

* Upload database initialization relations
    * Debug logging statement; errors are error logging statement
    * In the ``nolcat.initialization.views`` module
    * Success structure: "The `<relation name>` FileField data:\n<FileField object>"
    * Blank file uploaded (failure) structure: "The `<relation name>` relation data file was read in with no data."
"""