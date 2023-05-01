import datetime
import queue

from threading import Thread

from panopuppet.pano.puppetdb import puppetdb


class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return str('UTC')

    def dst(self, dt):
        return datetime.timedelta(0)

    def __repr__(self):
        return str('<UTC>')

    def __str__(self):
        return str('UTC')

    def __unicode__(self):
        return 'UTC'


def json_to_datetime(date):
    """Tranforms a JSON datetime string into a timezone aware datetime
    object with a UTC tzinfo object.

    :param date: The datetime representation.
    :type date: :obj:`string`

    :returns: A timezone aware datetime object.
    :rtype: :class:`datetime.datetime`
    """
    return datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ').replace(
        tzinfo=UTC())


def is_unreported(node_report_timestamp, unreported=120):
    # If node has no report timestamp
    # it has probably failed so return True.
    if node_report_timestamp is None:
        return True
    if type(unreported) not in [float, int]:
        raise ValueError("unreported input parameter must be integer.")
    last_report = json_to_datetime(node_report_timestamp)
    last_report = last_report.replace(tzinfo=None)
    now = datetime.datetime.utcnow()
    unreported_border = now - datetime.timedelta(minutes=unreported)
    if last_report < unreported_border:
        return True
    return False


def run_puppetdb_jobs(jobs, threads=6):
    if type(threads) != int:
        threads = 6
    if len(jobs) < threads:
        threads = len(jobs)
    jobs_q = queue.Queue()
    out_q = queue.Queue()

    def db_threaded_requests(i, q):
        while True:
            t_job = q.get()
            t_path = t_job['path']
            t_url = t_job.get('url')
            t_certs = t_job.get('certs')
            t_verify = t_job.get('verify')
            t_params = t_job.get('params', {})
            t_api_v = t_job.get('api_version', 'v3')
            t_request = t_job.get('request')
            results = puppetdb.api_get(
                api_url=t_url,
                verify=t_verify,
                cert=t_certs,
                path=t_path,
                params=puppetdb.mk_puppetdb_query(t_params, t_request),
                api_version=t_api_v,
            )
            out_q.put({t_job['id']: results})
            q.task_done()

    for i in range(threads):
        worker = Thread(target=db_threaded_requests, args=(i, jobs_q))
        worker.setDaemon(True)
        worker.start()

    for job in jobs:
        jobs_q.put(jobs[job])
    jobs_q.join()
    job_results = {}
    while True:
        try:
            msg = (out_q.get_nowait())
            job_results = dict(
                list(job_results.items()) + list(msg.items()))
        except queue.Empty:
            break

    return job_results


def generate_csv(jobs, threads=6):
    if type(threads) != int:
        threads = 6
    if len(jobs) < threads:
        threads = len(jobs)
    jobs_q = queue.Queue()
    out_q = queue.Queue()

    def db_threaded_requests(i, q):
        while True:
            # Get the job
            t_job = q.get()
            # Start assigning variables from the data in the dict we received above.
            t_id = t_job['id']
            t_include_facts = t_job['include_facts']
            t_node = t_job['node']
            t_facts = t_job['facts']
            # Convert tuple to list
            t_node = list(t_node)
            # End of assigning variables
            # For each fact the user requested, locate the fact result for each node
            # and append it to the t_node list.
            # If the node does not have a value for the fact add an empty column.
            for fact in t_include_facts:
                fact = fact.strip()
                if t_node[0] in t_facts[fact]:
                    t_node.append(t_facts[fact][t_node[0]]['value'])
                else:
                    t_node.append('')
            # package the above results and put into a dict with the key name corresponding to the ID.
            t_result = dict()
            t_result[t_id] = tuple(t_node)
            out_q.put(t_result)
            q.task_done()

    for i in range(threads):
        worker = Thread(target=db_threaded_requests, args=(i, jobs_q))
        worker.setDaemon(True)
        worker.start()

    for job in jobs:
        jobs_q.put(jobs[job])
    jobs_q.join()
    job_results = {}
    while True:
        try:
            msg = (out_q.get_nowait())
            job_results = dict(
                list(job_results.items()) + list(msg.items()))
        except queue.Empty:
            break
    return job_results
