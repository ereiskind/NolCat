import logging
from pathlib import Path
import re
from flask import render_template
from flask import redirect
from flask import url_for
from flask import request
from flask import abort
from flask import flash
import pandas as pd

from . import bp
from .forms import *
from ..app import *
from ..models import *
from ..statements import *
from ..upload_COUNTER_reports import UploadCOUNTERReports

log = logging.getLogger(__name__)


#Section: Database Initialization Wizard
@bp.route('/', methods=['GET', 'POST'])
def collect_FY_and_vendor_data():
    """This route function ingests the files containing data going into the `fiscalYears`, `annualStatistics`, `vendors`, and `vendorNotes` relations, then loads that data into the database.
    
    The route function renders the page showing the templates for the `fiscalYears`, `annualStatistics`, `vendors`, and `vendorNotes` relations as well as the form for submitting the completed templates. When the CSVs containing the data for those relations are submitted, the function saves the data by loading it into the database, then redirects to the `collect_sources_data()` route function. The creation of the initial relation CSVs is split into two route functions/pages to split up the instructions and to comply with the limit on the number of files that can be uploaded at once found in most browsers.
    """
    log.info("Starting `collect_FY_and_vendor_data()`.")
    form = FYAndVendorsDataForm()
    if request.method == 'GET':
        return render_template('initialization/index.html', form=form, CWD=str(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'initialization'))
    elif form.validate_on_submit():
        #Section: Ingest Data from Uploaded CSVs
        # For relations containing a record index (primary key) column when loaded, the primary key field name must be identified using the `index_col` keyword argument, otherwise pandas will create an `index` field for an auto-generated record index; this extra field will prevent the dataframe from being loaded into the database.
        # When Excel saves worksheets with non-Latin characters as CSVs, it defaults to UTF-16. The "save as" option "CSV UTF-8", which isn't available in all version of Excel, must be used.
        #ALERT: An error in the encoding statement can cause the logging statement directly above it to not appear in the output
        #Subsection: Upload `fiscalYears` CSV File
        log.debug(f"The `fiscalYears` FileField data:\n{form.fiscalYears_CSV.data}\n")
        fiscalYears_dataframe = pd.read_csv(
            form.fiscalYears_CSV.data,
            index_col='fiscal_year_ID',
            parse_dates=['start_date', 'end_date'],
            date_format='ISO8601',
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        if fiscalYears_dataframe.isnull().all(axis=None) == True:
            log.error("The `fiscalYears` relation data file was read in with no data.")
            return render_template('initialization/empty-dataframes-warning.html', relation="`fiscalYears`")
        
        fiscalYears_dataframe = fiscalYears_dataframe.astype({k: v for (k, v) in FiscalYears.state_data_types().items() if v != "datetime64[ns]"})  # Datetimes are excluded because their data type was set with the `date_format` argument
        log.debug(f"`fiscalYears` dataframe dtypes before encoding conversions:\n{fiscalYears_dataframe.dtypes}\n")
        fiscalYears_dataframe['notes_on_statisticsSources_used'] = fiscalYears_dataframe['notes_on_statisticsSources_used'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        fiscalYears_dataframe['notes_on_corrections_after_submission'] = fiscalYears_dataframe['notes_on_corrections_after_submission'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        log.info(f"`fiscalYears` dataframe:\n{fiscalYears_dataframe}\n")

        #Subsection: Upload `annualStatistics` CSV File
        log.debug(f"The `annualStatistics` FileField data:\n{form.annualStatistics_CSV.data}\n")
        annualStatistics_dataframe = pd.read_csv(
            form.annualStatistics_CSV.data,
            index_col=['fiscal_year_ID', 'question'],
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        if annualStatistics_dataframe.isnull().all(axis=None) == True:
            log.error("The `annualStatistics` relation data file was read in with no data.")
            return render_template('initialization/empty-dataframes-warning.html', relation="`annualStatistics`")
        
        annualStatistics_dataframe = annualStatistics_dataframe.astype({k: v for (k, v) in AnnualStatistics.state_data_types().items()})
        log.debug(f"`annualStatistics` dataframe dtypes before encoding conversions:\n{annualStatistics_dataframe.dtypes}\n")
        annualStatistics_dataframe = annualStatistics_dataframe.reset_index()
        annualStatistics_dataframe['question'] = annualStatistics_dataframe['question'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        annualStatistics_dataframe = annualStatistics_dataframe.set_index(['fiscal_year_ID', 'question'])
        log.info(f"`annualStatistics` dataframe:\n{annualStatistics_dataframe}\n")

        #Subsection: Upload `vendors` CSV File
        log.debug(f"The `vendors` FileField data:\n{form.vendors_CSV.data}\n")
        vendors_dataframe = pd.read_csv(
            form.vendors_CSV.data,
            index_col='vendor_ID',
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        if vendors_dataframe.isnull().all(axis=None) == True:
            log.error("The `vendors` relation data file was read in with no data.")
            return render_template('initialization/empty-dataframes-warning.html', relation="`vendors`")
        
        vendors_dataframe = vendors_dataframe.astype({k: v for (k, v) in Vendors.state_data_types().items()})
        log.debug(f"`vendors` dataframe dtypes before encoding conversions:\n{vendors_dataframe.dtypes}\n")
        vendors_dataframe['vendor_name'] = vendors_dataframe['vendor_name'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        log.info(f"`vendors` dataframe:\n{vendors_dataframe}\n")

        #Subsection: Upload `vendorNotes` CSV File
        log.debug(f"The `vendorNotes` FileField data:\n{form.vendorNotes_CSV.data}\n")
        vendorNotes_dataframe = pd.read_csv(
            form.vendorNotes_CSV.data,
            parse_dates=['date_written'],
            date_format='ISO8601',
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        if vendorNotes_dataframe.isnull().all(axis=None) == True:
            log.error("The `vendorNotes` relation data file was read in with no data.")
            return render_template('initialization/empty-dataframes-warning.html', relation="`vendorNotes`")
        
        vendorNotes_dataframe = vendorNotes_dataframe.astype({k: v for (k, v) in VendorNotes.state_data_types().items() if v != "datetime64[ns]"})  # Datetimes are excluded because their data type was set with the `date_format` argument
        log.debug(f"`vendorNotes` dataframe dtypes before encoding conversions:\n{vendorNotes_dataframe.dtypes}\n")
        vendorNotes_dataframe['note'] = vendorNotes_dataframe['note'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        log.info(f"`vendorNotes` dataframe:\n{vendorNotes_dataframe}\n")


        #Section: Load Data into Database
        data_load_errors = []
        fiscalYears_load_result = load_data_into_database(
            df=fiscalYears_dataframe,
            relation='fiscalYears',
            engine=db.engine,
        )
        if not load_data_into_database_success_regex().fullmatch(fiscalYears_load_result):
            data_load_errors.append(fiscalYears_load_result)
        annualStatistics_load_result = load_data_into_database(
            df=annualStatistics_dataframe,
            relation='annualStatistics',
            engine=db.engine,
        )
        if not load_data_into_database_success_regex().fullmatch(annualStatistics_load_result):
            data_load_errors.append(annualStatistics_load_result)
        vendors_load_result = load_data_into_database(
            df=vendors_dataframe,
            relation='vendors',
            engine=db.engine,
        )
        if not load_data_into_database_success_regex().fullmatch(vendors_load_result):
            data_load_errors.append(vendors_load_result)
        vendorNotes_dataframe.index += first_new_PK_value('vendorNotes')
        vendorNotes_dataframe.index.name = 'vendor_notes_ID'
        vendorNotes_load_result = load_data_into_database(
            df=vendorNotes_dataframe,
            relation='vendorNotes',
            engine=db.engine,
        )
        if not load_data_into_database_success_regex().fullmatch(vendorNotes_load_result):
            data_load_errors.append(vendorNotes_load_result)
        if data_load_errors:
            flash(data_load_errors)
            return redirect(url_for('initialization.collect_FY_and_vendor_data'))
        
        return redirect(url_for('initialization.collect_sources_data'))

    else:
        message = Flask_error_statement(form.errors)
        log.error(message)
        flash(message)
        return abort(404)


@bp.route('/initialization-page-2', methods=['GET', 'POST'])
def collect_sources_data():
    """This route function ingests the files containing data going into the `statisticsSources`, `statisticsSourceNotes`, `resourceSources`, `resourceSourceNotes`, and `statisticsResourceSources` relations, then loads that data into the database.

    The route function renders the page showing the templates for the `statisticsSources`, `statisticsSourceNotes`, `resourceSources`, `resourceSourceNotes`, and `statisticsResourceSources` relations as well as the form for submitting the completed templates. When the CSVs containing the data for those relations are submitted, the function saves the data by loading it into the database, then redirects to the `collect_AUCT_and_historical_COUNTER_data()` route function. The creation of the initial relation CSVs is split into two route functions/pages to split up the instructions and to comply with the limit on the number of files that can be uploaded at once found in most browsers.
    """
    log.info("Starting `collect_sources_data()`.")
    form = SourcesDataForm()
    if request.method == 'GET':
        return render_template('initialization/initial-data-upload-2.html', form=form, CWD=str(TOP_NOLCAT_DIRECTORY / 'nolcat' / 'initialization'))
    elif form.validate_on_submit():
        #Section: Ingest Data from Uploaded CSVs
        #Subsection: Upload `statisticsSources` CSV File
        log.debug(f"The `statisticsSources` FileField data:\n{form.statisticsSources_CSV.data}\n")
        statisticsSources_dataframe = pd.read_csv(
            form.statisticsSources_CSV.data,
            index_col='statistics_source_ID',
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        if statisticsSources_dataframe.isnull().all(axis=None) == True:
            log.error("The `statisticsSources` relation data file was read in with no data.")
            return render_template('initialization/empty-dataframes-warning.html', relation="`statisticsSources`")
        
        statisticsSources_dataframe = statisticsSources_dataframe.astype({k: v for (k, v) in StatisticsSources.state_data_types().items()})
        log.debug(f"`statisticsSources` dataframe dtypes before encoding conversions:\n{statisticsSources_dataframe.dtypes}\n")
        statisticsSources_dataframe['statistics_source_name'] = statisticsSources_dataframe['statistics_source_name'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        log.info(f"`statisticsSources` dataframe:\n{statisticsSources_dataframe}\n")

        #Subsection: Upload `statisticsSourceNotes` CSV File
        log.debug(f"The `statisticsSourceNotes` FileField data:\n{form.statisticsSourceNotes_CSV.data}\n")
        statisticsSourceNotes_dataframe = pd.read_csv(
            form.statisticsSourceNotes_CSV.data,
            encoding='utf-8',
            parse_dates=['date_written'],
            date_format='ISO8601',
            encoding_errors='backslashreplace',
        )
        if statisticsSourceNotes_dataframe.isnull().all(axis=None) == True:
            log.error("The `statisticsSourceNotes` relation data file was read in with no data.")
            return render_template('initialization/empty-dataframes-warning.html', relation="`statisticsSourceNotes`")
        
        statisticsSourceNotes_dataframe = statisticsSourceNotes_dataframe.astype({k: v for (k, v) in StatisticsSourceNotes.state_data_types().items() if v != "datetime64[ns]"})  # Datetimes are excluded because their data type was set with the `date_format` argument
        log.debug(f"`statisticsSourceNotes` dataframe dtypes before encoding conversions:\n{statisticsSourceNotes_dataframe.dtypes}\n")
        statisticsSourceNotes_dataframe['note'] = statisticsSourceNotes_dataframe['note'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        log.info(f"`statisticsSourceNotes` dataframe:\n{statisticsSourceNotes_dataframe}\n")

        #Subsection: Upload `resourceSources` CSV File
        log.debug(f"The `resourceSources` FileField data:\n{form.resourceSources_CSV.data}\n")
        resourceSources_dataframe = pd.read_csv(
            form.resourceSources_CSV.data,
            index_col='resource_source_ID',
            parse_dates=['access_stop_date'],
            date_format='ISO8601',
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        if resourceSources_dataframe.isnull().all(axis=None) == True:
            log.error("The `resourceSources` relation data file was read in with no data.")
            return render_template('initialization/empty-dataframes-warning.html', relation="`resourceSources`")
        
        resourceSources_dataframe = resourceSources_dataframe.astype({k: v for (k, v) in ResourceSources.state_data_types().items() if v != "datetime64[ns]"})  # Datetimes are excluded because their data type was set with the `date_format` argument
        log.debug(f"`resourceSources` dataframe dtypes before encoding conversions:\n{resourceSources_dataframe.dtypes}\n")
        resourceSources_dataframe['resource_source_name'] = resourceSources_dataframe['resource_source_name'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        log.info(f"`resourceSources` dataframe:\n{resourceSources_dataframe}\n")

        #Subsection: Upload `resourceSourceNotes` CSV File
        log.debug(f"The `resourceSourceNotes` FileField data:\n{form.resourceSourceNotes_CSV.data}\n")
        resourceSourceNotes_dataframe = pd.read_csv(
            form.resourceSourceNotes_CSV.data,
            parse_dates=['date_written'],
            date_format='ISO8601',
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        if resourceSourceNotes_dataframe.isnull().all(axis=None) == True:
            log.error("The `resourceSourceNotes` relation data file was read in with no data.")
            return render_template('initialization/empty-dataframes-warning.html', relation="`resourceSourceNotes`")
        
        resourceSourceNotes_dataframe = resourceSourceNotes_dataframe.astype({k: v for (k, v) in ResourceSourceNotes.state_data_types().items() if v != "datetime64[ns]"})  # Datetimes are excluded because their data type was set with the `date_format` argument
        log.debug(f"`resourceSourceNotes` dataframe dtypes before encoding conversions:\n{resourceSourceNotes_dataframe.dtypes}\n")
        resourceSourceNotes_dataframe['note'] = resourceSourceNotes_dataframe['note'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        log.info(f"`resourceSourceNotes` dataframe:\n{resourceSourceNotes_dataframe}\n")

        #Subsection: Upload `statisticsResourceSources` CSV File
        log.debug(f"The `statisticsResourceSources` FileField data:\n{form.statisticsResourceSources_CSV.data}\n")
        statisticsResourceSources_dataframe = pd.read_csv(
            form.statisticsResourceSources_CSV.data,
            index_col=['SRS_statistics_source', 'SRS_resource_source'],
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        if statisticsResourceSources_dataframe.isnull().all(axis=None) == True:
            log.error("The `statisticsResourceSources` relation data file was read in with no data.")
            return render_template('initialization/empty-dataframes-warning.html', relation="`statisticsResourceSources`")
        
        # Because there aren't any string dtypes in need of encoding correction, the logging statements for the dtypes and the dataframe have been combined
        log.info(f"`statisticsResourceSources` dtypes and dataframe:\n{statisticsResourceSources_dataframe.dtypes}\n{statisticsResourceSources_dataframe}\n")


        #Section: Load Data into Database
        data_load_errors = []
        statisticsSources_load_result = load_data_into_database(
            df=statisticsSources_dataframe,
            relation='statisticsSources',
            engine=db.engine,
        )
        if not load_data_into_database_success_regex().fullmatch(statisticsSources_load_result):
            data_load_errors.append(statisticsSources_load_result)
        statisticsSourceNotes_dataframe.index += first_new_PK_value('statisticsSourceNotes')
        statisticsSourceNotes_dataframe.index.name = 'statistics_source_notes_ID'
        statisticsSourceNotes_load_result = load_data_into_database(
            df=statisticsSourceNotes_dataframe,
            relation='statisticsSourceNotes',
            engine=db.engine,
        )
        if not load_data_into_database_success_regex().fullmatch(statisticsSourceNotes_load_result):
            data_load_errors.append(statisticsSourceNotes_load_result)
        resourceSources_load_result = load_data_into_database(
            df=resourceSources_dataframe,
            relation='resourceSources',
            engine=db.engine,
        )
        if not load_data_into_database_success_regex().fullmatch(resourceSources_load_result):
            data_load_errors.append(resourceSources_load_result)
        resourceSourceNotes_dataframe.index += first_new_PK_value('resourceSourceNotes')
        resourceSourceNotes_dataframe.index.name = 'resource_source_notes_ID'
        resourceSourceNotes_load_result = load_data_into_database(
            df= resourceSourceNotes_dataframe,
            relation='resourceSourceNotes',
            engine=db.engine,
        )
        if not load_data_into_database_success_regex().fullmatch(resourceSourceNotes_load_result):
            data_load_errors.append(resourceSourceNotes_load_result)
        statisticsResourceSources_load_result = load_data_into_database(
            df=statisticsResourceSources_dataframe,
            relation='statisticsResourceSources',
            engine=db.engine,
        )
        if not load_data_into_database_success_regex().fullmatch(statisticsResourceSources_load_result):
            data_load_errors.append(statisticsResourceSources_load_result)
        if data_load_errors:
            flash(data_load_errors)
            return redirect(url_for('initialization.collect_sources_data'))
        
        return redirect(url_for('initialization.collect_AUCT_and_historical_COUNTER_data'))

    else:
        message = Flask_error_statement(form.errors)
        log.error(message)
        flash(message)
        return abort(404)


@bp.route('/initialization-page-3', methods=['GET', 'POST'])
def collect_AUCT_and_historical_COUNTER_data():
    """This route function creates the template for the `annualUsageCollectionTracking` relation and lets the user download it, then lets the user upload the `annualUsageCollectionTracking` relation data and the historical COUNTER reports into the database.

    Upon redirect, this route function renders the page for downloading the template for the `annualUsageCollectionTracking` relation and the form to upload that filled-out template and any tabular R4 and R5 COUNTER reports. When the `annualUsageCollectionTracking` relation and COUNTER reports are submitted, the function saves the `annualUsageCollectionTracking` relation data by loading it into the database, then processes the COUNTER reports by transforming them into a dataframe with `UploadCOUNTERReports.create_dataframe()` and loading the resulting dataframe into the database.
    """
    log.info("Starting `collect_AUCT_and_historical_COUNTER_data()`.")
    form = AUCTAndCOUNTERForm()
    
    #Section: Before Page Renders
    if request.method == 'GET':  # `POST` goes to HTTP status code 302 because of `redirect`, subsequent 200 is a GET
        #Subsection: Get Cartesian Product of `fiscalYears` and `statisticsSources` Primary Keys via Database Query
        df = query_database(
            query="SELECT statisticsSources.statistics_source_ID, fiscalYears.fiscal_year_ID, statisticsSources.statistics_source_name, fiscalYears.fiscal_year FROM statisticsSources JOIN fiscalYears ORDER BY statisticsSources.statistics_source_ID, fiscalYears.fiscal_year_ID;",  # The ORDER BY keeps the indexes in order for testing
            engine=db.engine,
            index=["statistics_source_ID", "fiscal_year_ID"],
        )
        if isinstance(df, str):
            message = database_query_fail_statement(df)
            log.error(message)
            flash(message)
            return redirect(url_for('initialization.collect_FY_and_vendor_data'))
        log.debug(return_dataframe_from_query_statement("the AUCT Cartesian product dataframe", df))

        #Subsection: Create `annualUsageConnectionTracking` Relation Template File
        df = df.rename_axis(index={
            "statistics_source_ID": "AUCT_statistics_source",
            "fiscal_year_ID": "AUCT_fiscal_year",
        })
        df = df.rename(columns={
            "statistics_source_name": "Statistics Source",
            "fiscal_year": "Fiscal Year",
        })
        log.debug(f"`annualUsageCollectionTracking` dataframe with fields renamed:\n{df}")

        df['usage_is_being_collected'] = None
        df['manual_collection_required'] = None
        df['collection_via_email'] = None
        df['is_COUNTER_compliant'] = None
        df['collection_status'] = None
        df['usage_file_path'] = None
        df['notes'] = None
        log.info(f"`annualUsageCollectionTracking` template dataframe:\n{df}")

        template_save_location = TOP_NOLCAT_DIRECTORY / 'nolcat' / 'initialization' / 'initialize_annualUsageCollectionTracking.csv'
        try:
            df.to_csv(
                template_save_location,
                index_label=["AUCT_statistics_source", "AUCT_fiscal_year"],
                encoding='utf-8',
                errors='backslashreplace',  # For encoding errors
            )
            log.debug(f"Successfully created `annualUsageCollectionTracking` relation template CSV at {template_save_location}.")
        except Exception as error:
            log.error(f"Creating the `annualUsageCollectionTracking` relation template CSV raised the error {error}.")
            if infinite_loop_error in locals():  # This is triggered the second time this code block is reached
                message = "Multiple attempts to create the AUCT template CSV have failed. Please try uploading the `statisticsSources`, `statisticsSourceNotes`, `resourceSources`, `resourceSourceNotes`, and `statisticsResourceSources` relations again."
                log.error(message)
                for relation in ['statisticsSources', 'statisticsSourceNotes', 'resourceSources', 'resourceSourceNotes', 'statisticsResourceSources']:
                    update_result = update_database(
                        update_statement=f"Truncate {relation};",
                        engine=db.engine,
                    )
                    if not update_database_success_regex().fullmatch(update_result):
                        message = f"Multiple problems of unclear origin have occurred in the process of attempting to initialize the database. Please truncate all relations via the SQL command line and restart the initialization wizard."
                        log.critical(message)
                        flash(message)
                        return redirect(url_for('initialization.collect_FY_and_vendor_data'))
                flash(message)
                return redirect(url_for('initialization.collect_sources_data'))
            infinite_loop_error = True
            return render_template('initialization/initial-data-upload-3.html', form=form)  # This will restart the route function
        
        return render_template('initialization/initial-data-upload-3.html', form=form, AUCT_file_path=str(template_save_location))

    #Section: After Form Submission
    elif form.validate_on_submit():
        if 'template_save_location' in locals():  # Submitting the form calls the function again, so the initialized variable isn't saved
            template_save_location.unlink(missing_ok=True)
        #Subsection: Ingest `annualUsageCollectionTracking` Data
        log.debug(f"The `annualUsageCollectionTracking` FileField data: {form.annualUsageCollectionTracking_CSV.data}")
        AUCT_dataframe = pd.read_csv(
            form.annualUsageCollectionTracking_CSV.data,
            index_col=['AUCT_statistics_source', 'AUCT_fiscal_year'],
            encoding='utf-8',
            encoding_errors='backslashreplace',
        )
        if AUCT_dataframe.isnull().all(axis=None) == True:
            log.error("The `annualUsageCollectionTracking` relation data file was read in with no data.")
            return render_template('initialization/empty-dataframes-warning.html', relation="`annualUsageCollectionTracking`")
        
        AUCT_dataframe = AUCT_dataframe.astype({k: v for (k, v) in AnnualUsageCollectionTracking.state_data_types().items()})
        log.debug(f"`annualUsageCollectionTracking` dataframe dtypes before encoding conversions:\n{AUCT_dataframe.dtypes}\n")
        AUCT_dataframe['usage_file_path'] = AUCT_dataframe['usage_file_path'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        AUCT_dataframe['notes'] = AUCT_dataframe['notes'].apply(lambda value: value if pd.isnull(value) == True else value.encode('utf-8').decode('unicode-escape'))
        log.info(f"`annualUsageCollectionTracking` dataframe:\n{AUCT_dataframe}\n")

        #Subsection: Ingest COUNTER Reports
        messages_to_flash = []
        if len(form.COUNTER_reports.data) == 0 or form.COUNTER_reports.data[0].filename == "":  # In tests, not submitting forms is done with an empty list, so an empty list is returned; in production, an empty FileStorage object is returned instead
            log.info(f"No COUNTER files were provided for upload.")
            COUNTER_reports_df = None
        else:
            try:
                COUNTER_reports_df, data_not_in_df = UploadCOUNTERReports(form.COUNTER_reports.data).create_dataframe()  # `form.COUNTER_reports.data` is a list of <class 'werkzeug.datastructures.FileStorage'> objects
                COUNTER_reports_df['report_creation_date'] = pd.to_datetime(None)
                if data_not_in_df:
                    messages_to_flash.append(f"The following worksheets and workbooks weren't included in the loaded data:\n{format_list_for_stdout(data_not_in_df)}")
            except Exception as error:
                message = unable_to_convert_SUSHI_data_to_dataframe_statement(error)
                log.error(message)
                flash(message)
                return redirect(url_for('initialization.collect_AUCT_and_historical_COUNTER_data'))
            log.debug(f"`COUNTERData` data:\n{COUNTER_reports_df}\n")

            try:
                COUNTER_reports_df, message_to_flash = check_if_data_already_in_COUNTERData(COUNTER_reports_df)
            except Exception as error:
                message = f"The uploaded data wasn't added to the database because the check for possible duplication raised {error}."
                log.error(message)
                flash(message)
                return redirect(url_for('initialization.collect_AUCT_and_historical_COUNTER_data'))
            if COUNTER_reports_df is None:
                flash(message_to_flash)
                return redirect(url_for('initialization.collect_AUCT_and_historical_COUNTER_data'))
            if message_to_flash:
                messages_to_flash.append(message_to_flash)
            
            try:
                COUNTER_reports_df.index += first_new_PK_value('COUNTERData')
            except Exception as error:
                message = unable_to_get_updated_primary_key_values_statement("COUNTERData", error)
                log.warning(message)
                messages_to_flash.append(message)
                flash(messages_to_flash)
                return redirect(url_for('initialization.collect_AUCT_and_historical_COUNTER_data'))
            log.info(f"Sample of data to load into `COUNTERData` dataframe:\n{COUNTER_reports_df.head()}\n...\n{COUNTER_reports_df.tail()}\n")
            log.debug(f"Data to load into `COUNTERData` dataframe:\n{COUNTER_reports_df}\n")

        #Subsection: Load Data into Database
        annualUsageCollectionTracking_load_result = load_data_into_database(
            df=AUCT_dataframe,
            relation='annualUsageCollectionTracking',
            engine=db.engine,
            index_field_name=['AUCT_statistics_source', 'AUCT_fiscal_year'],
        )
        if not load_data_into_database_success_regex().fullmatch(annualUsageCollectionTracking_load_result):
            messages_to_flash.append(annualUsageCollectionTracking_load_result)
            flash(messages_to_flash)
            return redirect(url_for('initialization.collect_AUCT_and_historical_COUNTER_data'))
        if COUNTER_reports_df is not None:  # `is not None` required--when `COUNTER_reports_df` is a dataframe, error about ambiguous truthiness of dataframes raised
            COUNTERData_load_result = load_data_into_database(
                df=COUNTER_reports_df,
                relation='COUNTERData',
                engine=db.engine,
                index_field_name='COUNTER_data_ID',
            )
            if not load_data_into_database_success_regex().fullmatch(COUNTERData_load_result):
                messages_to_flash.append(COUNTERData_load_result)
        if messages_to_flash:
            flash(messages_to_flash)
        return redirect(url_for('initialization.upload_historical_non_COUNTER_usage'))

    else:
        message = Flask_error_statement(form.errors)
        log.error(message)
        flash(message)
        return abort(404)


@bp.route('/initialization-page-4/', defaults={'testing': ""}, methods=['GET', 'POST'])
@bp.route('/initialization-page-4/<string:testing>', methods=['GET', 'POST'])
def upload_historical_non_COUNTER_usage(testing):
    """This route function allows the user to upload files containing non-COUNTER usage reports to the container hosting this program, placing the file paths within the COUNTER usage statistics database for easy retrieval in the future.
    
    The route function renders the page showing a form with a field for uploading a file for each non-COUNTER `annualUsageCollectionTracking` record. When the files containing the non-COUNTER data are submitted, the function saves the data by changing the file name, saving the file to S3, and saving the file name to the `annualUsageCollectionTracking.usage_file_path` field of the given record, then redirects to the `data_load_complete()` route function.

    Args:
        testing (str, optional): an indicator that the route function call is for a test; default is an empty string which indicates POST is for production
    """
    log.info("Starting `upload_historical_non_COUNTER_usage()`.")
    form = HistoricalNonCOUNTERForm()
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
            return redirect(url_for('initialization.data_load_complete'))
        list_of_non_COUNTER_usage = create_AUCT_SelectField_options(non_COUNTER_files_needed)
        form = HistoricalNonCOUNTERForm(usage_files = [{"usage_file": non_COUNTER_usage[1]} for non_COUNTER_usage in list_of_non_COUNTER_usage])
        return render_template('initialization/initial-data-upload-4.html', form=form, testing=testing)
    elif form.validate_on_submit():
        flash_error_messages = dict()
        files_submitted_for_upload = len(form.usage_files.data)
        files_uploaded = 0
        for file in form.usage_files.data:
            if file['usage_file']:
                log.debug(f"Processing the file {file['usage_file']} for upload.")
                try:
                    statistics_source_ID, fiscal_year = non_COUNTER_file_name_regex().fullmatch(file['usage_file'].filename).group(1, 2)
                except Exception as error:
                    message = f"Unable to get query filter data from file name because {error[0].lower()}{error[1:]}"
                    log.warning(message)
                    flash_error_messages[file['usage_file'].filename] = message
                    continue
                df = query_database(
                    query=f"""
                        SELECT
                            annualUsageCollectionTracking.AUCT_statistics_source,
                            fiscalYears.fiscal_year_ID,
                            annualUsageCollectionTracking.usage_is_being_collected,
                            annualUsageCollectionTracking.manual_collection_required,
                            annualUsageCollectionTracking.collection_via_email,
                            annualUsageCollectionTracking.is_COUNTER_compliant,
                            annualUsageCollectionTracking.collection_status,
                            annualUsageCollectionTracking.usage_file_path,
                            annualUsageCollectionTracking.notes
                        FROM annualUsageCollectionTracking
                        JOIN fiscalYears ON fiscalYears.fiscal_year_ID=annualUsageCollectionTracking.AUCT_fiscal_year
                        WHERE
                            annualUsageCollectionTracking.AUCT_statistics_source={statistics_source_ID} AND
                            fiscalYears.fiscal_year='{fiscal_year}';
                    """,
                    engine=db.engine,
                )
                if isinstance(df, str):
                    message = database_query_fail_statement(df, f"upload the usage file for statistics_source_ID {statistics_source_ID} and fiscal year {fiscal_year}")
                    log.error(message)
                    flash_error_messages[file['usage_file'].filename] = message
                    continue
                AUCT_object = AnnualUsageCollectionTracking(
                    AUCT_statistics_source=df.at[0,'AUCT_statistics_source'],
                    AUCT_fiscal_year=df.at[0,'fiscal_year_ID'],
                    usage_is_being_collected=df.at[0,'usage_is_being_collected'],
                    manual_collection_required=df.at[0,'manual_collection_required'],
                    collection_via_email=df.at[0,'collection_via_email'],
                    is_COUNTER_compliant=df.at[0,'is_COUNTER_compliant'],
                    collection_status=df.at[0,'collection_status'],
                    usage_file_path=df.at[0,'usage_file_path'],
                    notes=df.at[0,'notes'],
                )
                log.info(initialize_relation_class_object_statement("AnnualUsageCollectionTracking", AUCT_object))
                if testing == "":
                    bucket_path = PATH_WITHIN_BUCKET
                elif testing == "test":
                    bucket_path = PATH_WITHIN_BUCKET_FOR_TESTS
                else:
                    message = f"The dynamic route featured the invalid value {testing}."
                    log.error(message)
                    flash(message)
                    return redirect(url_for('initialization.upload_historical_non_COUNTER_usage'))
                response = AUCT_object.upload_nonstandard_usage_file(file['usage_file'], bucket_path)
                if upload_nonstandard_usage_file_success_regex().fullmatch(response):
                    log.debug(response)
                    files_uploaded += 1
                elif re.fullmatch(r"Successfully loaded the file .+ into the .+ S3 bucket, but updating the .+ relation automatically failed, so the SQL update statement needs to be submitted via the SQL command line:\n.+", response, flags=re.DOTALL):
                    log.warning(response)
                    flash_error_messages[file['usage_file'].filename] = response
                else:
                    log.warning(response)
                    flash_error_messages[file['usage_file'].filename] = response
        log.info(f"Successfully uploaded {files_uploaded} of {files_submitted_for_upload}files.")
        return redirect(url_for('initialization.data_load_complete'))
    else:
        message = Flask_error_statement(form.errors)
        log.error(message)
        flash(message)
        return abort(404)


@bp.route('/initialization-page-5', methods=['GET', 'POST'])
def data_load_complete():
    """This route function indicates the successful completion of the wizard and initialization of the database."""
    return render_template('initialization/show-loaded-data.html')