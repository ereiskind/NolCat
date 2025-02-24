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


@bp.route('/<string:list>')
def view_lists_homepage(list):
    """Returns the homepage for the `view_lists` blueprint, which shows the list of resource sources, statistics sources, or vendors depending on the variable route value.

    Args:
        list (str): the relation whose records are being listed
    """
    log.info(f"Starting `view_lists_homepage()` for {list}.")
    #TEST: temp
    try:
        log.warning(f"`list.__dict__`:\n{list.__dict__}")
    except:
        pass
    try:
        log.warning(f"`list.dir()`:\n{list.dir()}")
    except:
        pass
    try:
        log.warning(f"`list.var()`:\n{list.var()}")
    except:
        pass
    #TEST: end temp
    if list == "resources":
        title = "Resource Sources"
        SQL_query = f"""
            SELECT
                resourceSources.resource_source_ID AS ID,
                resourceSources.resource_source_name,
                resourceSources.source_in_use,
                resourceSources.access_stop_date,
                vendors.vendor_name
            FROM resourceSources
                JOIN vendors ON resourceSources.vendor_ID=vendors.vendor_ID
            ORDER BY resourceSources.resource_source_name;
        """
        df = query_database(
            query=SQL_query,
            engine=db.engine,
        )
        if isinstance(df, str):
            message = database_query_fail_statement(df)
            log.error(message)
            flash(message)
            return redirect(url_for('view_lists.view_lists_homepage'))
        df = df.astype({
            **{k: v for (k, v) in COUNTERData.state_data_types().items() if k in df.columns.tolist()},
            "ID": 'int',
        })
        df['source_in_use'] = restore_boolean_values_to_boolean_field(df['source_in_use'])
    elif list == "statistics":
        title = "Statistics Sources"
        SQL_query = f"""
            SELECT
                statisticsSources.statistics_source_ID AS ID,
                statisticsSources.statistics_source_name,
                vendors.vendor_name
            FROM statisticsSources
                JOIN vendors ON statisticsSources.vendor_ID=vendors.vendor_ID
            ORDER BY statisticsSources.statistics_source_name;
        """
        df = query_database(
            query=SQL_query,
            engine=db.engine,
        )
        if isinstance(df, str):
            message = database_query_fail_statement(df)
            log.error(message)
            flash(message)
            return redirect(url_for('view_lists.view_lists_homepage'))
        df = df.astype({
            **{k: v for (k, v) in COUNTERData.state_data_types().items() if k in df.columns.tolist()},
            "ID": 'int',
        })
    elif list == "vendors":
        title = "Vendors"
        SQL_query = f"""
            SELECT
                vendor_ID AS ID,
                vendor_name
            FROM vendors
            ORDER BY vendor_name;
        """
        df = query_database(
            query=SQL_query,
            engine=db.engine,
        )
        if isinstance(df, str):
            message = database_query_fail_statement(df)
            log.error(message)
            flash(message)
            return redirect(url_for('view_lists.view_lists_homepage'))
        df = df.astype({
            **{k: v for (k, v) in COUNTERData.state_data_types().items() if k in df.columns.tolist()},
            "ID": 'int',
        })
    else:
        message = f"`{list}` is not a valid list option."
        log.error(message)
        flash(message)
        return abort(404)
    
    df['View Record Details'] = df['ID'].apply(lambda cell_value: (list, cell_value))
    df['Edit'] = df['ID'].apply(lambda cell_value: (list, cell_value))
    log.info(f"List of {list} as dataframe:\n{df}")
    return render_template(
        'view_lists/index.html',
        title=title,
        fields=[field_name.replace("_", " ").title() for field_name in df.columns.values.tolist() if field_name != "ID"],
        records=[field_values[1:] for field_values in df.values.tolist()],
        zip=zip,
    )


@bp.route('/<string:list>/<int:PK>')
def view_list_record(list, PK):
    """Returns the details and notes about a statistics source, resource source, or vendor.

    For a given record in the `resourceSources`, `statisticsSources`, or `vendors` relations, the value of all of the relation's fields and the notes are shown. For vendor records, the currently affiliated resource sources and statistics sources are shown as well. From this page, notes can be added, but not edited or deleted.

    Args:
        list (str): the relation the record comes from
        PK (int): the primary key of the record being viewed
    """
    log.info(f"Starting `view_list_record()` for {list}.")
    #ToDo: form = Write form for adding notes
    if request.method == 'GET':
        # df = query_database(
        #     query=#ToDo:Write query returning all fields in human-understandable data and notes (and statistics and resource sources if a vendor) for the record with primary key `PK` in the relation indicated by `list`,
        #     engine=db.engine,
        # )
        #ToDo: df = df.astype({dict setting correct dtypes})
        return "render_template('view_lists/view-record.html', form=form)"
    # elif form.validate_on_submit():
        #ToDo: Run one of the methods below based on the list type
            # Vendors.add_note()
            # StatisticsSources.add_note()
            # ResourceSources.add_note()
        return redirect(url_for('view_lists.view_list_record', list=list, PK=PK))
    else:
        #message = Flask_error_statement(form.errors)
        #log.error(message)
        #flash(message)
        return abort(404)
    


@bp.route('/edit/<string:list>/<int:PK>')
def edit_list_record(list, PK):
    """Returns a page for editing records in the `resourceSources`, `statisticsSources`, or `vendors` relations.

    Adding a record is done by creating a `PK` value that matches what's next in the auto-generated count list, adding new values to all the fields available for edit, which are then committed to the relation as a new record. Editing the `resourceSources` relation is also the method for updating the `statisticsResourceSources` junction table, which is never directly visible or directly accessed.

    Args:
        list (str): the relation the record comes from
        PK (int): the primary key of the record being edited
    """
    log.info(f"Starting `edit_list_record()` for {list}.")
    #ToDo: Write form for adding/editing record and for adding or editing notes
    if request.method == 'GET':
        #ToDo: if request came from adding new record link/PK not in relation:
            #ToDo: Show page without prefilled values
            return "render_template('view_lists/edit-record.html', form=form)"
        #ToDo: if `PK` is in the relation
            # df = query_database(
            #     query=#ToDo:Write query returning all fields in human-understandable data and notes (and statistics and resource sources if a vendor) for the record with primary key `PK` in the relation indicated by `list`,
            #     engine=db.engine,
            # )
            # if isinstance(df, str):
            #     message = database_query_fail_statement(df)
            #     log.error(message)
            #     flash(message)
            #     return redirect(url_for(view_lists.view_lists_homepage))
            # df = df.astype({dict setting correct dtypes})
            #ToDo: Prepopulate the fields
                # https://stackoverflow.com/q/35892144
                # https://stackoverflow.com/q/23712986
                # https://stackoverflow.com/q/42984453
                # https://stackoverflow.com/q/28941504
        # return render_template('view_lists/page.html', form=form)
    # elif form.validate_on_submit():
        #ToDo: add_access_stop_date()
        #ToDo: remove_access_stop_date()
        #ToDo: change_StatisticsSource()
            #ToDo: Above has a statistics source PK as its argument--provide a drop-down of names of all statistics sources via "if stats source changes, pick new one here" drop-down listing on a resource source details page which triggers this method
        #ToDo: Use `update_database()` as necessary for any other edits
        #ToDo: Add message flashing about successful upload
        # return redirect(url_for('view_lists.view_list_record', list=list, PK=PK))  
    else:
        #message = Flask_error_statement(form.errors)
        #log.error(message)
        #flash(message)
        return abort(404)