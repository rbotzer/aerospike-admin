#!/usr/bin/env python

# Copyright 2013-2017 Aerospike, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cmd
import copy
import getpass
import os
import re
import shlex
import sys
import logging
import traceback

if '-e' not in sys.argv and '--asinfo' not in sys.argv:
    # asinfo mode or non-interactive mode does not need readline
    # if we import readline then it adds escape character, which breaks some of asinfo use-cases.
    import readline
    if 'libedit' in readline.__doc__:
        # BSD libedit style tab completion for OS X
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

# Setup logger before anything


class BaseLogger(logging.Logger, object):

    def __init__(self, name, level=logging.WARNING):
        return super(BaseLogger, self).__init__(name, level=level)

    def _handle_exception(self, msg):
        if isinstance(msg, Exception) and not isinstance(msg, ShellException):
            traceback.print_exc()

    def _print_message(self, msg, level, red_color=False, *args, **kwargs):
        try:
            message = str(msg).format(*args, **kwargs)
        except Exception:
            message = str(msg)

        message = level + ": " + message

        if red_color:
            message = terminal.fg_red() + message + terminal.fg_clear()

        print message

    def debug(self, msg, *args, **kwargs):
        if self.level <= logging.DEBUG:
            self._print_message(msg=msg, level="DEBUG", red_color=False, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        if self.level <= logging.INFO:
            self._print_message(msg=msg, level="INFO", red_color=False, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        if self.level <= logging.WARNING:
            self._print_message(msg=msg, level="WARNING", red_color=True, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        if self.level <= logging.ERROR:
            self._print_message(msg=msg, level="ERROR", red_color=True, *args, **kwargs)
            self._handle_exception(msg)

    def critical(self, msg, *args, **kwargs):
        if self.level <= logging.CRITICAL:
            self._print_message(msg=msg, level="ERROR", red_color=True, *args, **kwargs)
            self._handle_exception(msg)
        exit(1)

logging.setLoggerClass(BaseLogger)
logging.basicConfig(level=logging.WARNING)

logger = logging.getLogger('asadm')
logger.setLevel(logging.INFO)

from lib.controllerlib import ShellException
from lib.basiccontroller import BasicRootController
from lib.client import info
from lib.client.assocket import ASSocket
from lib.client.ssl_context import SSLContext
from lib.collectinfocontroller import CollectinfoRootController
from lib.logcontroller import LogRootController
from lib.utils import util
from lib.utils.constants import ADMIN_HOME
from lib.view import terminal, view

__version__ = '$$__version__$$'
CMD_FILE_SINGLE_LINE_COMMENT_START = "//"
CMD_FILE_MULTI_LINE_COMMENT_START = "/*"
CMD_FILE_MULTI_LINE_COMMENT_END = "*/"

ADMINHIST = ADMIN_HOME + 'admin_hist'

MULTILEVEL_COMMANDS = ["show", "info"]


class AerospikeShell(cmd.Cmd):
    def __init__(self, seed, user=None, password=None, use_services_alumni=False, use_services_alt=False,
                 log_path="", log_analyser=False, collectinfo=False,
                 ssl_context=None, only_connect_seed=False, execute_only_mode=False, timeout=5):

        self.execute_only_mode = execute_only_mode

        if log_analyser:
            self.name = 'Aerospike Log Analyzer Shell'
        elif collectinfo:
            self.name = 'Aerospike Collectinfo Shell'
        else:
            self.name = 'Aerospike Interactive Shell'

        if not execute_only_mode:
            print terminal.bold() + self.name + ', version ' +\
                __version__ + terminal.reset() + "\n"

        cmd.Cmd.__init__(self)

        try:
            if log_analyser:
                if not log_path:
                    log_path = " "
                self.ctrl = LogRootController(__version__, log_path)

                self.prompt = "Log-analyzer> "
            elif collectinfo:
                if not log_path:
                    logger.error(
                        "You have not specified any collectinfo path. Usage: asadm -c -f <collectinfopath>")
                    self.do_exit('')
                    exit(1)

                self.ctrl = CollectinfoRootController(__version__,
                                                      clinfo_path=log_path)

                self.prompt = "Collectinfo-analyzer> "
                if not execute_only_mode:
                    self.intro = str(self.ctrl.loghdlr)
            else:
                if user is not None:
                    if password == "prompt":
                        if sys.stdin.isatty():
                            password = getpass.getpass("Enter Password:")
                        else:
                            password = sys.stdin.readline().strip()
                    password = info.hashpassword(password)

                self.ctrl = BasicRootController(seed_nodes=[seed], user=user,
                                                password=password, use_services_alumni=use_services_alumni, use_services_alt=use_services_alt,
                                                ssl_context=ssl_context, asadm_version=__version__,
                                                only_connect_seed=only_connect_seed, timeout=timeout)

                if not self.ctrl.cluster.get_live_nodes():
                    self.do_exit('')
                    logger.critical("Not able to connect any cluster.")

                self.prompt = "Admin> "
                self.intro = ""
                if not execute_only_mode:
                    self.intro += str(self.ctrl.cluster) + "\n"
                    cluster_visibility_error_nodes = self.ctrl.cluster.get_visibility_error_nodes()

                    if cluster_visibility_error_nodes:
                        self.intro += terminal.fg_red() + "Cluster Visibility error (Please check services list): %s" % (
                            ", ".join(cluster_visibility_error_nodes)) + terminal.fg_clear() + "\n"

                    cluster_down_nodes = self.ctrl.cluster.get_down_nodes()

                    if cluster_down_nodes:
                        self.intro += terminal.fg_red() + "Extra nodes in alumni list: %s" % (
                            ", ".join(cluster_down_nodes)) + terminal.fg_clear() + "\n"

            if self.use_rawinput:
                self.prompt = "\001" + terminal.bold() + terminal.fg_red() + "\002" +\
                              self.prompt + "\001" +\
                              terminal.unbold() + terminal.fg_clear() + "\002"
        except Exception as e:
            self.do_exit('')
            logger.critical(str(e))

        if not execute_only_mode:
            try:
                readline.read_history_file(ADMINHIST)
            except Exception:
                readline.write_history_file(ADMINHIST)

        self.commands = set()

        regex = re.compile("^do_(.*)$")
        commands = map(lambda v: regex.match(v).groups()[0],
                       filter(regex.search, dir(self)))

        for command in commands:
            if command != 'help':
                self.commands.add(command)

    def clean_line(self, line):
        # get rid of extra whitespace
        lexer = shlex.shlex(line)
        # TODO: shlex is not working with 'with' ip addresses. Need to write a
        #       new parser or correct shlex behavior.
        commands = []

        command = []
        build_token = ''
        lexer.wordchars += ".-:/_{}"
        for token in lexer:
            build_token += token
            if token == '-':
                continue

            if token == ';':
                if command:
                    commands.append(command)
                    command = []
            else:
                command.append(build_token)
            build_token = ''
        else:
            if build_token:
                command.append(build_token)
            if command:
                commands.append(command)

        return commands

    def precmd(self, line, max_commands_to_print_header=1,
               command_index_to_print_from=1):

        lines = None

        try:
            lines = self.clean_line(line)

            if not lines:  # allow empty lines
                return ""
        except Exception as e:
            logger.error(str(e))
            return ""

        for line in lines:
            if line[0] in self.commands:
                return " ".join(line)

            if len(lines) > max_commands_to_print_header:
                if len(line) > 1 and any(cmd.startswith(line[0]) for cmd in MULTILEVEL_COMMANDS):
                    index = command_index_to_print_from
                else:
                    # If single level command then print from first index. For example: health, features, grep etc.
                    index = 0

                print "\n~~~ %s%s%s ~~~" % (
                    terminal.bold(), ' '.join(line[index:]), terminal.reset())

            sys.stdout.write(terminal.reset())
            try:
                response = self.ctrl.execute(line)
                if response == "EXIT":
                    return "exit"
            except Exception as e:
                logger.error(str(e))
        return ""  # line was handled by execute

    def _listdir(self, root):
        "List directory 'root' appending the path separator to subdirs."
        res = []
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                name += os.sep
            res.append(name)
        return res

    def _complete_path(self, path=None):
        "Perform completion of filesystem path."
        if not path:
            return self._listdir('.')
        dirname, rest = os.path.split(path)
        tmp = dirname if dirname else '.'
        res = [os.path.join(dirname, p)
               for p in self._listdir(tmp) if p.startswith(rest)]
        # more than one match, or single match which does not exist (typo)
        if len(res) > 1 or not os.path.exists(path):
            return res
        # resolved to a single directory, so return list of files below it
        if os.path.isdir(path):
            return [os.path.join(path, p) for p in self._listdir(path)]
        # exact file match terminates this completion
        return [path + ' ']

    def complete_path(self, args):
        "Completions for the 'extra' command."
        if not args:
            return []

        if args[-1].startswith("\'"):
            names = map(
                lambda v: "\'" + v, self._complete_path(args[-1].split("\'")[-1]))
            return names
        if args[-1].startswith("\""):
            names = map(
                lambda v: "\"" + v, self._complete_path(args[-1].split("\"")[-1]))
            return names

        # treat the last arg as a path and complete it
        return self._complete_path(args[-1])

    def completenames(self, text, line, begidx, endidx):
        try:
            origline = line

            if isinstance(origline, str):
                line = origline.split(" ")
                line = filter(lambda v: v, map(str.strip, line))
                if origline and origline[-1] == ' ':
                    line.append('')

            if len(line) > 0:
                self.ctrl._init_commands()  # dirty
                cmds = self.ctrl.commands.get_key(line[0])
            else:
                cmds = []

            watch = False
            if len(cmds) == 1:
                cmd = cmds[0]
                if cmd == 'help':
                    line.pop(0)
                if cmd == 'watch':
                    watch = True
                    line.pop(0)
                    try:
                        for _ in (1, 2):
                            int(line[0])
                            line.pop(0)
                    except Exception:
                        pass
            line_copy = copy.deepcopy(line)
            names = self.ctrl.complete(line)
            if watch:
                try:
                    names.remove('watch')
                except Exception:
                    pass
            if not names:
                names = self.complete_path(line_copy) + [None]
                return names

        except Exception:
            return []
        return map(lambda n: "%s " % n, names)

    def complete(self, text, state):
        """Return the next possible completion for 'text'.

        If a command has not been entered, then complete against command list.
        Otherwise try to call complete_<command> to get list of completions.
        """
        try:
            if state >= 0:
                origline = readline.get_line_buffer()
                line = origline.lstrip()
                stripped = len(origline) - len(line)
                begidx = readline.get_begidx() - stripped
                endidx = readline.get_endidx() - stripped
                compfunc = self.completenames
                self.completion_matches = compfunc(text, line, begidx, endidx)
        except Exception:
            pass

        try:
            return self.completion_matches[state]
        except IndexError:
            return None

    def emptyline(self):
        # do nothing
        return

    def close(self):
        try:
            self.ctrl.close()
        except Exception:
            pass

    # Other
    def do_exit(self, line):
        self.close()
        if not self.execute_only_mode and readline.get_current_history_length() > 0:
            readline.write_history_file(ADMINHIST)

        return True

    def do_EOF(self, line):
        return self.do_exit(line)

    def do_cake(self, line):
        msg = """
                           *             *
                                                     *
      *                                                               *
               *               (             )
                              (*)           (*)
                       )       |             |       (
              *       (*)     |~|           |~|     (*)
                       |      |S|           |A|      |          *
                      |~|     |P|           |D|     |~|
                      |A|     |I|           |M|     |U|
                     ,|E|a@@@@|K|@@@@@@@@@@@|I|@@@@a|T|.
                .,a@@@|R|@@@@@|E|@@@@@@@@@@@|N|@@@@@|I|@@@@a,.
              ,a@@@@@@|O|@@@@@@@@@@@@.@@@@@@@@@@@@@@|L|@@@@@@@a,
             a@@@@@@@@@@@@@@@@@@@@@\' . `@@@@@@@@@@@@@@@@@@@@@@@@a
             ;`@@@@@@@@@@@@@@@@@@\'   .   `@@@@@@@@@@@@@@@@@@@@@\';
             ;@@@`@@@@@@@@@@@@@\'     .     `@@@@@@@@@@@@@@@@\'@@@;
             ;@@@;,.aaaaaaaaaa       .       aaaaa,,aaaaaaa,;@@@;
             ;;@;;;;@@@@@@@@;@      @.@      ;@@@;;;@@@@@@;;;;@@;
             ;;;;;;;@@@@;@@;;@    @@ . @@    ;;@;;;;@@;@@@;;;;;;;
             ;;;;;;;;@@;;;;;;;  @@   .   @@  ;;;;;;;;;;;@@;;;;@;;
             ;;;;;;;;;;;;;;;;;@@     .     @@;;;;;;;;;;;;;;;;@@@;
         ,%%%;;;;;;;;@;;;;;;;;       .       ;;;;;;;;;;;;;;;;@@;;%%%,
      .%%%%%%;;;;;;;@@;;;;;;;;     ,%%%,     ;;;;;;;;;;;;;;;;;;;;%%%%%%,
     .%%%%%%%;;;;;;;@@;;;;;;;;   ,%%%%%%%,   ;;;;;;;;;;;;;;;;;;;;%%%%%%%,
     %%%%%%%%`;;;;;;;;;;;;;;;;  %%%%%%%%%%%  ;;;;;;;;;;;;;;;;;;;\'%%%%%%%%
     %%%%%%%%%%%%`;;;;;;;;;;;;,%%%%%%%%%%%%%,;;;;;;;;;;;;;;;\'%%%%%%%%%%%%
     `%%%%%%%%%%%%%%%%%,,,,,,,%%%%%%%%%%%%%%%,,,,,,,%%%%%%%%%%%%%%%%%%%%\'
       `%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\'
           `%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\'
"""
        from time import sleep
        s = 0.5
        for line in msg.split('\n'):
            print line
            sleep(s)
            s = s / 1.2
        print terminal.bold() + \
            "Let there be CAKE!".center(80) + \
            terminal.reset()


def do_ctrl_c(*args, **kwargs):
    print "Please press ctrl+d or type exit"


def parse_tls_input(cli_args):
    try:
        return SSLContext(enable_tls=cli_args.enable_tls,
                          encrypt_only=cli_args.encrypt_only, cafile=cli_args.cafile,
                          capath=cli_args.capath, keyfile=cli_args.keyfile,
                          certfile=cli_args.certfile, protocols=cli_args.protocols,
                          cipher_suite=cli_args.cipher_suite,
                          cert_blacklist=cli_args.cert_blacklist,
                          crl_check=cli_args.crl_check,
                          crl_check_all=cli_args.crl_check_all).ctx

    except Exception as e:
        logger.error("SSLContext creation Exception: " + str(e))
        exit(1)


def execute_asinfo_commands(commands_arg, seed, user=None, password=None, ssl_context=None, line_separator=False):
    cmds = [None]

    if commands_arg:
        asinfo_command_pattern = re.compile(r'''((?:[^;"']|"[^"]*"|'[^']*')+)''')

        cmds = asinfo_command_pattern.split(commands_arg)[1::2]
        if not cmds:
            return

    if user is not None:
        if password == "prompt":
            if sys.stdin.isatty():
                password = getpass.getpass("Enter Password:")
            else:
                password = sys.stdin.readline().strip()
        password = info.hashpassword(password)

    assock = ASSocket(seed[0], seed[1], seed[2], user, password, ssl_context)
    if not assock.connect():
        raise Exception("Could not connect to node")

    node_name = "%s:%s" % (seed[0], seed[1])

    for command in cmds:
        if command:
            command = util.strip_string(command)

        result = assock.execute(command)

        if result == -1 or result is None:
            result = IOError("Error: Invalid command '%s'" % command)

        view.CliView.asinfo({node_name: result}, line_separator, False, None)

    return


def main():
    try:
        import argparse
        parser = argparse.ArgumentParser(
            add_help=False, conflict_handler='resolve')
        parser.add_argument("-h", "--host", dest="host", default="127.0.0.1", help="Address (ip/fqdn) of a host in an " +
                            "Aerospike cluster")
        parser.add_argument("-p", "--port", dest="port", type=int,
                            default=3000, help="Aerospike service port used by the host.")
        parser.add_argument("-t", "--tls_name", dest="tls_name",
                            help="TLS name of host to verify for TLS connection. It is required if tls_enable is set.")
        parser.add_argument("-U", "--user", dest="user", help="user name")
        parser.add_argument("-P", "--password", dest="password", nargs="?", const="prompt", help="password")

        parser.add_argument("-c", "--collectinfo", dest="collectinfo", action="store_true",
                            help="Start asadm to run against offline collectinfo files.")
        parser.add_argument("-l", "--log_analyser", dest="log_analyser", action="store_true",
                            help="Start asadm in log-analyser mode and analyse data from log files")
        parser.add_argument("--asinfo", dest="asinfo_mode", action="store_true",
                            # help="Enable asinfo mode to connect directly to seed node without cluster creation. By default asadm connects to all nodes and creates cluster.",
                            help=argparse.SUPPRESS)

        parser.add_argument("-e", "--execute", dest="execute",
                            help="Execute a single or multiple asadm commands and exit. The input value is either string of ';' separated asadm commands or path of file which has asadm commands (ends with ';')")
        parser.add_argument("-o", "--out_file", dest="out_file",
                            help="Path of file to write output of -e command/s")

        parser.add_argument("--no-color", dest="no_color",
                            action="store_true", help="Disable colored output")
        parser.add_argument("--profile", dest="profile", action="store_true",
                            # , help="Profile Aerospike Admin for performance issues"
                            help=argparse.SUPPRESS)

        parser.add_argument("-u", "--help", dest="help", action="store_true", help="show program usage")
        parser.add_argument("--version", dest="show_version",
                            action="store_true", help="Show the version of asadm and exit")

        parser.add_argument("-s", "--services_alumni", dest="use_services_alumni",
                            action="store_true", help="Enable use of services-alumni-list instead of services-list")
        parser.add_argument("-a", "--services_alternate", dest="use_services_alternate",
                            action="store_true", help="Enable use of services-alternate instead of services in info request during cluster tending")
        parser.add_argument("--single_node_cluster", dest="only_connect_seed", action="store_true",
                            help="Enable asadm mode to connect only seed node. By default asadm connects to all nodes in cluster.")
        parser.add_argument("--timeout", dest="timeout", type=float, default=5,
                            help="Set timeout value in seconds to node level operations. TLS connection does not support timeout. Default: 5 seconds")

        parser.add_argument("--lineseperator", dest="line_separator", action="store_true",
                            # help="Print output in separate lines. This works only for asinfo mode."
                            help=argparse.SUPPRESS)

        parser.add_argument("-f", "--file-path", dest="log_path",
                            help="Path of cluster collectinfo file or directory containing collectinfo and system info files."
                                 "This works only for collectinfo-analyser or log-analyser mode.")

        parser.add_argument("--tls_enable", dest="enable_tls", action="store_true",
                            help="Enable TLS on connections. By default TLS is disabled.")
        parser.add_argument("--tls_encrypt_only", dest="encrypt_only", action="store_true",
                            help="Enable mode to do only encryption, so connections won't verify certificates.")
        parser.add_argument("--tls_cafile", dest="cafile", help="Path to a trusted CA certificate file.")
        parser.add_argument("--tls_capath", dest="capath",
                            help="Path to a directory of trusted CA certificates.")
        parser.add_argument("--tls_protocols", dest="protocols", help="Set the TLS protocol selection criteria. This format is the same as Apache's SSLProtocol documented "
                            "at https://httpd.apache.org/docs/current/mod/mod_ssl.html#sslprotocol . "
                            "If not specified the asadm will use '-all +TLSv1.2' if has support for TLSv1.2,"
                            "otherwise it will be '-all +TLSv1'.")
        parser.add_argument("--tls_cipher_suite", dest="cipher_suite", help="Set the TLS cipher selection criteria. The format is the same as Open_sSL's Cipher List Format documented "
                            "at https://www.openssl.org/docs/man1.0.1/apps/ciphers.html")
        parser.add_argument("--tls_keyfile", dest="keyfile",
                            help="Path to the key for mutual authentication (if Aerospike Cluster is supporting it).")
        parser.add_argument("--tls_certfile", dest="certfile",
                            help="Path to the chain file for mutual authentication (if Aerospike Cluster is supporting it).")
        parser.add_argument("--tls_cert_blacklist", dest="cert_blacklist", help="Path to a certificate blacklist file. The file should contain one line for each blacklisted certificate. "
                            "Each line starts with the certificate serial number expressed in hex. "
                            "Each entry may optionally specify the issuer name of the "
                            "certificate (serial numbers are only required to be unique per    "
                            "issuer)."
                            "Example: "
                            "867EC87482B2 /C=US/ST=CA/O=Acme/OU=Engineering/CN=TestChainCA")
        parser.add_argument("--tls_crl_check", dest="crl_check", action="store_true",
                            help="Enable CRL checking for leaf certificate. An error occurs if a valid CRL files cannot be found in tls_capath.")
        parser.add_argument("--tls_crl_check_all", dest="crl_check_all", action="store_true",
                            help="Enable CRL checking for entire certificate chain. An error occurs if a valid CRL files cannot be found in tls_capath.")

        cli_args = parser.parse_args()
    except Exception:
        import optparse
        usage = "usage: %prog [options]"
        parser = optparse.OptionParser(usage, add_help_option=False)
        parser.add_option("-h", "--host", dest="host", default="127.0.0.1", help="Address (ip/fqdn) of a host in an " +
                          "Aerospike cluster")
        parser.add_option("-p", "--port", dest="port", type=int,
                          default=3000, help="Aerospike service port used by the host.")
        parser.add_option("-t", "--tls_name", dest="tls_name",
                          help="TLS name of host to verify for TLS connection. It is required if tls_enable is set.")
        parser.add_option("-U", "--user", dest="user", help="user name")
        parser.add_option("-P", "--password", dest="password", action="store_const",  # , nargs="?"
                          const="prompt", help="password")

        parser.add_option("-c", "--collectinfo", dest="collectinfo", action="store_true",
                          help="Start asadm to run against offline collectinfo files.")
        parser.add_option("-l", "--log_analyser", dest="log_analyser", action="store_true",
                          help="Start asadm in log-analyser mode and analyse data from log files")
        parser.add_option("--asinfo_mode", dest="asinfo_mode", action="store_true",
                          # help="Enable asinfo mode to connect directly to seed node without cluster creation. By default asadm connects to all nodes and creates cluster."
                          help=optparse.SUPPRESS_USAGE)

        parser.add_option("-e", "--execute", dest="execute",
                          help="Execute a single or multiple asadm commands and exit. The input value is either string of ';' separated asadm commands or path of file which has asadm commands (ends with ';')")
        parser.add_option("-o", "--out_file", dest="out_file",
                          help="Path of file to write output of -e command/s")

        parser.add_option("--no-color", dest="no_color",
                          action="store_true", help="Disable colored output")
        parser.add_option("--profile", dest="profile", action="store_true",  # , help="Profile Aerospike Admin for performance issues"
                          help=optparse.SUPPRESS_USAGE)

        parser.add_option("-u", "--help", dest="help", action="store_true", help="show program usage")
        parser.add_option("--version", dest="show_version",
                          action="store_true", help="Show the version of asadm and exit")

        parser.add_option("-s", "--services_alumni", dest="use_services_alumni",
                          action="store_true", help="Enable use of services-alumni-list instead of services-list")
        parser.add_option("-a", "--services_alternate", dest="use_services_alternate",
                          action="store_true", help="Enable use of services-alternate instead of services in info request during cluster tending")
        parser.add_option("--single_node_cluster", dest="only_connect_seed", action="store_true",
                          help="Enable asadm mode to connect only seed node. By default asadm connects to all nodes in cluster.")
        parser.add_option("--timeout", dest="timeout", type=float, default=5,
                          help="Set timeout value in seconds to node level operations. TLS connection does not support timeout. Default: 5 seconds")

        parser.add_option("--lineseperator", dest="line_separator", action="store_true",
                          # help="Print output in separate lines. This works only for asinfo mode."
                          help=optparse.SUPPRESS_USAGE)

        parser.add_option("-f", "--file-path", dest="log_path",
                          help="Path of cluster collectinfo file or directory containing collectinfo and system info files.")

        parser.add_option("--tls_enable", dest="enable_tls", action="store_true",
                          help="Enable TLS on connections. By default TLS is disabled.")
        parser.add_option("--tls_encrypt_only", dest="encrypt_only", action="store_true",
                          help="Enable mode to do only encryption, so connections won't verify certificates.")
        parser.add_option("--tls_cafile", dest="cafile", help="Path to a trusted CA certificate file.")
        parser.add_option("--tls_capath", dest="capath",
                          help="Path to a directory of trusted CA certificates.")
        parser.add_option("--tls_protocols", dest="protocols", help="Set the TLS protocol selection criteria. This format is the same as Apache's SSLProtocol documented "
                          "at https://httpd.apache.org/docs/current/mod/mod_ssl.html#sslprotocol . "
                          "If not specified the asadm will use '-all +TLSv1.2' if has support for TLSv1.2,"
                          "otherwise it will be '-all +TLSv1'.")
        parser.add_option("--tls_cipher_suite", dest="cipher_suite", help="Set the TLS cipher selection criteria. The format is the same as Open_sSL's Cipher List Format documented "
                          "at https://www.openssl.org/docs/man1.0.1/apps/ciphers.html")
        parser.add_option("--tls_keyfile", dest="keyfile",
                          help="Path to the key for mutual authentication (if Aerospike Cluster is supporting it).")
        parser.add_option("--tls_certfile", dest="certfile",
                          help="Path to the chain file for mutual authentication (if Aerospike Cluster is supporting it).")
        parser.add_option("--tls_cert_blacklist", dest="cert_blacklist", help="Path to a certificate blacklist file. The file should contain one line for each blacklisted certificate. "
                          "Each line starts with the certificate serial number expressed in hex. "
                          "Each entry may optionally specify the issuer name of the "
                          "certificate (serial numbers are only required to be unique per    "
                          "issuer)."
                          "Example: "
                          "867EC87482B2 /C=US/ST=CA/O=Acme/OU=Engineering/CN=TestChainCA")
        parser.add_option("--tls_crl_check", dest="crl_check", action="store_true",
                          help="Enable CRL checking for leaf certificate. An error occurs if a valid CRL files cannot be found in tls_capath.")
        parser.add_option("--tls_crl_check_all", dest="crl_check_all", action="store_true",
                          help="Enable CRL checking for entire certificate chain. An error occurs if a valid CRL files cannot be found in tls_capath.")

        (cli_args, args) = parser.parse_args()

    if cli_args.help:
        parser.print_help()
        exit(0)

    if cli_args.show_version:
        print __version__
        exit(0)

    if cli_args.no_color:
        disable_coloring()

    if cli_args.use_services_alumni and cli_args.use_services_alternate:
        print "Aerospike does not support alternate address for alumni services. Please enable only one of services_alumni or services_alternate."
        exit(1)

    if not os.path.isdir(ADMIN_HOME):
        os.makedirs(ADMIN_HOME)

    seed = (cli_args.host, cli_args.port, cli_args.tls_name)

    execute_only_mode = False
    if cli_args.execute:
        execute_only_mode = True

    ssl_context = parse_tls_input(cli_args)

    if cli_args.asinfo_mode:

        if cli_args.collectinfo or cli_args.log_analyser:
            print "asinfo mode can not work with Collectinfo-analyser or Log-analyser mode."
            exit(1)

        commands_arg = cli_args.execute
        if commands_arg and os.path.isfile(commands_arg):
            commands_arg = parse_commands(commands_arg)

        try:
            execute_asinfo_commands(
                commands_arg, seed, user=cli_args.user, password=cli_args.password,
                ssl_context=ssl_context, line_separator=cli_args.line_separator)
            exit(0)
        except Exception as e:
            logger.error(str(e))
            exit(1)

    if not execute_only_mode:
        readline.set_completer_delims(' \t\n;')

    shell = AerospikeShell(seed, user=cli_args.user,
                           password=cli_args.password,
                           use_services_alumni=cli_args.use_services_alumni,
                           use_services_alt=cli_args.use_services_alternate,
                           log_path=cli_args.log_path,
                           log_analyser=cli_args.log_analyser,
                           collectinfo=cli_args.collectinfo,
                           ssl_context=ssl_context,
                           only_connect_seed=cli_args.only_connect_seed,
                           execute_only_mode=execute_only_mode, timeout=cli_args.timeout)

    use_yappi = False
    if cli_args.profile:
        try:
            import yappi
            use_yappi = True
        except Exception as a:
            print "Unable to load profiler"
            print "Yappi Exception:"
            print str(a)
            exit(1)

    func = None
    args = ()
    single_command = True
    real_stdout = sys.stdout
    if not execute_only_mode:
        func = shell.cmdloop
        single_command = False
    else:
        commands_arg = cli_args.execute
        max_commands_to_print_header = 1
        command_index_to_print_from = 1
        if os.path.isfile(commands_arg):
            commands_arg = parse_commands(commands_arg)
            max_commands_to_print_header = 0
            command_index_to_print_from = 0

        if cli_args.out_file:
            try:
                f = open(str(cli_args.out_file), "w")
                sys.stdout = f
                disable_coloring()
                max_commands_to_print_header = 0
                command_index_to_print_from = 0
            except Exception as e:
                print e

        line = shell.precmd(commands_arg,
                            max_commands_to_print_header=max_commands_to_print_header,
                            command_index_to_print_from=command_index_to_print_from)

        shell.onecmd(line)
        func = shell.onecmd
        args = (line,)

    cmdloop(shell, func, args, use_yappi, single_command)
    shell.close()
    try:
        sys.stdout = real_stdout
        if f:
            f.close()
    except Exception:
        pass


def disable_coloring():
    from lib.view import terminal
    terminal.enable_color(False)


def cmdloop(shell, func, args, use_yappi, single_command):
    try:
        if use_yappi:
            import yappi
            yappi.start()
            func(*args)
            yappi.get_func_stats().print_all()
        else:
            func(*args)
    except (KeyboardInterrupt, SystemExit):
        if not single_command:
            shell.intro = terminal.fg_red() + \
                "\nTo exit asadm utility please run exit command." + \
                terminal.fg_clear()
        cmdloop(shell, func, args, use_yappi, single_command)


def parse_commands(file):
    commands = ""
    commented = False
    for line in open(file, 'r').readlines():
        if not line or not line.strip():
            continue
        if commented:
            if line.strip().endswith(CMD_FILE_MULTI_LINE_COMMENT_END):
                commented = False
            continue
        if line.strip().startswith(CMD_FILE_SINGLE_LINE_COMMENT_START):
            continue
        if line.strip().startswith(CMD_FILE_MULTI_LINE_COMMENT_START):
            if not line.strip().endswith(CMD_FILE_MULTI_LINE_COMMENT_END):
                commented = True
            continue
        try:
            commands = commands + line
        except Exception:
            commands = line
    return commands


if __name__ == '__main__':
    main()
