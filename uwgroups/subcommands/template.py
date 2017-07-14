"""Template for a subcommand.

The first line above is shown in the top-level help.  Additional lines
in this docstring are included in the help message for the subcommand.
"""

import logging

log = logging.getLogger(__name__)


def build_parser(parser):
    parser.add_argument('infile',
                        nargs='?',
                        help='A required input file')
    parser.add_argument('outfile',
                        nargs='?',
                        help='A required output file')
    parser.add_argument('-m', '--monkey-type',
                        default='rhesus',
                        type=str,
                        help="specify type of monkey [%(default)s]")


def action(args):
    print 'monkey type:{}'.format(args.monkey_type)
