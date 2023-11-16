import io
import logging
from pathlib import Path
from datetime import datetime
from itertools import product
import json
import re
from sqlalchemy import log as SQLAlchemy_log
from flask import Flask
from flask import render_template
from flask import send_file
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import pandas as pd
from numpy import squeeze
import boto3
import botocore.exceptions  # `botocore` is a dependency of `boto3`

from .statements import *

"""Since GitHub is used to manage the code, and the repo is public, secret information is stored in a file named `nolcat_secrets.py` exclusive to the Docker container and imported into this file.

The overall structure of this app doesn't facilitate a separate module for a SQLAlchemy `create_engine` function: when `nolcat/__init__.py` is present, keeping these functions in a separate module and importing them causes a ``ModuleNotFoundError: No module named 'database_connectors'`` error when starting up the Flask server, but with no `__init__` file, the blueprint folder imports don't work. With Flask-SQLAlchemy, a string for the config variable `SQLALCHEMY_DATABASE_URI` is all that's needed, so the data the string needs are imported from a `nolcat_secrets.py` file saved to Docker and added to this directory during the build process. This import has been problematic; moving the file from the top-level directory to this directory and providing multiple possible import statements in try-except blocks are used to handle the problem.
"""
try:
    import nolcat_secrets as secrets
except:
    try:
        from . import nolcat_secrets as secrets
    except:
        try:
            from nolcat import nolcat_secrets as secrets
        except:
            print("None of the provided import statements for `nolcat\\nolcat_secrets.py` worked.")

DATABASE_USERNAME = secrets.Username
DATABASE_PASSWORD = secrets.Password
DATABASE_HOST = secrets.Host
DATABASE_PORT = secrets.Port
DATABASE_SCHEMA_NAME = secrets.Database
SECRET_KEY = secrets.Secret
BUCKET_NAME = secrets.Bucket
PATH_WITHIN_BUCKET = "raw-vendor-reports/"  #ToDo: The location of files within a S3 bucket isn't sensitive information; should it be included in the "nolcat_secrets.py" file?
TOP_NOLCAT_DIRECTORY = Path(*Path(__file__).parts[0:Path(__file__).parts.index('nolcat')+1])


