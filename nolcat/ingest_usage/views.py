import logging
from datetime import date
import calendar
from ast import literal_eval
from flask import render_template
from flask import request
from flask import abort
from flask import redirect
from flask import url_for
from flask import flash
import pandas as pd
from werkzeug.utils import secure_filename

from . import bp
from .forms import *
from ..app import *
from ..models import *
from ..statements import *
from ..upload_COUNTER_reports import UploadCOUNTERReports

log = logging.getLogger(__name__)


@bp.route('/')
def ingest_usage_homepage():
    """Returns the homepage for the `ingest_usage` blueprint, which has links to the different usage upload options."""
    return render_template('ingest_usage/index.html')


@bp.route('/upload-COUNTER', methods=['GET', 'POST'])
def upload_COUNTER_data():
    """The route function for uploading COUNTER data into the `COUNTERData` relation."""
    log.info("Starting `upload_COUNTER_data()`.")
    form = COUNTERDataForm()
    if request.method == 'GET':
        return render_template('ingest_usage/upload-COUNTER-data.html', form=form)
    elif form.validate_on_submit():
        file_objects = form.COUNTER_data.data  # `form.COUNTER_data.data` is a list of <class 'werkzeug.datastructures.FileStorage'> objects, the mimetypes of which need to be determined
        mimetype_set = set()  # Using a set for automatic deduplication; when referencing contents, list constructor is used to change set into a list, making it compatible with index operators
        for file in file_objects:
            log.debug(f"Uploading the file {file} (type {type(file)}; mimetype {file.mimetype}).")
            if file.mimetype == 'application/octet-stream' and file.filename.endswith('.sql'):  # SQL files can have the generic `octet-stream` mimetype (before IANA RFC6922, SQL did use that mimetype)
                mimetype_set.add('application/sql')
            else:
                mimetype_set.add(file.mimetype)
        
        if len(mimetype_set) > 1:
            message = "The form submission failed because the upload included multiple file types. Please try again with only SQL files or Excel workbooks."
            log.error(message)
            flash(message)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        elif list(mimetype_set)[0] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            try:
                df, data_not_in_df = UploadCOUNTERReports(file_objects).create_dataframe()  
                df['report_creation_date'] = pd.to_datetime(None)
                if data_not_in_df:
                    messages_to_flash = [f"The following worksheets and workbooks weren't included in the loaded data:\n{format_list_for_stdout(data_not_in_df)}"]
                else:
                    messages_to_flash = []
            except Exception as error:
                message = unable_to_convert_SUSHI_data_to_dataframe_statement(error)
                log.error(message)
                flash(message)
                return redirect(url_for('ingest_usage.ingest_usage_homepage'))
            log.debug(f"`COUNTERData` data:\n{df}\n")
            
            try:
                df, message_to_flash = check_if_data_already_in_COUNTERData(df)
            except Exception as error:
                message = f"The uploaded data wasn't added to the database because the check for possible duplication raised {error}."
                log.error(message)
                flash(message)
                return redirect(url_for('ingest_usage.ingest_usage_homepage'))
            if df is None:
                flash(message_to_flash)
                return redirect(url_for('ingest_usage.ingest_usage_homepage'))
            if message_to_flash:
                messages_to_flash.append(message_to_flash)
            
            try:
                df.index += first_new_PK_value('COUNTERData')
            except Exception as error:
                message = unable_to_get_updated_primary_key_values_statement("COUNTERData", error)
                log.warning(message)
                messages_to_flash.append(message)
                flash(messages_to_flash)
                return redirect(url_for('ingest_usage.ingest_usage_homepage'))
            log.info(f"Sample of data to load into `COUNTERData` dataframe:\n{df.head()}\n...\n{df.tail()}\n")
            log.debug(f"Data to load into `COUNTERData` dataframe:\n{df}\n")
            load_result = load_data_into_database(
                df=df,
                relation='COUNTERData',
                engine=db.engine,
                index_field_name='COUNTER_data_ID',
            )
            messages_to_flash.append(load_result)
            flash(messages_to_flash)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        elif list(mimetype_set)[0] == 'application/sql':
            insert_statements = []
            for file in file_objects:
                for line in file.stream:  # `file.stream` is a <class 'tempfile.SpooledTemporaryFile'> object and can be treated like a file object created with `open()`
                    display_line = truncate_longer_lines(line)  # Size of lines on display limited to prevent memory errors due to overly long lines
                    log.debug(f"The line starting `{display_line}` in the SQL file data is type {type(line)}.")
                    COUNTERData_insert_statement = re.fullmatch(br"(INSERT INTO `COUNTERData` (\(.+\) )?VALUES.+\);)\s*", line)  # The `\s*` after the semicolon is for the new line character(s)
                    if COUNTERData_insert_statement:
                        COUNTERData_insert_statement = COUNTERData_insert_statement.groups()[0].decode('utf-8')
                        log.debug(f"Adding the line starting `{display_line}` to the list of insert statements.")
                        insert_statements.append(COUNTERData_insert_statement)
            messages_to_flash = []
            for statement in insert_statements:
                update_result = update_database(
                    update_statement=statement,
                    engine=db.engine,
                )
                if not update_database_success_regex().fullmatch(update_result):
                    message = database_update_fail_statement(statement)
                    log.warning(message)
                    messages_to_flash.append(message)   
            
            flash(messages_to_flash)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        else:
            message = f"The form submission failed because the upload was made up of {list(mimetype_set)[0]} file(s). Please try again with only SQL files or Excel workbooks."
            log.error(message)
            flash(message)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
    else:
        message = Flask_error_statement(form.errors)
        log.error(message)
        flash(message)
        return abort(404)


