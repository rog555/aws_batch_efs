#!/usr/bin/env python
# --------------------------------------------------------------
# simple script to submit and monitor aws batch jobs
# --------------------------------------------------------------
import argparse
import boto3
from datetime import datetime
import gevent.monkey
gevent.monkey.patch_all()
import gevent
import gevent.pool
import os
import sys
import time

client = boto3.client('batch')

STATUSES = [
    'SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING',
    'RUNNING', 'SUCCEEDED', 'FAILED'
]


# --------------------------------------------------------------
def fatal(msg):
    print('ERROR: %s' % msg)
    sys.exit(1)


# --------------------------------------------------------------
def get_job(job_id):
    if job_id is None:
        raise Exception('job_id required')
    r = client.describe_jobs(jobs=[job_id])
    if len(r['jobs']) == 0:
        raise Exception('job_id %s not found' % job_id)
    else:
        return r['jobs'][0]


# --------------------------------------------------------------
def get_jobs_by_status(job_queue, status, job_name=None):
    kwargs = {
        'jobQueue': job_queue,
        'jobStatus': status
    }
    jobs = []
    while True:
        r = client.list_jobs(**kwargs)
        for jsl in r['jobSummaryList']:
            if job_name is not None and jsl['jobName'] != job_name:
                continue
            jobs.append(jsl)
        if 'nextToken' in r:
            kwargs['nextToken'] = r['nextToken']
        else:
            break
    return jobs


# --------------------------------------------------------------
def get_job_statuses(job_queue):
    pool = gevent.pool.Pool(len(STATUSES))
    greenlets = []
    for status in STATUSES:
        greenlets.append(pool.spawn(
            get_jobs_by_status, job_queue, status
        ))
    gevent.joinall(greenlets)
    jobs = {}
    for g in greenlets:
        if g is not None and isinstance(g.value, list):
            for jsl in g.value:
                name = jsl['jobName']
                status = jsl['status']
                created_at = jsl['createdAt']
                if name not in jobs:
                    jobs[name] = {}
                job = jobs[name]
                if 'created_at' not in job or job['created_at'] > created_at:
                    job['created_at'] = created_at
                    job['status'] = status
                    job['id'] = jsl['jobId']
    return jobs


# --------------------------------------------------------------
def get_job_log(job_id, log_status=False, print_log=False, timestamp=False):
    wait_job_completion(job_id, log=False)
    job = get_job(job_id)
    kwargs = {
        'logGroupName': '/aws/batch/job',
        'logStreamName': job['container']['logStreamName'],
        'startFromHead': True
    }
    logs_client = boto3.client('logs')
    log_messages = []
    while True:
        r = logs_client.get_log_events(**kwargs)
        token = r.get('nextForwardToken')
        events = r.get('events')
        if token is None or len(events) == 0:
            break
        else:
            kwargs['nextToken'] = token
        for event in events:
            msg = ''
            if timestamp is True:
                msg += time.strftime(
                    '%Y-%m-%dT%H:%M:%SZ',
                    time.gmtime(event['timestamp'] / 1000)
                ) + ': '
            msg += event['message']
            if print_log is True:
                print(msg)
            else:
                log_messages.append(msg)
    return '\n'.join(log_messages)


# --------------------------------------------------------------
def get_job_status(job_id):
    return get_job(job_id).get('status')


# --------------------------------------------------------------
def get_latest_job_definition_id(name):
    kwargs = {
        'jobDefinitionName': name,
        'status': 'ACTIVE'
    }
    revision = 0
    while True:
        r = client.describe_job_definitions(**kwargs)
        for jd in r['jobDefinitions']:
            if jd['revision'] > revision:
                revision = jd['revision']
        if 'nextToken' in r:
            kwargs['nextToken'] = r['nextToken']
        else:
            break
    if revision == 0:
        raise Exception("ACTIVE job definition with name '%s' not found" % (
            name
        ))
    return '%s:%s' % (name, revision)


# --------------------------------------------------------------
def get_timestamp():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