def configure_logging(app):
    """Create single logging configuration for entire program.

    This function was largely based upon the information at https://shzhangji.com/blog/2022/08/10/configure-logging-for-flask-sqlalchemy-project/ with some additional information from https://engineeringfordatascience.com/posts/python_logging/.

    Args:
        app (flask.Flask): the Flask object

    Returns:
        None: no return value is needed, so the default `None` is used
    """
    logging.basicConfig(
        level=logging.DEBUG,  # This sets the logging level displayed in stdout and the minimum logging level available with pytest's `log-cli-level` argument at the command line
        format= "[%(asctime)s] %(name)s::%(lineno)d - %(message)s",  # "[timestamp] module name::line number - error message"
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    #Test: SQLAlchemy logging statements appear when when no live log output is requested--investigate and determine if related to the to-do below
    SQLAlchemy_log._add_default_handler = lambda handler: None  # Patch to avoid duplicate logging (from https://stackoverflow.com/a/76498428)
    #ToDo: `pd.to_sql()` logging output begins with multiple setup statements with messages of just a pair of parentheses in between; some parentheses-only logging statements also appear in the `pd.read_sql()` output. Is there a way to remove those statements from the logging output?
    logging.getLogger('botocore').setLevel(logging.INFO)  # This prompts `s3transfer` module logging to appear
    logging.getLogger('s3transfer.utils').setLevel(logging.INFO)  # Expected log statements seem to be set at debug level, so this hides all log statements
    if app.debug:
        logging.getLogger('werkzeug').handlers = []  # Prevents Werkzeug from outputting messages twice in debug mode


log = logging.getLogger(__name__)


csrf = CSRFProtect()
db = SQLAlchemy()
s3_client = boto3.client('s3')  # Authentication is done through a CloudFormation init file


def page_not_found(error):
    """Returns the 404 page when a HTTP 404 error is raised."""
    return render_template('404.html'), 404


def internal_server_error(error):
    """Returns the 500 page when a HTTP 500 error is raised."""
    return render_template('500.html', error=error), 500  #ToDo: This doesn't seem to be working; figure out why


def create_app():
    """A factory pattern for instantiating Flask web apps."""
    log.info("Starting `create_app()`.")
    app = Flask(__name__)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_SCHEMA_NAME}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Explicitly set to disable warning in tests
    app.config['SQLALCHEMY_ECHO'] = False  # This prevents SQLAlchemy from duplicating the log output generated by `nolcat.app.configure_logging()`
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['UPLOAD_FOLDER'] = './static'  # This config is never invoked because Flask alone is never used for file I/O.
    csrf.init_app(app)
    db.init_app(app)
    configure_logging(app)

    #Section: Create Command to Build Schema
    # Documentation for decorator at https://flask.palletsprojects.com/en/2.1.x/appcontext/
    @app.cli.command('create-db')
    def create_db():
        with create_app().app_context():  # Creates an app context using the Flask factory pattern
            # Per instructions at https://flask-sqlalchemy.palletsprojects.com/en/2.x/quickstart/: "To create the initial database, just import the db object[s]...and run the `SQLAlchemy.create_all()` method"
            from .models import FiscalYears
            from .models import Vendors
            from .models import VendorNotes
            from .models import StatisticsSources
            from .models import StatisticsSourceNotes
            from .models import ResourceSources
            from .models import ResourceSourceNotes
            from .models import StatisticsResourceSources
            from .models import AnnualUsageCollectionTracking
            from .models import COUNTERData
            db.create_all()

    #Section: Register Blueprints
    try:
        from nolcat import annual_stats
    except:
        from . import annual_stats
    app.register_blueprint(annual_stats.bp)

    try:
        from nolcat import ingest_usage
    except:
        from . import ingest_usage
    app.register_blueprint(ingest_usage.bp)

    try:
        from nolcat import initialization
    except:
        from . import initialization
    app.register_blueprint(initialization.bp)

    try:
        from nolcat import login
    except:
        from . import login
    app.register_blueprint(login.bp)

    try:
        from nolcat import view_lists
    except:
        from . import view_lists
    app.register_blueprint(view_lists.bp)

    try:
        from nolcat import view_usage
    except:
        from . import view_usage
    app.register_blueprint(view_usage.bp)

    #Section: Create Basic Routes
    @app.route('/')
    def homepage():
        """Returns the homepage in response to web app root requests."""
        return render_template('index.html')
    
    
    @app.route('/download/<path:file_path>',  methods=['GET', 'POST'])
    def download_file(file_path):
        """Downloads the file at the absolute file path in the variable route.

        An absolute file path is used to ensure that issues of relative locations and changing current working directories don't cause errors.

        Args:
            file_path (str): an absolute file path
        
        Returns:
            file: a file is downloaded to the host machine through the web application
        """
        log.info(f"Starting `create_app.download_file()` for file at path {file_path} (type {type(file_path)}).")
        file_path = Path(  # Just using the `Path()` constructor creates a relative path; relative paths in `send_file()` are considered in relation to CWD
            *Path(__file__).parts[0:Path(__file__).parts.index('nolcat')+1],  # This creates an absolute file path from the *nix root or Windows drive to the outer `nolcat` folder
            *Path(file_path).parts[Path(file_path).parts.index('nolcat')+1:],  # This creates a path from `file_path` with everything after the initial `nolcat` folder
        )
        log.info(f"`file_path` after type juggling is '{file_path}' (type {type(file_path)}) which is an absolute file path: {file_path.is_absolute()}.")
        return send_file(
            path_or_file=file_path,
            mimetype=file_extensions_and_mimetypes()[file_path.suffix],  # Suffixes that aren't keys in `file_extensions_and_mimetypes()` can't be uploaded to S3 via NoLCAT
            as_attachment=True,
            download_name=file_path.name,
            last_modified=datetime.today(),
        )


    return app


