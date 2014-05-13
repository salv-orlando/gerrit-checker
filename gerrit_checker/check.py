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


def get_review_age():
    try:
        f = open(constants.CHECK_DATA_FILE)
        data = json.loads(f.read())
        last_check = datetime.datetime.strptime(
            data['last_check'], constants.DATETIME_FORMAT)
        delta = datetime.datetime.now() - last_check
        return delta.seconds
    except (IOError, KeyError, ValueError):
        print("Last check timestamp not found or invalid. "
              "Defaulting to 48 hours",
              file=sys.stderr)
        return 48 * 3600


def save_check_data():
    last_check = datetime.datetime.now()
    output = json.dumps({'last_check':
                         last_check.strftime(constants.DATETIME_FORMAT)})
    f = open(constants.CHECK_DATA_FILE, 'w')
    f.write(output)
    f.close()


def main():
    # Parse arguments
    args = parse_arguments()
    if not args.age:
        # Age was not explicitly specified
        review_age = get_review_age()
    else:
        review_age = args.age * 3600
    print("Maximum review age:%s seconds" % review_age)
    stuff = gerrit_client.get_new_changes(args.uri, args.projects, review_age)
    columns = ["Change number", "Subject", "Project", "Branch", "Topic"]
    table = prettytable.PrettyTable(columns)
    for column in columns:
        table.align[column] = "l"
    table.padding_width = 1
    for item in stuff:
        table.add_row(item)
    print(table)
    if not args.peek:
        save_check_data()