# --------------------------------------------------------------
def submit_job(
    job_name, job_queue, defn_name, parameters=None, overrides=None,
    environment=None, print_log=False
):
    defn_id = get_latest_job_definition_id(defn_name)
    kwargs = {
        'jobName': job_name,
        'jobQueue': job_queue,
        'jobDefinition': defn_id
    }
    if isinstance(parameters, dict):
        kwargs['parameters'] = parameters
    if isinstance(overrides, dict):
        kwargs['containerOverrides'] = overrides
    if environment is not None:
        if 'containerOverrides' not in kwargs:
            kwargs['containerOverrides'] = {}
        kwargs['containerOverrides']['environment'] = val_list_dicts(
            environment, 'name'
        )
    r = client.submit_job(**kwargs)
    job_id = r['jobId']
    print('submitted job %s from definition ID %s with ID %s' % (
        job_name, defn_id, job_id
    ))
    if print_log is True:
        wait_job_completion(job_id)
        get_job_log(job_id, print_log=True)
    return job_id


# --------------------------------------------------------------
def val_list_dicts(val, keys=None):
    if type(keys) in [str, unicode]:
        keys = [keys, 'value']
    if not isinstance(keys, list):
        keys = ['key', 'value']
    if len(keys) != 2:
        raise('keys must be list of length 2')
    if isinstance(val, list):
        return val
    if type(val) in [str, unicode]:
        d = {}
        for kv in val.split(','):
            kv = kv.split('=', 1)
            if len(kv) == 2 and kv[0] != '':
                d[kv[0]] = kv[1]
        val = d
    if isinstance(val, dict):
        new_val = []
        for k, v in sorted(val.iteritems()):
            new_val.append(dict(zip(keys, [k, v])))
        return new_val
    raise Exception(
        'val type must be either list, dict or comma sep list of key=val'
    )


# --------------------------------------------------------------
def wait_job_completion(job_id, log=True):
    return wait_job_status(job_id, 'SUCCEEDED,FAILED', log)


# -----------------------------------   ---------------------------
def wait_job_status(job_id, status, log=True):
    if type(status) in [str, unicode]:
        status = status.split(',')
    last_job_status = ''
    while True:
        job_status = get_job(job_id)['status']
        if job_status != last_job_status:
            if log is True:
                print('%s status is %s' % (
                    get_timestamp(),
                    job_status)
                )
            last_job_status = job_status
        if job_status in status:
            break
        time.sleep(10)
    return job_status


# --------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description='Simple script to submit and monitor AWS Batch jobs'
    )
    ap.add_argument(
        'operation',
        choices=['submit', 'jobs', 'log', 'wait']
    )
    ap.add_argument(
        '-q', '--queue', default=os.environ.get('BATCH_QUEUE'),
        help='job queue name'
    )
    ap.add_argument(
        '-j', '--job', help='job name'
    )
    ap.add_argument(
        '-d', '--defn_name', help='job definition name',
        default=os.environ.get('BATCH_DEFN_NAME')
    )
    ap.add_argument(
        '-e', '--environment',
        help='comma separated name=value list of environment variables'
    )
    args = ap.parse_args()
    if args.queue is None:
        fatal('--queue or BATCH_QUEUE env var required')

    jobs = get_job_statuses(args.queue)

    if args.operation == 'jobs':
        fmt = ' '.join(['%-15s' for s in STATUSES])
        print(fmt % tuple([s for s in STATUSES]))
        for job_name, job in sorted(jobs.iteritems()):
            print(fmt % tuple([
                job_name if s == job['status'] else '' for s in STATUSES
            ]))
        sys.exit(0)

    if args.job is None:
        fatal('--job required')
    job_id = jobs.get(args.job, {}).get('id')

    if args.operation == 'submit':
        if args.defn_name is None:
            fatal('--defn_name or BATCH_DEFN_NAME env var required')
        if job_id is not None:
            status = jobs[args.job]['status']
            fatal("job '%s' already process%s with status %s" % (
                args.job,
                'ed' if status in ['SUCCEEDED', 'FAILED'] else 'ing',
                status
            ))
        submit_job(
            args.job,
            args.queue,
            args.defn_name,
            environment=args.environment,
            print_log=True
        )
        sys.exit(0)

    if job_id is None:
        fatal('job %s not found on queue %s' % (args.job, args.queue))

    elif args.operation == 'log':
        get_job_log(job_id, print_log=True)

    elif args.operation == 'wait':
        wait_job_completion(job_id)