def date_parser(dates):
    """The function for parsing dates as part of converting ingested data into a dataframe.
    
    The `date_parser` argument of pandas's methods for reading external files to a dataframe traditionally takes a lambda expression, but due to repeated use throughout the program, a reusable function is a better option. Using the `to_datetime` method itself ensures dates will be in ISO format in dataframes, facilitating the upload of those dataframes to the database.

    Args:
        dates (date, datetime, string): a value in a data file being read into a pandas dataframe being interpreted as a date

    Returns:
        datetime64[ns]: a datetime value pandas inherits from numpy
    """
    return pd.to_datetime(dates, format='%Y-%m-%d', errors='coerce', infer_datetime_format=True)  # The `errors` argument sets all invalid parsing values, including null values and empty strings, to `NaT`, the null value for the pandas datetime data type


def last_day_of_month(first_day_of_month):
    """The function for returning the last day of a given month.

    When COUNTER date ranges include the day, the "End_Date" value is for the last day of the month. This function consolidates that functionality in a single location and facilitates its use in pandas `map` functions.

    Args:
        first_day_of_month (pd.Timestamp): the first day of the month; the dataframe of origin will have the date in a datetime64[ns] data type, but within this function, the data type is Timestamp
    
    Returns:
        str: the last day of the given month in ISO format
    """
    year_and_month_string = first_day_of_month.date().isoformat()[0:-2]  # Returns an ISO date string, then takes off the last two digits
    return year_and_month_string + str(first_day_of_month.days_in_month)


def first_new_PK_value(relation):
    """The function for getting the next value in the primary key sequence.

    The default value of the SQLAlchemy `autoincrement` argument in the field constructor method adds `AUTO_INCREMENT` to the primary key field in the data definition language. Loading values, even ones following the sequential numbering that auto-incrementation would use, alters the relation's `AUTO_INCREMENT` attribute, causing a primary key duplication error. Stopping this error requires removing auto-incrementation from the primary key fields (by setting the `autoincrement` argument in the field constructor method to `False`); without the auto-incrementation, however, the primary key values must be included as the dataframe's record index field. This function finds the highest value in the primary key field of the given relation and returns the next integer.

    Args:
        relation (str): the name of the relation being checked
    
    Returns:
        int: the first primary key value in the data to be uploaded to the relation
        str: a message including the error raised by the attempt to run the query
    """
    log.info(f"Starting `first_new_PK_value()` for the {relation} relation.")
    if relation == 'fiscalYears':
        PK_field = 'fiscal_year_ID'
    elif relation == 'vendors':
        PK_field = 'vendor_ID'
    elif relation == 'vendorNotes':
        PK_field = 'vendor_notes_ID'
    elif relation == 'statisticsSources':
        PK_field = 'statistics_source_ID'
    elif relation == 'statisticsSourceNotes':
        PK_field = 'statistics_source_notes_ID'
    elif relation == 'resourceSources':
        PK_field = 'resource_source_ID'
    elif relation == 'resourceSourceNotes':
        PK_field = 'resource_source_notes_ID'
    elif relation == 'COUNTERData':
        PK_field = 'COUNTER_data_ID'
    
    largest_PK_value = query_database(
        query=f"""
            SELECT {PK_field} FROM {relation}
            ORDER BY {PK_field} DESC
            LIMIT 1;
        """,
        engine=db.engine,
    )
    if isinstance(largest_PK_value, str):
        log.debug(database_query_fail_statement(largest_PK_value, "return requested value"))
        return largest_PK_value  # Only passing the initial returned error statement to `nolcat.statements.unable_to_get_updated_primary_key_values_statement()`
    elif largest_PK_value.empty:  # If there's no data in the relation, the dataframe is empty, and the primary key numbering should start at zero
        log.debug(f"The {relation} relation is empty.")
        return 0
    else:
        largest_PK_value = largest_PK_value.iloc[0][0]
        log.debug(return_value_from_query_statement(largest_PK_value))
        return int(largest_PK_value) + 1


