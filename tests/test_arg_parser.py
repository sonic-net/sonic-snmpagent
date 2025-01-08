from unittest import TestCase
from unittest.mock import patch

import pytest
from sonic_ax_impl.utils.arg_parser import process_options


class TestUtil(TestCase):

    # Given: Don't pass any parameter
    # When: Parse args
    # Then: Return empty dict
    @patch('sys.argv', ['sonic_ax_impl'])
    def test_valid_options_default_value_none(self):
        args = process_options("sonic_ax_impl")

        self.assertNotIn("log_level", args)
        self.assertNotIn("host", args)
        self.assertNotIn("port", args)
        self.assertNotIn("unix_socket_path", args)
        self.assertNotIn("update_frequency", args)
        self.assertNotIn("enable_dynamic_frequency", args)

    # Given: Pass --port=aaa
    # When: Parse args
    # Then: Print valure error
    @patch('builtins.print')
    @patch('sys.argv', ['sonic_ax_impl', '--port=aaa'])
    def test_valid_options_value_error(self, mock_print):
        with pytest.raises(SystemExit) as excinfo:
            process_options("sonic_ax_impl")
        assert excinfo.value.code == 1
        mock_print.assert_called_with("Invalid option for --port: invalid literal for int() with base 10: 'aaa'")

    # Given: Pass -h
    # When: Parse args
    # Then: Print help logs
    @patch('builtins.print')
    @patch('sys.argv', ['sonic_ax_impl', '-h'])
    def test_valid_options_help(self, mock_print):
        with pytest.raises(SystemExit) as excinfo:
            process_options("sonic_ax_impl")
        assert excinfo.value.code == 0
        mock_print.assert_called_with('Usage: python ', 'sonic_ax_impl', '-t [host] -p [port] -s [unix_socket_path] -d [logging_level] -f [update_frequency] -r [enable_dynamic_frequency] -h [help]')

    # Given: Pass help
    # When: Parse args
    # Then: Print help logs
    @patch('builtins.print')
    @patch('sys.argv', ['sonic_ax_impl', '--help'])
    def test_valid_options_help_long(self, mock_print):
        with pytest.raises(SystemExit) as excinfo:
            process_options("sonic_ax_impl")
        assert excinfo.value.code == 0
        mock_print.assert_called_with('Usage: python ', 'sonic_ax_impl', '-t [host] -p [port] -s [unix_socket_path] -d [logging_level] -f [update_frequency] -r [enable_dynamic_frequency] -h [help]')

    # Given: Pass -r
    # When: Parse args
    # Then: Enable enable_dynamic_frequency
    @patch('sys.argv', ['sonic_ax_impl', '-r'])
    def test_valid_options_enable_dynamic_frequency(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["enable_dynamic_frequency"], True)

    # Given: Pass --enable_dynamic_frequency
    # When: Parse args
    # Then: Enable enable_dynamic_frequency
    @patch('sys.argv', ['sonic_ax_impl', '--enable_dynamic_frequency'])
    def test_valid_options_enable_dynamic_frequency_long(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["enable_dynamic_frequency"], True)

    # Given: Pass -f
    # When: Parse args
    # Then: Enable enable_dynamic_frequency
    @patch('sys.argv', ['sonic_ax_impl', '-f9'])
    def test_valid_options_update_frequency(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["update_frequency"], 9)

    # Given: Pass --frequency
    # When: Parse args
    # Then: Enable enable_dynamic_frequency
    @patch('sys.argv', ['sonic_ax_impl', '--frequency=9'])
    def test_valid_options_update_frequency_long(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["update_frequency"], 9)

    # Given: Pass -s
    # When: Parse args
    # Then: Parse socket
    @patch('sys.argv', ['sonic_ax_impl', '-s/unix/socket'])
    def test_valid_options_socket(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["unix_socket_path"], "/unix/socket")

    # Given: Pass --unix_socket_path
    # When: Parse args
    # Then: Parse socket
    @patch('sys.argv', ['sonic_ax_impl', '--unix_socket_path=/unix/socket'])
    def test_valid_options_socket_long(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["unix_socket_path"], "/unix/socket")

    # Given: Pass -p
    # When: Parse args
    # Then: Parse port
    @patch('sys.argv', ['sonic_ax_impl', '-p6666'])
    def test_valid_options_port(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["port"], 6666)

    # Given: Pass --port
    # When: Parse args
    # Then: Parse port
    @patch('sys.argv', ['sonic_ax_impl', '--port=6666'])
    def test_valid_options_port_long(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["port"], 6666)

    # Given: Pass -t
    # When: Parse args
    # Then: Parse host
    @patch('sys.argv', ['sonic_ax_impl', '-tsnmp.com'])
    def test_valid_options_host(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["host"], 'snmp.com')

    # Given: Pass --host
    # When: Parse args
    # Then: Parse host
    @patch('sys.argv', ['sonic_ax_impl', '--host=snmp.com'])
    def test_valid_options_host_long(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["host"], 'snmp.com')

    # Given: Pass -d
    # When: Parse args
    # Then: Parse log_level
    @patch('sys.argv', ['sonic_ax_impl', '-d9'])
    def test_valid_options_host(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["log_level"], 9)

    # Given: Pass --debug
    # When: Parse args
    # Then: Parse log_level
    @patch('sys.argv', ['sonic_ax_impl', '--debug=9'])
    def test_valid_options_host_long(self):
        args = process_options("sonic_ax_impl")
        self.assertEqual(args["log_level"], 9)

