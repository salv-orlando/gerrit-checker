from __future__ import print_function
import argparse
import datetime
import json
import sys

import prettytable

from gerrit_checker import constants
from gerrit_checker import gerrit_client


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Do useful things with gerrit REST API')
    parser.add_argument('--projects', type=str, nargs='+', required=True,
                        help='project for which changes should be retrieved')
    parser.add_argument('--age', type=int, default=None,
                        help=('maximum review age in hours'))
    parser.add_argument('--peek', default=False, action='store_true',
                        help=("Only peek changes, do not update "
                              "check timestamp"))
    parser.add_argument('--uri', type=str,
                        default='https://review.openstack.org',
                        help='Gerrit REST API endpoint (including protocol)')
    return parser.parse_args()


def get_review_age(projects):
    review_ages = {}

    def set_default_ages():
        print("Last check timestamp for project %s, not found or "
              "invalid. Defaulting to 48 hours." % project,
              file=sys.stderr)
        review_ages[project] = 48 * 3600

    try:
        f = open(constants.CHECK_DATA_FILE)
        data = json.loads(f.read())
    except IOError:
        set_default_ages()
        return

    last_check_data = data.get('last_check', {})
    for project in projects:
        try:
            last_check = datetime.datetime.strptime(
                last_check_data[project],
                constants.DATETIME_FORMAT)
            delta = datetime.datetime.now() - last_check
            review_ages[project] = delta.seconds
        except (KeyError, TypeError, ValueError):
            set_default_ages()
    return review_ages


def save_check_data(projects):
    last_check = datetime.datetime.now()
    output = json.dumps(
        {'last_check':
            dict((project, last_check.strftime(constants.DATETIME_FORMAT))
                 for project in projects)})
    f = open(constants.CHECK_DATA_FILE, 'w')
    f.write(output)
    f.close()


def main():
    # Parse arguments
    args = parse_arguments()
    if not args.age:
        # Age was not explicitly specified
        projects_and_ages = get_review_age(args.projects)
    else:
        projects_and_ages = (dict((project, args.age * 3600)
                             for project in args.projects))
    print("Maximum review ages:\n%s" % projects_and_ages)
    for project in projects_and_ages:
        stuff = gerrit_client.get_new_changes_for_project(
            args.uri, project, projects_and_ages[project])
        columns = ["Change number", "Subject", "Owner", "Branch", "Topic"]
        table = prettytable.PrettyTable(columns)
        for column in columns:
            table.align[column] = "l"
        table.padding_width = 1
        for item in stuff:
            table.add_row(item)
        print("--------------------------------------------------------------")
        print("Project:%s" % project)
        print("--------------------------------------------------------------")
        print(table)
    if not args.peek:
        save_check_data(args.projects)