def return_string_of_dataframe_info(df):
    """Returns the data output by `pandas.DataFrame.info()` as a string so the method can be used in logging statements.

    The `pandas.DataFrame.info()` method forgoes returning a value in favor of printing directly to stdout; as a result, it doesn't output anything when used in a logging statement. This function captures the data traditionally output directly to stdout in a string for use in a logging statement. This function is based off the one at https://stackoverflow.com/a/39440325.

    Args:
        df (dataframe): the dataframe in the logging statement
    
    Returns:
        str: the output of the `pandas.DataFrame.info()` method
    """
    in_memory_stream = io.StringIO()
    df.info(buf=in_memory_stream)
    return in_memory_stream.getvalue()


def change_single_field_dataframe_into_series(df):
    """The function for changing a dataframe with a single field into a series.

    This function transforms any dataframe with a single non-index field into a series with the same index. Dataframes with multiindexes are accepted and those indexes are preserved.

    Args:
        df (dataframe): the dataframe to be transformed
    
    Returns:
        pd.Series: a series object with the same exact data as the initial dataframe
    """
    return pd.Series(
        data=squeeze(df.values),  # `squeeze` converts the numpy array from one column with n elements to an array with n elements
        index=df.index,
        dtype=df[df.columns[0]].dtype,
        name=df.columns[0],
    )


def restore_boolean_values_to_boolean_field(series):
    """The function for converting the integer field used for Booleans in MySQL into a pandas `boolean` field.

    MySQL stores Boolean values in a `TINYINT(1)` field, so any Boolean fields read from the database into a pandas dataframe appear as integer or float fields with the values `1`, `0`, and, if nulls are allowed, `pd.NA`. For simplicity, clarity, and consistency, turning these fields back into pandas `boolean` fields is often a good idea.

    Args:
        series (pd.Series): a Boolean field with numeric values and a numeric dtype from MySQL
    
    Returns:
        pd.Series: a series object with the same information as the initial series but with Boolean values and a `boolean` dtype
    """
    return series.replace({
        0: False,
        1: True,
    }).astype('boolean')


