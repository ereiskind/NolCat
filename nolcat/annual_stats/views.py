import logging
from flask import render_template
from flask import request
from flask import abort
from flask import redirect
from flask import url_for
from flask import flash
import pandas as pd

from . import bp
from .forms import *
from ..app import *
from ..models import *
from ..statements import *

log = logging.getLogger(__name__)


@bp.route('/', methods=['GET', 'POST'])
def annual_stats_homepage():
    """Returns the homepage for the `annual_stats` blueprint, which serves as a homepage for administrative functions."""
    log.info("Starting `annual_stats_homepage()`.")
    form = ChooseFiscalYearForm()
    if request.method == 'GET':
        # The links to the lists of vendors, resource sources, and statistics sources are standard jinja redirects; the code for populating the lists from the underlying relations is in the route functions being redirected to
        fiscal_year_options = query_database(
            query="SELECT fiscal_year_ID, fiscal_year FROM fiscalYears;",
            engine=db.engine,
        )
        if isinstance(fiscal_year_options, str):
            message = database_query_fail_statement(fiscal_year_options)
            log.error(message)
            flash(message)
            return redirect(url_for('annual_stats.annual_stats_homepage'))
        form.fiscal_year.choices = list(fiscal_year_options.itertuples(index=False, name=None))
        return render_template('annual_stats/index.html', form=form)
    elif form.validate_on_submit():
        return redirect(url_for('annual_stats.show_fiscal_year_details', PK=int(form.fiscal_year.data)))
    else:
        message = Flask_error_statement(form.errors)
        log.error(message)
        flash(message)
        return abort(404)


@bp.route('/view_year/<int:PK>', methods=['GET', 'POST'])
def show_fiscal_year_details(PK):
    """Returns a page that shows the information about and the statistics collection status for the fiscal year.

    Args:
        PK (int): the primary key of the record being viewed
    """
    log.info(f"Starting `show_fiscal_year_details()` for the FY with the PK {PK}.")
    #ToDo: `FiscalYears.collect_fiscal_year_usage_statistics()` runs from here
    #ToDo: `AnnualUsageCollectionTracking.collect_annual_usage_statistics()` runs from here
    #ToDo: `AnnualStatistics.add_annual_statistic_value()` runs from here
    run_annual_stats_methods_form = RunAnnualStatsMethodsForm()
    edit_fiscalYear_form = EditFiscalYearForm()
    edit_annualStatistics_form = EditAnnualStatisticsForm()
    edit_AUCT_form = EditAUCTForm()
    #ToDo: is the best way to run `FiscalYears.create_usage_tracking_records_for_fiscal_year()` also a form?
    if request.method == 'GET':
        fiscal_year_details = query_database(
            query=f"SELECT * FROM fiscalYears WHERE fiscal_year_ID={PK};",
            engine=db.engine,
        )
        if isinstance(fiscal_year_details, str):
            flash(database_query_fail_statement(fiscal_year_details))
            return redirect(url_for('annual_stats.annual_stats_homepage'))
        fiscal_year_details = fiscal_year_details.astype(FiscalYears.state_data_types())
        #ToDo: Pass `fiscal_year_details` single-record dataframe to page for display
        fiscal_year_reporting = query_database(
            query=f"SELECT * FROM annualUsageCollectionTracking WHERE AUCT_fiscal_year={PK};",
            engine=db.engine,
            index='AUCT_statistics_source',
        )
        if isinstance(fiscal_year_reporting, str):
            flash(database_query_fail_statement(fiscal_year_reporting))
            return redirect(url_for('annual_stats.annual_stats_homepage'))
        fiscal_year_reporting = fiscal_year_reporting.astype(AnnualUsageCollectionTracking.state_data_types())
        #ToDo: Pass `fiscal_year_reporting` dataframe to page for display
        return render_template('annual_stats/fiscal-year-details.html', run_annual_stats_methods_form=run_annual_stats_methods_form, edit_fiscalYear_form=edit_fiscalYear_form, edit_AUCT_form=edit_AUCT_form)
    elif run_annual_stats_methods_form.validate_on_submit():
        #ToDo: if run_annual_stats_methods_form.annual_stats_method.data is the number for `calculate_depreciated_ACRL_60b()`:
            #ToDo: Flash result of `PK.calculate_depreciated_ACRL_60b()`
            return redirect(url_for('annual_stats.show_fiscal_year_details'))
        #ToDo: if run_annual_stats_methods_form.annual_stats_method.data is the number for `calculate_depreciated_ACRL_63()`:
            #ToDo: Flash result of `PK.calculate_depreciated_ACRL_63()`
            return redirect(url_for('annual_stats.show_fiscal_year_details'))
        #ToDo: if run_annual_stats_methods_form.annual_stats_method.data is the number for `calculate_ACRL_61a()`:
            #ToDo: Flash result of `PK.calculate_ACRL_61a()`
            return redirect(url_for('annual_stats.show_fiscal_year_details'))
        #ToDo: if run_annual_stats_methods_form.annual_stats_method.data is the number for `calculate_ACRL_61b()`:
            #ToDo: Flash result of `PK.calculate_ACRL_61b()`
            return redirect(url_for('annual_stats.show_fiscal_year_details'))
        #ToDo: if run_annual_stats_methods_form.annual_stats_method.data is the number for `calculate_ARL_18()`:
            #ToDo: Flash result of `PK.calculate_ARL_18()`
            return redirect(url_for('annual_stats.show_fiscal_year_details'))
        #ToDo: if run_annual_stats_methods_form.annual_stats_method.data is the number for `calculate_ARL_19()`:
            #ToDo: Flash result of `PK.calculate_ARL_19()`
            return redirect(url_for('annual_stats.show_fiscal_year_details'))
        #ToDo: if run_annual_stats_methods_form.annual_stats_method.data is the number for `calculate_ARL_20()`:
            #ToDo: Flash result of `PK.calculate_ARL_20()`
            return redirect(url_for('annual_stats.show_fiscal_year_details'))
    elif edit_fiscalYear_form.validate_on_submit():
        #ToDo: Upload change to `fiscalYears` relation
        #ToDo: Set up message flashing that change was made
        return redirect(url_for('annual_stats.show_fiscal_year_details'))
    elif edit_AUCT_form.validate_on_submit():
        #ToDo: Upload change to `annualUsageCollectionTracking` relation
        #ToDo: Set up message flashing that change was made
        return redirect(url_for('annual_stats.show_fiscal_year_details'))
    elif edit_annualStatistics_form.validate_on_submit():
        #ToDo: Pass submitted values to `AnnualStatistics.add_annual_statistic_value()`
        #ToDo: Set up message flashing that change was made
        return redirect(url_for('annual_stats.show_fiscal_year_details'))
    else:
        if run_annual_stats_methods_form.errors:
            message = Flask_error_statement(run_annual_stats_methods_form.errors)
        elif edit_fiscalYear_form.errors:
            message = Flask_error_statement(edit_fiscalYear_form.errors)
        elif edit_AUCT_form.errors:
            message = Flask_error_statement(edit_AUCT_form.errors)
        else:
            message = "The page was reached with a POST request, and the forms on the page neither validated themselves on submission nor returned error values."
        log.error(message)
        flash(message)
        return abort(404)