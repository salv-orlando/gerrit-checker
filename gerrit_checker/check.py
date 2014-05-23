from __future__ import print_function
import argparse
import datetime
import json
import sys

import prettytable
from requests import exceptions as req_exc

from gerrit_checker import constants
from gerrit_checker import gerrit_client


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Do useful things with gerrit REST API')
    parser.add_argument('--projects', type=str, nargs='+', required=True,
                        help='project for which changes should be retrieved')
    owner_group = parser.add_mutually_exclusive_group()
    owner_group.add_argument('--owners', type=str, nargs='+',
                             help='filter by patch owned by specified users')
    owner_group.add_argument('--exclude-owners', type=str, nargs='+',
                             help='exluded patches owned by specified users')
    parser.add_argument('--only-new', default=False, action='store_true',
                        help='Retrieve only completely new changes')
    parser.add_argument('--age', type=int, default=None,
                        help=('maximum review age in hours'))
    parser.add_argument('--reviewers', type=str, nargs='+', required=True,
                        help='retrieve only patches being reviewed by '
                             'specified users')
    parser.add_argument('--files', type=str,
                        help='regex pattern for matching files')
    parser.add_argument('--peek', default=False, action='store_true',
                        help=("Only peek changes, do not update "
                              "check timestamp"))
    parser.add_argument('--uri', type=str,
                        default='https://review.openstack.org',
                        help='Gerrit REST API endpoint (including protocol)')
    parser.add_argument('--user', type=str,
                        help='Gerrit user name for authentication')
    parser.add_argument('--password', type=str,
                        help='Gerrit HTTP password')
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
            review_ages[project] = int(delta.total_seconds())
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


def validate_input(args):
    """Perform validation across multiple arguments"""
    if (args.user or args.password) and not (args.user and args.password):
        print("Both user and password should be specified."
              "User is:%s, password is:%s" % (args.user, args.password),
              file=sys.stderr)
        sys.exit(1)
    if ('self' in (args.owners or []) + (args.reviewers or []) and
            not (args.user and args.password)):
        print("The 'self' keyword cannot be used without credentials",
              file=sys.stderr)
        sys.exit(1)


def main():
    # Parse arguments
    args = parse_arguments()
    validate_input(args)
    if not args.age:
        # Age was not explicitly specified
        projects_and_ages = get_review_age(args.projects)
    else:
        projects_and_ages = (dict((project, args.age * 3600)
                             for project in args.projects))
    print("Maximum review ages:\n%s" % projects_and_ages)
    exclude_owners = False
    owners = args.owners
    if args.exclude_owners:
        exclude_owners = True
        owners = args.exclude_owners
    try:
        credentials = None
        if args.user:
            credentials = {'user': args.user, 'password': args.password}
        stuff = gerrit_client.get_changes(
            args.uri, projects_and_ages,
            owners=owners, exclude_owners=exclude_owners,
            reviewers=args.reviewers, files=args.files,
            only_new=args.only_new,
            credentials=credentials)
    except req_exc.HTTPError as e:
        print("The Gerrit API request returned an error:%s" % e,
              file=sys.stderr)
        sys.exit(1)

    columns = ["Project", "Change number", "Subject",
               "Owner", "Last update", "Branch", "Topic"]
    table = prettytable.PrettyTable(columns)
    for column in columns:
        table.align[column] = "l"
    table.padding_width = 1
    for item in stuff:
        table.add_row(item)
    print(table)
    if not args.peek:
        save_check_data(args.projects)