def upload_file_to_S3_bucket(file, file_name, client=s3_client, bucket=BUCKET_NAME, bucket_path=PATH_WITHIN_BUCKET):
    """The function for uploading files to a S3 bucket.  #ALERT: On 2023-10-20, this created a file, but the only contents of that file were some ending curly and square braces

    SUSHI pulls that cannot be loaded into the database for any reason are saved to S3 with a file name following the convention "{statistics_source_ID}_{report path with hyphen replacing slash}_{date range start in 'yyyy-mm' format}_{date range end in 'yyyy-mm' format}_{ISO timestamp}". Non-COUNTER usage files use the file naming convention "{statistics_source_ID}_{fiscal_year_ID}".

    Args:
        file (file-like or path-like object): the file being uploaded to the S3 bucket or the path to said file as a Python object
        file_name (str): the name the file will be saved under in the S3 bucket
        client (S3.Client, optional): the client for connecting to an S3 bucket; default is `S3_client` initialized at the beginning of this module
        bucket (str, optional): the name of the S3 bucket; default is constant derived from `nolcat_secrets.py`
        bucket_path (str, optional): the path within the bucket where the files will be saved; default is constant initialized at the beginning of this module
    
    Returns:
        str: the logging statement to indicate if uploading the data succeeded or failed
    """
    log.info(f"Starting `upload_file_to_S3_bucket()` for the file named {file_name}.")
    #Section: Confirm Bucket Exists
    # The canonical way to check for a bucket's existence and the user's privilege to access it
    try:
        check_for_bucket = s3_client.head_bucket(Bucket=bucket)
    except botocore.exceptions.ClientError as error:
        message = f"Unable to upload files to S3 because the check for the S3 bucket designated for downloads raised the error {error}."
        log.error(message)
        return message
 

    #Section: Upload File to Bucket
    log.debug(f"Loading object {file} (type {type(file)}) with file name `{file_name}` into S3 location `{bucket}/{bucket_path}`.")
    #Subsection: Upload File with `upload_fileobj()`
    try:
        file_object = open(file, 'rb')
        log.debug(f"Successfully initialized {file_object} (type {type(file_object)}).")
        try:
            client.upload_fileobj(
                Fileobj=file_object,
                Bucket=bucket,
                Key=bucket_path + file_name,
            )
            file_object.close()
            message = f"Successfully loaded the file {file_name} into the {bucket} S3 bucket."
            log.info(message)
            return message
        except Exception as error:
            log.warning(f"Running the function `upload_fileobj()` on {file_object} (type {type(file_object)}) raised the error {error}. The system will now try to use `upload_file()`.")
            file_object.close()
    except Exception as error:
        log.warning(f"Running the function `open()` on {file} (type {type(file)}) raised the error {error}. The system will now try to use `upload_file()`.")
    
    #Subsection: Upload File with `upload_file()`
    if file.is_file():
        try:
            client.upload_file(  # This uploads `file` like a path-like object
                Filename=file,
                Bucket=bucket,
                Key=bucket_path + file_name,
            )
            message = f"Successfully loaded the file {file_name} into the {bucket} S3 bucket."
            log.info(message)
            return message
        except Exception as error:
            message = f"Running the function `upload_file()` on {file} (type {type(file)}) raised the error {error}."
            log.error(message)
            return message
    else:
        message = f"Unable to load file {file} (type {type(file)}) into an S3 bucket because it relied the ability for {file} to be a file-like or path-like object."
        log.error(message)
        return message


def create_AUCT_SelectField_options(df):
    """Transforms a dataframe into a list of options for use as SelectField options.

    A dataframe with the fields `annualUsageCollectionTracking.AUCT_statistics_source`, `annualUsageCollectionTracking.AUCT_fiscal_year`, `statisticsSources.statistics_source_name`, and `fiscalYears.fiscal_year` is changed into a list of tuples, one for each record; the first value is another tuple with the primary key values from `annualUsageCollectionTracking`, and the second value is a string showing the statistics source name and fiscal year.

    Args:
        df (dataframe): a dataframe with the fields `annualUsageCollectionTracking.AUCT_statistics_source`, `annualUsageCollectionTracking.AUCT_fiscal_year`, `statisticsSources.statistics_source_name`, and `fiscalYears.fiscal_year`
    
    Returns:
        list: a list of tuples; see the docstring's detailed description for the contents of the list
    """
    log.info(f"Starting `create_AUCT_SelectField_options()` for the {df} dataframe.")
    df = df.set_index(['AUCT_statistics_source', 'AUCT_fiscal_year'])
    df['field_display'] = df[['statistics_source_name', 'fiscal_year']].apply("--FY ".join, axis='columns')  # Standard string concatenation with `astype` methods to ensure both values are strings raises `IndexError: only integers, slices (`:`), ellipsis (`...`), numpy.newaxis (`None`) and integer or Boolean arrays are valid indices`
    df = df.drop(columns=['statistics_source_name', 'fiscal_year'])
    s = change_single_field_dataframe_into_series(df)
    log.info(f"AUCT multiindex values and their corresponding form choices:\n{s}")
    return list(s.items())


