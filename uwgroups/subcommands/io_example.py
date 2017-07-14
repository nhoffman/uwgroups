"""
Provides an example of file I/O using utils.Opener

Writes contents of `infile` to `outfile`. Examples:

    % cat infile.txt
    hello world!
    % ./uwgroups io_example infile.txt
    hello world!
    % cat infile.txt | ./uwgroups io_example
    hello world!
    % cat infile.txt | ./uwgroups io_example -
    hello world!
    % ./uwgroups io_example infile.txt -o outfile.txt
    % cat outfile.txt
    hello world!
"""

import sys
import logging
from ..utils import Opener

log = logging.getLogger(__name__)


def build_parser(parser):
    parser.add_argument('infile',
                        default=sys.stdin, type=Opener('r'), nargs='?',
                        help='A required input file')
    parser.add_argument('-o', '--outfile',
                        default=sys.stdout, type=Opener('w'),
                        help='An optional output file [default stdout]')


def action(args):
    args.outfile.write(args.infile.read())
