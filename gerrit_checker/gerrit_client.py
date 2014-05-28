import datetime
import json

import requests
import requests.auth

from gerrit_checker import constants


def _check_status_code(res):
    if res.status_code != 200:
        print("Request failed:%s" % res.text)
        res.raise_for_status()


def _retrieve_new_changes(data, projects_and_ages):
    results = []
    for change in data:
        project_age = projects_and_ages[change['project']]
        create_timestamp = datetime.datetime.strptime(
            change['created'][:-10], constants.DATETIME_FORMAT_G)
        delta = datetime.datetime.now() - create_timestamp
        if project_age > delta.total_seconds():
            results.append(change)
    return results


def _post_query_filtering(data, projects_and_ages, only_new):
    """Perform further filtering on results returned by gerrit"""
    if only_new:
        data = _retrieve_new_changes(data, projects_and_ages)
    return data


def _prepare_output(data, is_auth=False):
    """Prepares a list response for the frontend."""
    results = []
    for change in data:
        # Gerrit outputs timestamps with nanoseconds. We're not that pedant
        update_timestamp = datetime.datetime.strptime(
            change['updated'][:-10], constants.DATETIME_FORMAT_G)
        print change
        reviewed = change.get('reviewed', False) if is_auth else None
        results.append((change['project'],
                        change['_number'],
                        change['subject'],
                        change['owner'].get('name'),
                        update_timestamp.strftime(constants.DATETIME_FORMAT),
                        change['branch'],
                        change.get('topic'),
                        reviewed))
    return results


def get_changes(uri, projects_and_ages={}, only_open=True,
                owners=None, exclude_owners=False, reviewers=None,
                files=None, only_new=False, credentials=None):
    """Retrieves gerrit changes.

    Also performds filters on age, patch status, patch owner and newnewss.
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
    # Ensure reviewers is iterable
    if not reviewers:
        reviewers = []
    reviewer_clause = '+'.join(["%s:%s" % ('reviewer', reviewer)
                                for reviewer in reviewers])

    # Gerrit requires regex pattern to start with '^'
    if files and not files.startswith('^'):
        files = '^' + files
    auth = None
    if credentials:
        auth = requests.auth.HTTPDigestAuth(credentials['user'],
                                            credentials['password'])
    req_url = (("%(uri)s/%(auth)schanges/?q=%(project_age)s"
                "%(status)s%(owner)s%(reviewer)s%(file)s"
                "&o=LABELS&o=REVIEWED") %
               {'uri': uri,
                'auth': 'a/' if auth else '',
                'project_age': ('(%s)' % project_age_clause
                                if project_age_clause else ''),
                'status': '+status:open' if only_open else '',
                'owner': '+(%s)' % owner_clause if owner_clause else '',
                'reviewer': ('+(%s)' % reviewer_clause
                             if reviewer_clause else ''),
                'file': '+file:%s' % files if files else ''})
    auth = None
    if credentials:
        auth = requests.auth.HTTPDigestAuth(credentials['user'],
                                            credentials['password'])
    res = requests.get(req_url, auth=auth)
    _check_status_code(res)
    actual_res = res.text[res.text.index(constants.GERRIT_MAGIC_STRING) +
                          len(constants.GERRIT_MAGIC_STRING):]
    stuff = json.loads(actual_res)
    return _prepare_output(_post_query_filtering(
        stuff, projects_and_ages, only_new), is_auth=auth)


def add_reviewer_to_change(uri, user, password, change_id, reviewer):
    """Add a reviewer to a gerrit change.

    This operation requires authentication.
    """
    req_url = ("%(uri)s/a/changes/%(change_id)s/reviewers" %
               {'uri': uri,
                'change_id': change_id})
    req_data = json.dumps({'reviewer': reviewer})
    auth = requests.auth.HTTPDigestAuth(user, password)
    res = requests.post(req_url, req_data, auth=auth,
                        headers={'content-type': 'application/json'})
    _check_status_code(res)
    actual_res = res.text[res.text.index(constants.GERRIT_MAGIC_STRING) +
                          len(constants.GERRIT_MAGIC_STRING):]
    stuff = json.loads(actual_res)['reviewers']
    # verify if the reviewer was actually added or not
    reviewers = [item.get('username') for item in stuff]
    return reviewer in reviewers