def load_data_into_database(df, relation, engine, index_field_name=None):
    """A wrapper for the pandas `to_sql()` method that includes the error handling.

    Args:
        df (dataframe): the data to load into the database
        relation (str): the relation the data is being loaded into
        engine (sqlalchemy.engine.Engine): a SQLAlchemy engine
        index_field_name (str or list of str): the name of the field(s) in the relation that the dataframe index values should be loaded into; default is `None`, same as in the wrapped method, which means the index field name(s) are matched to field(s) in the relation

    Returns:
        str: a message indicating success or including the error raised by the attempt to load the data
    """
    log.info(f"Starting `load_data_into_database()` for relation {relation}.")
    try:
        df.to_sql(
            name=relation,
            con=engine,
            if_exists='append',
            chunksize=1000,
            index_label=index_field_name,
        )
        message = f"Successfully loaded {df.shape[0]} records into the {relation} relation."
        log.info(message)
        return message
    except Exception as error:
        message = f"Loading data into the {relation} relation raised the error {error}."
        log.error(message)
        return message


def query_database(query, engine, index=None):
    """A wrapper for the `pd.read_sql()` method that includes the error handling.

    Args:
        query (str): the SQL query
        engine (sqlalchemy.engine.Engine): a SQLAlchemy engine
        index (str or list of str): the field(s) in the resulting dataframe to use as the index; default is `None`, same as in the wrapped method
    
    Returns:
        dataframe: the result of the query
        str: a message including the error raised by the attempt to run the query
    """
    log.info(f"Starting `query_database()` for query {query}.")
    try:
        df = pd.read_sql(
            sql=query,
            con=engine,
            index_col=index,
        )
        if df.shape[1] > 20:
            log.info(f"The beginning and the end of the response to `{query}`:\n{df.head(10)}\n...\n{df.tail(10)}")
            log.debug(f"The complete response to `{query}`:\n{df}")
        else:
            log.info(f"The complete response to `{query}`:\n{df}")
        return df
    except Exception as error:
        message = f"Running the query `{query}` raised the error {error}."
        log.error(message)
        return message


