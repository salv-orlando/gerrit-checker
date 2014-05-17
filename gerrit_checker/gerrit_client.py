import datetime
import json

import requests

from gerrit_checker import constants


def _check_status_code(res):
    if res.status_code != 200:
        print("Request failed:%s" % res.text)
        res.raise_for_status()


def _prepare_output(res, sorts=None):
    """Prepares a list response for the frontend."""
    actual_res = res[res.index(constants.GERRIT_MAGIC_STRING) +
                     len(constants.GERRIT_MAGIC_STRING):]
    stuff = json.loads(actual_res)
    results = []
    for change in stuff:
        # Gerrit outputs timestamps with nanoseconds. We're not that pedant
        update_timestamp = datetime.datetime.strptime(change['updated'][:-10],
                                                      '%Y-%m-%d %H:%M:%S')
        results.append((change['project'],
                        change['_number'],
                        change['subject'],
                        change['owner'].get('name'),
                        update_timestamp.strftime(constants.DATETIME_FORMAT),
                        change['branch'],
                        change.get('topic')))
    return results


def get_new_changes_for_project(uri, projects_and_ages, only_open=True,
                                owners=None, exclude_owners=False):
    """Retrieve new changes up to a certain age.

    This method will return information only for new changes
    submitted to gerrit since the last
    """
    owner_key = '-owner' if exclude_owners else 'owner'
    owner_joiner = '+' if exclude_owners else '+OR+'
    project_age_clause = ' OR '.join('(project:%s+-age:%ss)'
                                     % (project, age) for (project, age) in
                                     projects_and_ages.iteritems())
    # Ensure owners is iterable
    if not owners:
        owners = []
    owner_clause = owner_joiner.join(["%s:%s" % (owner_key, owner)
                                      for owner in owners])
    req_uri = (("%(uri)s/changes/?q=%(project_age)s"
                "%(status)s%(owner)s&o=LABELS") %
               {'uri': uri,
                'project_age': project_age_clause,
                'status': '+status:open' if only_open else '',
                'owner': '+(%s)' % owner_clause if owner_clause else ''})
    res = requests.get(req_uri)
    _check_status_code(res)
    return _prepare_output(res.text)
