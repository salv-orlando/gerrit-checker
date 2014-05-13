import json

import requests

from gerrit_checker import constants


def _check_status_code(res):
    if res.status_code != 200:
        res.raise_for_status()


def get_new_changes(uri, projects, age):
    """ Retrieve new changes up to a certain age.

    This method will return information only for new changes
    submitted to gerrit since the last
    """
    project_list = ' OR '.join(projects)
    age_str = "%ss" % age
    res = requests.get(
        "%(uri)s/changes/?q=project:%(project_list)s+"
        "status:open+-age:%(age)s&o=LABELS" %
        {'uri': uri,
         'project_list': project_list,
         'age': age_str})
    _check_status_code(res)
    actual_res = res.text[res.text.index(constants.GERRIT_MAGIC_STRING) +
                          len(constants.GERRIT_MAGIC_STRING):]
    stuff = json.loads(actual_res)
    results = []
    return [(change['_number'],
             change['subject'],
             change['project'],
             change['branch'],
             change['topic']) for change in stuff]