def check_if_data_already_in_COUNTERData(df):  #ALERT: NOT WORKING -- NOT PERFORMING AS EXPECTED, NOT STOPPING CALLS
    """Checks if records for a given combination of statistics source, report type, and date are already in the `COUNTERData` relation.

    Individual attribute lists are deduplicated with `list(set())` construction because `pandas.Series.unique()` method returns numpy arrays or experimental pandas arrays depending on the origin series' dtype.

    Args:
        df (dataframe): the data to be loaded into the `COUNTERData` relation
    
    Returns:
        tuple: the dataframe to be loaded into `COUNTERData` or `None` if if no records are being loaded; the message to be flashed about the records not loaded or `None` if all records are being loaded (str or None)
    """
    log.info(f"Starting `check_if_data_already_in_COUNTERData()`.")

    #Section: Get the Statistics Sources, Report Types, and Dates
    #Subsection: Get the Statistics Sources
    statistics_sources_in_dataframe = df['statistics_source_ID'].tolist()
    log.debug(f"All statistics sources as a list:\n{statistics_sources_in_dataframe}")
    statistics_sources_in_dataframe = list(set(statistics_sources_in_dataframe))
    log.debug(f"All statistics sources as a deduped list:\n{statistics_sources_in_dataframe}")

    #Subsection: Get the Report Types
    report_types_in_dataframe = df['report_type'].tolist()
    log.debug(f"All report types as a list:\n{report_types_in_dataframe}")
    report_types_in_dataframe = list(set(report_types_in_dataframe))
    log.debug(f"All report types as a deduped list:\n{report_types_in_dataframe}")

    #Subsection: Get the Dates
    dates_in_dataframe = df['usage_date'].tolist()
    log.debug(f"All usage dates as a list:\n{dates_in_dataframe}")
    dates_in_dataframe = list(set(dates_in_dataframe))
    log.debug(f"All usage dates as a deduped list:\n{dates_in_dataframe}")

    #Section: Check Database for Combinations of Above
    combinations_to_check = tuple(product(statistics_sources_in_dataframe, report_types_in_dataframe, dates_in_dataframe))
    log.info(f"Checking the database for the existence of records with the following statistics source ID, report type, and usage date combinations: {combinations_to_check}")
    total_number_of_matching_records = 0
    matching_record_instances = []
    for combo in combinations_to_check:
        number_of_matching_records = query_database(
            query=f"SELECT COUNT(*) FROM COUNTERData WHERE statistics_source_ID={combo[0]} AND report_type='{combo[1]}' AND usage_date='{combo[2].strftime('%Y-%m-%d')}';",
            engine=db.engine,
        )
        if isinstance(number_of_matching_records, str):
            return (None, database_query_fail_statement(number_of_matching_records, "return requested value"))
        number_of_matching_records = number_of_matching_records.iloc[0][0]
        log.debug(return_value_from_query_statement(number_of_matching_records, f"existing usage for statistics_source_ID {combo[0]}, report {combo[1]}, and date {combo[2].strftime('%Y-%m-%d')}"))
        if number_of_matching_records > 0:
            matching_record_instances.append({
                'statistics_source_ID': combo[0],
                'report_type': combo[1],
                'usage_date': combo[2],
            })
            log.debug(f"The list of combinations with matches in the database now includes {matching_record_instances[-1]}.")
            total_number_of_matching_records = total_number_of_matching_records + number_of_matching_records
        
    #Section: Return Result
    if total_number_of_matching_records > 0:
        #Subsection: Get Records and Statistics Source Names for Matches
        records_to_remove = []
        for instance in matching_record_instances:
            to_remove = df[
                (df['statistics_source_ID']==instance['statistics_source_ID']) &
                (df['report_type']==instance['report_type']) &
                (df['usage_date']==instance['usage_date'])
            ]
            records_to_remove.append(to_remove)

            statistics_source_name = query_database(
                query=f"SELECT statistics_source_name FROM statisticsSources WHERE statistics_source_ID={instance['statistics_source_ID']};",
                engine=db.engine,
            )
            if isinstance(statistics_source_name, str):
                return (None, database_query_fail_statement(statistics_source_name, "return requested value"))
            instance['statistics_source_name'] = statistics_source_name.iloc[0][0]
        
        #Subsection: Return Results
        records_to_remove = pd.concat(records_to_remove)
        records_to_keep = df[
            pd.merge(
                df,
                records_to_remove,
                how='left',  # Because all records come from the left (first) dataframe, there's no difference between a left and outer join
                indicator=True,
            )['_merge']=='left_only'
        ]
        matching_record_instances_list = []
        for instance in matching_record_instances:
            matching_record_instances_list.append(f"{instance['report_type']:3} | {instance['usage_date'].strftime('%Y-%m-%d')} | {instance['statistics_source_name']} (ID {instance['statistics_source_ID']})")
        message = f"Usage statistics for the report type, usage date, and statistics source combination(s) below, which were included in the upload, are already in the database; as a result, it wasn't uploaded to the database. If the data needs to be re-uploaded, please remove the existing data from the database first.\n{format_list_for_stdout(matching_record_instances_list)}"
        log.info(message)
        return (records_to_keep, message)
    else:
        return (df, None)


def update_database(update_statement, engine):
    """A wrapper for the `Engine.execute()` method that includes the error handling.

    The `execute()` method of the `sqlalchemy.engine.Engine` class automatically commits the changes made by the statement.

    Args:
        update_statement (str): the SQL update statement
        engine (sqlalchemy.engine.Engine): a SQLAlchemy engine
    
    Returns:
        str: a message indicating success or including the error raised by the attempt to update the data
    """
    log.info(f"Starting `update_database()` for the update statement {update_statement}.")
    try:
        engine.execute(update_statement)
        log.debug(f"`update_statement` is {update_statement}")  #temp
        single_line_update_statement = update_statement.replace('\n', ' ')
        log.debug(f"`single_line_update_statement` is {single_line_update_statement}")  #temp
        message = f"Successfully preformed the update `{update_statement}`."
        log.info(message)
        return message
    except Exception as error:
        message = f"Running the update statement `{update_statement}` raised the error {error}."
        log.error(message)
        return message


