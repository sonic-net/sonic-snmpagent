from __future__ import print_function
import sys
from getopt import getopt


def usage(script_name):
    print('Usage: python ', script_name,
          '-t [host] -p [port] -s [unix_socket_path] -d [logging_level] -f [update_frequency] -r [enable_dynamic_frequency] -h [help]')


def process_options(script_name):
    """
    Process command line options
    """
    options, remainders = getopt(sys.argv[1:], "t:p:s:d:f:rh", ["host=", "port=", "unix_socket_path=", "debug=", "frequency=", "enable_dynamic_frequency", "help"])

    args = {}
    for (opt, arg) in options:
        try:
            if opt in ('-d', '--debug'):
                args['log_level'] = int(arg)
            elif opt in ('-t', '--host'):
                args['host'] = arg
            elif opt in ('-p', '--port'):
                args['port'] = int(arg)
            elif opt in ('-s', '--unix_socket_path'):
                args['unix_socket_path'] = arg
            elif opt in ('-f', '--frequency'):
                args['update_frequency'] = int(arg)
            elif opt in ('-r', '--enable_dynamic_frequency'):
                args['enable_dynamic_frequency'] = True
            elif opt in ('-h', '--help'):
                usage(script_name)
                sys.exit(0)
        except ValueError as e:
            print('Invalid option for {}: {}'.format(opt, e))
            sys.exit(1)

    return args