@bp.route('/harvest/', defaults={'testing': ""}, methods=['GET', 'POST'])
@bp.route('/harvest/<string:testing>', methods=['GET', 'POST'])
def harvest_SUSHI_statistics(testing):
    """A page for initiating R5 SUSHI usage statistics harvesting.
    
    This page lets the user input custom parameters for an R5 SUSHI call, then executes the `StatisticsSources.collect_usage_statistics()` method. From this page, SUSHI calls for specific statistics sources with date ranges other than the fiscal year can be performed. 

    Args:
        testing (str, optional): an indicator that the route function call is for a test; default is an empty string which indicates POST is for production
    """
    log.info("Starting `harvest_SUSHI_statistics()`.")
    form = SUSHIParametersForm()
    if request.method == 'GET':
        statistics_source_options = query_database(
            query="SELECT statistics_source_ID, statistics_source_name FROM statisticsSources WHERE statistics_source_retrieval_code IS NOT NULL ORDER BY statistics_source_name;",
            engine=db.engine,
        )
        if isinstance(statistics_source_options, str):
            flash(database_query_fail_statement(statistics_source_options))
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        form.statistics_source.choices = list(statistics_source_options.itertuples(index=False, name=None))
        return render_template('ingest_usage/make-SUSHI-call.html', form=form, testing=testing)
    elif form.validate_on_submit():
        df = query_database(
            query=f"SELECT * FROM statisticsSources WHERE statistics_source_ID={form.statistics_source.data};",
            engine=db.engine,
        )
        if isinstance(df, str):
            message = database_query_fail_statement(df)
            log.error(message)
            flash(message)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        
        statistics_source = StatisticsSources(  # Even with one value, the field of a single-record dataframe is still considered a series, making type juggling necessary
            statistics_source_ID = int(df.at[0,'statistics_source_ID']),
            statistics_source_name = str(df.at[0,'statistics_source_name']),
            statistics_source_retrieval_code = str(df.at[0,'statistics_source_retrieval_code']).split(".")[0],  #String created is of a float (aka `n.0`), so the decimal and everything after it need to be removed
            vendor_ID = int(df.at[0,'vendor_ID']),
        )  # Without the `int` constructors, a numpy int type is used
        log.info(initialize_relation_class_object_statement("StatisticsSources", statistics_source))

        begin_date = form.begin_date.data
        end_date = form.end_date.data
        if form.report_to_harvest.data == 'null':  # All possible responses returned by a select field must be the same data type, so `None` can't be returned
            report_to_harvest = None
            log.debug(f"Preparing to make SUSHI call to statistics source {statistics_source} for the date range {begin_date} to {end_date}.")
        else:
            report_to_harvest = form.report_to_harvest.data
            log.debug(f"Preparing to make SUSHI call to statistics source {statistics_source} for the {report_to_harvest} the date range {begin_date} to {end_date}.")
        
        if testing == "":
            bucket_path = PATH_WITHIN_BUCKET
        elif testing == "test":
            bucket_path = PATH_WITHIN_BUCKET_FOR_TESTS
        else:
            message = f"The dynamic route featured the invalid value {testing}."
            log.error(message)
            flash(message)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        try:
            result_message, flash_messages = statistics_source.collect_usage_statistics(
                begin_date,
                end_date,
                report_to_harvest,
                bucket_path,
            )
            log.info(result_message)
            if [item for sublist in flash_messages.values() for item in sublist]:
                flash(flash_messages)
            else:  # So success message shows instead of a lack of error messages
                flash(result_message)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        except Exception as error:
            message = f"The SUSHI call raised {error}."
            log.warning(message)
            flash(message)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
    else:
        message = Flask_error_statement(form.errors)
        log.error(message)
        flash(message)
        return abort(404)