def save_unconverted_data_via_upload(data, file_name_stem):
    """A wrapper for the `upload_file_to_S3_bucket()` when saving SUSHI data that couldn't change data types when needed.

    Data going into the S3 bucket must be saved to a file because `upload_file_to_S3_bucket()` takes file-like objects or path-like objects that lead to file-like objects. These files have a specific naming convention, but the file name stem is an argument in the function call to simplify both this function and its testing.

    Args:
        data (dict or str): the data to be saved to a file in S3
        file_name_stem (str): the stem of the name the file will be saved with in S3
    
    Returns:
        str: a message indicating success or including the error raised by the attempt to load the data
    """
    log.info(f"Starting `save_unconverted_data_via_upload()`.")

    #Section: Create Temporary File
    #Subsection: Create File Path
    if isinstance(data, dict):
        temp_file_name = 'temp.json'
    else:
        temp_file_name = 'temp.txt'
    temp_file_path = TOP_NOLCAT_DIRECTORY / temp_file_name
    temp_file_path.unlink(missing_ok=True)
    log.info(f"Contents of `{TOP_NOLCAT_DIRECTORY}` after `unlink()` at start of `save_unconverted_data_via_upload()`:\n{format_list_for_stdout(TOP_NOLCAT_DIRECTORY.iterdir())}")

    #Subsection: Save File
    if temp_file_name == 'temp.json':
        try:
            with open(temp_file_path, 'wb') as file:
                log.debug(f"About to write bytes JSON `data` (type {type(data)}) to file object {file}.")  #AboutTo
                json.dump(data, file)
            log.debug(f"Data written as bytes JSON to file object {file}.")
        except Exception as TypeError:
            with open(temp_file_path, 'wt') as file:
                log.debug(f"About to write text JSON `data` (type {type(data)}) to file object {file}.")  #AboutTo
                file.write(json.dumps(data))
                log.debug(f"Data written as text JSON to file object {file}.")
    else:
        try:
            with open(temp_file_path, 'wb') as file:
                log.debug(f"About to write bytes `data` (type {type(data)}) to file object {file}.")  #AboutTo
                file.write(data)
                log.debug(f"Data written as bytes to file object {file}.")
        except Exception as binary_error:
            try:
                with open(temp_file_path, 'wt', encoding='utf-8', errors='backslashreplace') as file:
                    log.debug(f"About to write text `data` (type {type(data)}) to file object {file}.")  #AboutTo
                    file.write(data)
                    log.debug(f"Data written as text to file object {file}.")
            except Exception as text_error:
                message = f"Writing data into a binary file raised the error {binary_error}; writing that data into a text file raised the error {text_error}."
                log.error(message)
                return message
    log.debug(f"File at {temp_file_path} successfully created.")

    #Section: Upload File to S3
    file_name = file_name_stem + temp_file_path.suffix
    log.debug(f"About to upload file '{file_name}' from temporary file location {temp_file_path} to S3 bucket {BUCKET_NAME}.")
    logging_message = upload_file_to_S3_bucket(
        temp_file_path,
        file_name,
    )
    log.info(f"Contents of `{Path(__file__).parent}` before `unlink()` at end of `save_unconverted_data_via_upload()`:\n{format_list_for_stdout(Path(__file__).parent.iterdir())}")
    temp_file_path.unlink()
    log.info(f"Contents of `{Path(__file__).parent}` after `unlink()` at end of `save_unconverted_data_via_upload()`:\n{format_list_for_stdout(Path(__file__).parent.iterdir())}")
    if isinstance(logging_message, str) and re.fullmatch(r'Running the function `.*\(\)` on .* \(type .*\) raised the error .*\.', logging_message):
        message = f"Uploading the file {file_name} to S3 failed because {logging_message[0].lower()}{logging_message[1:]}"
        log.critical(message)
    else:
        message = logging_message
        log.debug(message)
    return message


def ISSN_regex():
    """A regex object matching an ISSN.

    Returns:
        re.Pattern: the regex object
    """
    return re.compile(r"\d{4}\-\d{3}[\dxX]\s*")