from datetime import timedelta
from django.template import defaultfilters as filters
from django.utils.timezone import localtime

from panopuppet.pano.puppetdb.pdbutils import json_to_datetime, is_unreported
from panopuppet.pano.settings import PUPPET_RUN_INTERVAL

__author__ = 'etaklar'


def sort_table(table, col=0, order=False):
    return sorted(table, reverse=order, key=lambda field: field[col])


def dictstatus(node_list, reports_dict, status_dict, sort=True, sortby=None, asc=False, get_status="all",
               puppet_run_time=PUPPET_RUN_INTERVAL, format_time=True):
    """
    :param node_list: dict
    :param status_dict: dict
    :param sortby: Takes a field name to sort by 'certname', 'latestCatalog', 'latestReport', 'latestFacts', 'success', 'noop', 'failure', 'skipped'
    :param get_status: Status type to return. all, changed, failed, unreported, noops
    :return: tuple(tuple,tuple)

    node_dict input:
    {
        'certname': {
            "name": <string>,
            "deactivated": <timestamp>,
            "catalog_timestamp": <timestamp>,
            "facts_timestamp": <timestamp>,
            "report_timestamp": <timestamp>
        },
    }
    --------------------------------
    status_dict input:
    {
        'certname': {
            "subject-type": "certname",
            "subject": { "title": "foo.local" },
            "failures": 0,
            "successes": 2,
            "noops": 0,
           "skips": 1
        },
    }
    """
    # The merged_list tuple should look like this.
    # (
    # ('certname', 'latestCatalog', 'latestReport', 'latestFacts', 'success', 'noop', 'failure', 'skipped'),
    # )
    def check_failed_compile(report_timestamp,
                             fact_timestamp,
                             catalog_timestamp,
                             puppet_run_interval=puppet_run_time):
        """
        :param report_timestamp: str
        :param fact_timestamp: str
        :param catalog_timestamp: str
        :return: Bool
        Returns False if the compiled run has not failed
        Returns True if the compiled run has failed
        """

        if report_timestamp is None or catalog_timestamp is None or fact_timestamp is None:
            return True
        # check if the fact report is older than puppet_run_time by double the run time
        report_time = json_to_datetime(report_timestamp)
        fact_time = json_to_datetime(fact_timestamp)
        catalog_time = json_to_datetime(catalog_timestamp)

        # Report time, fact time and catalog time should all be run within (PUPPET_RUN_INTERVAL / 2)
        # minutes of each other
        diffs = dict()
        # Time elapsed between fact time and catalog time
        diffs['catalog_fact'] = catalog_time - fact_time
        diffs['fact_catalog'] = fact_time - catalog_time

        # Time elapsed between fact time and report time
        diffs['report_fact'] = report_time - fact_time
        diffs['fact_report'] = fact_time - report_time
        # Time elapsed between report and catalog
        diffs['report_catalog'] = report_time - catalog_time
        diffs['catalog_report'] = catalog_time - report_time

        for key, value in diffs.items():
            if value > timedelta(minutes=puppet_run_interval / 2):
                return True
        return False

    def append_list(n_data, s_data, m_list, r_status, format_time=True):
        if type(n_data) is not dict or type(s_data) is not dict and type(m_list) is not list and not r_status:
            raise ValueError('Incorrect type given as input. Expects n_data, s_data as dict and m_list as list.')
        catalog_timestamp = n_data['catalog_timestamp'] if n_data['catalog_timestamp'] is not None else ''
        report_timestamp = n_data['report_timestamp'] if n_data['report_timestamp'] is not None else ''
        facts_timestamp = n_data['facts_timestamp'] if n_data['facts_timestamp'] is not None else ''

        if format_time:
            if catalog_timestamp is not '':
                catalog_timestamp = filters.date(localtime(json_to_datetime(catalog_timestamp)), 'Y-m-d H:i:s')
            if report_timestamp is not '':
                report_timestamp = filters.date(localtime(json_to_datetime(report_timestamp)), 'Y-m-d H:i:s')
            if facts_timestamp is not '':
                facts_timestamp = filters.date(localtime(json_to_datetime(facts_timestamp)), 'Y-m-d H:i:s')

        m_list.append((
            n_data['certname'],
            catalog_timestamp,
            report_timestamp,
            facts_timestamp,
            s_data.get('successes', 0),
            s_data.get('noops', 0),
            s_data.get('failures', 0),
            s_data.get('skips', 0),
            r_status,
        ))

    def get_report_status(reports_dict, certname, node=None, node_dict=None):
        """
        This function will attempt to fetch the latest report status from
        the node or node_dict in case the reports_dict are None. This will
        allow passing both None or a dictionary as the report_dicts function
        to dictstatus() to keep compability and allow performance improvements
        """
        if reports_dict is None:
            if node is not None:
                return node.get('latest_report_status', 'unknown')
            elif node_dict is not None:
                if certname in node_dict:
                    return node_dict[certname].get('latest_report_status', 'unknown')
                else:
                    return None
        else:
            if certname in reports_dict:
                return reports_dict[certname]['status']
            else:
                return None

    sortables = {
        'certname': 0,
        'catalog_timestamp': 1,
        'report_timestamp': 2,
        'facts_timestamp': 3,
        'successes': 4,
        'noops': 5,
        'failures': 6,
        'skips': 7,
    }

    if sortby:
        # Sort by the field recieved, if valid field was not supplied, fallback
        # to report
        sortbycol = sortables.get(sortby, 2)
    else:
        sortbycol = 2

    # if sortbycol is 4, 5, 6 or 7 ( a different list creation method must be used.

    merged_list = []
    failed_list = []
    unreported_list = []
    changed_list = []
    pending_list = []
    mismatch_list = []

    # if sort field is certname or catalog/report/facts_timestamp then we will sort this way
    # or if the get_status is set to "not_all" indicating that the dashboard wants info.
    if get_status != 'all':
        for node in node_list:
            node_is_unreported = False
            node_has_mismatching_timestamps = False
            # Check if its unreported.
            if is_unreported(node_report_timestamp=node['report_timestamp'], unreported=puppet_run_time):
                node_is_unreported = True
            if check_failed_compile(report_timestamp=node.get('report_timestamp', None),
                                    fact_timestamp=node.get('facts_timestamp', None),
                                    catalog_timestamp=node.get('catalog_timestamp', None)):
                node_has_mismatching_timestamps = True
            # Check for the latest report.
            report_status = get_report_status(reports_dict, node['certname'], node=node)
            if report_status is not None:
                # Check which status the run is.

                """
                Can be used later but right now we just utilize the event-counts response.
                # Dictify the metrics for the report.
                metrics_data = {item['category'] + '-' + item['name']: item for item in
                                reports_dict[node_name]['metrics']['data']}
                """

                # Collect the number of events for each node in its latest report.
                if node['certname'] in status_dict:
                    # If the puppet status is changed but there are noop events set to pending.
                    if report_status == 'unchanged' and status_dict[node['certname']]['noops'] > 0:
                        report_status = 'pending'
                # If there is no status events for the latest report then send an empty list to append_list function
                else:
                    # Add an empty status_dict for the node.
                    status_dict[node['certname']] = {}

                # If theres no report for this node ... panic no idea how to handle this yet. If it can even happen?
                # Check if its an unreported longer than the unreported time.
                if node_is_unreported is True:
                    # Append to the unreported list.
                    append_list(node, status_dict[node['certname']], unreported_list, report_status, format_time=format_time)
                # If its got mismatching timestamps put it in the mismatching list
                if node_has_mismatching_timestamps is True:
                    append_list(node, status_dict[node['certname']], mismatch_list, report_status, format_time=format_time)
                # If the node is not unreported or has mismatching timestamps.. proceed to put in the correct lists.
                if report_status == 'changed':
                    append_list(node, status_dict[node['certname']], changed_list, report_status, format_time=format_time)
                elif report_status == 'failed':
                    append_list(node, status_dict[node['certname']], failed_list, report_status, format_time=format_time)
                elif report_status == 'pending':
                    append_list(node, status_dict[node['certname']], pending_list, report_status, format_time=format_time)

    elif sortbycol <= 3 and get_status == 'all':
        for node in node_list:
            # Check for the latest report.
            report_status = get_report_status(reports_dict, node['certname'], node=node)
            if report_status is not None:
                # Check which status the run is.
                """
                Can be used later but right now we just utilize the event-counts response.
                # Dictify the metrics for the report.
                metrics_data = {item['category'] + '-' + item['name']: item for item in
                                reports_dict[node_name]['metrics']['data']}
                """
            # Collect the number of events for each node in its latest report.
            if node['certname'] in status_dict:
                # If the puppet status is changed but there are noop events set to pending.
                if status_dict[node['certname']]:
                    if report_status == 'unchanged' and status_dict[node['certname']]['noops'] > 0:
                        report_status = 'pending'
            # If there is no status events for the latest report then send an empty list to append_list function
            else:
                # Add an empty status_dict for the node.
                status_dict[node['certname']] = {}
                report_status = 'unknown' #FIXME: what's the correct status
            append_list(node, status_dict[node['certname']], merged_list, report_status, format_time=format_time)
    # Only used when orderby is a status field.
    elif sortbycol >= 4 and get_status == 'all':
        sort = True
        node_dict = {item['certname']: item for item in node_list}
        for status, value in status_dict.items():
            # Check which status the run is.
            report_status = get_report_status(reports_dict, value['subject']['title'], node_dict=node_dict)
            if value['subject']['title'] in node_dict and report_status:
                append_list(node_dict[value['subject']['title']], value, merged_list, report_status, format_time=format_time)

    # Sort the lists if sort is True
    if sort and get_status == 'all':
        return sort_table(merged_list, order=asc, col=sortbycol)
    elif sort and get_status != 'all':
        sorted_unreported_list = sort_table(unreported_list, order=asc, col=sortbycol)
        sorted_changed_list = sort_table(changed_list, order=asc, col=sortbycol)
        sorted_failed_list = sort_table(failed_list, order=asc, col=sortbycol)
        sorted_mismatch_list = sort_table(mismatch_list, order=asc, col=sortbycol)
        sorted_pending_list = sort_table(pending_list, order=asc, col=sortbycol)
        return sorted_failed_list, \
               sorted_changed_list, \
               sorted_unreported_list, \
               sorted_mismatch_list, \
               sorted_pending_list

    if get_status == 'all':
        return merged_list
    else:
        return failed_list, changed_list, unreported_list, mismatch_list, pending_list


class DictDiffer(object):
    """
    Taken from: https://github.com/hughdbrown/dictdiffer
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """

    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])