@bp.route('/upload-non-COUNTER/', defaults={'testing': ""}, methods=['GET', 'POST'])
@bp.route('/upload-non-COUNTER/<string:testing>', methods=['GET', 'POST'])
def upload_non_COUNTER_reports(testing):
    """The route function for uploading files containing non-COUNTER data into the container.

    Args:
        testing (str, optional): an indicator that the route function call is for a test; default is an empty string which indicates POST is for production
    """
    log.info("Starting `upload_non_COUNTER_reports()`.")
    form = UsageFileForm()
    if request.method == 'GET':
        non_COUNTER_files_needed = query_database(
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
        if isinstance(non_COUNTER_files_needed, str):
            flash(database_query_fail_statement(non_COUNTER_files_needed))
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        form.AUCT_option.choices = create_AUCT_SelectField_options(non_COUNTER_files_needed)
        return render_template('ingest_usage/upload-non-COUNTER-usage.html', form=form, testing=testing)
    elif form.validate_on_submit():
        statistics_source_ID, fiscal_year_ID = literal_eval(form.AUCT_option.data) # Since `AUCT_option_choices` had a multiindex, the select field using it returns a tuple
        df = query_database(
            query=f"""
                SELECT
                    annualUsageCollectionTracking.AUCT_statistics_source,
                    annualUsageCollectionTracking.AUCT_fiscal_year,
                    annualUsageCollectionTracking.usage_is_being_collected,
                    annualUsageCollectionTracking.manual_collection_required,
                    annualUsageCollectionTracking.collection_via_email,
                    annualUsageCollectionTracking.is_COUNTER_compliant,
                    annualUsageCollectionTracking.collection_status,
                    annualUsageCollectionTracking.usage_file_path,
                    annualUsageCollectionTracking.notes,
                    statisticsSources.statistics_source_name,
                    fiscalYears.fiscal_year
                FROM annualUsageCollectionTracking
                    JOIN statisticsSources ON statisticsSources.statistics_source_ID=annualUsageCollectionTracking.AUCT_statistics_source
                    JOIN fiscalYears ON fiscalYears.fiscal_year_ID=annualUsageCollectionTracking.AUCT_fiscal_year
                WHERE
                    AUCT_statistics_source={statistics_source_ID}
                    AND AUCT_fiscal_year={fiscal_year_ID};
            """,
            engine=db.engine,
        )
        if isinstance(df, str):
            message = database_query_fail_statement(df)
            log.error(message)
            flash(message)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        AUCT_object = AnnualUsageCollectionTracking(
            AUCT_statistics_source=df.at[0,'AUCT_statistics_source'],
            AUCT_fiscal_year=df.at[0,'AUCT_fiscal_year'],
            usage_is_being_collected=df.at[0,'usage_is_being_collected'],
            manual_collection_required=df.at[0,'manual_collection_required'],
            collection_via_email=df.at[0,'collection_via_email'],
            is_COUNTER_compliant=df.at[0,'is_COUNTER_compliant'],
            collection_status=df.at[0,'collection_status'],
            usage_file_path=df.at[0,'usage_file_path'],
            notes=df.at[0,'notes'],
        )
        log.debug(f"The file being uploaded is {form.usage_file.data} (type {type(form.usage_file.data)}).")
        if testing == "":
            bucket_path = PATH_WITHIN_BUCKET
        elif testing == "test":
            bucket_path = PATH_WITHIN_BUCKET_FOR_TESTS
        else:
            message = f"The dynamic route featured the invalid value {testing}."
            log.error(message)
            flash(message)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        response = AUCT_object.upload_nonstandard_usage_file(form.usage_file.data, bucket_path)
        if upload_nonstandard_usage_file_success_regex().match(response) is None:
            #ToDo: Do any other actions need to be taken?
            log.error(response)
            flash(response)
            return redirect(url_for('ingest_usage.ingest_usage_homepage'))
        message = f"Usage file for {df.at[0, 'statistics_source_name']}--FY {df.at[0, 'fiscal_year']} uploaded successfully."
        log.debug(message)
        flash(message)
        return redirect(url_for('ingest_usage.ingest_usage_homepage'))
    else:
        message = Flask_error_statement(form.errors)
        log.error(message)
        flash(message)
        return abort(404)