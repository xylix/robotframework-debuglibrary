import os

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn
from robot.errors import ExecutionFailed, HandlerExecutionFailed
from robot.running.signalhandler import STOP_SIGNAL_MONITOR

from .cmdcompleter import CmdCompleter
from .globals import context
from .prompttoolkitcmd import PromptToolkitCmd
from .robotkeyword import (get_keywords, get_lib_keywords, find_keyword,
                           run_keyword)
from .robotlib import get_builtin_libs, get_libs, get_libs_dict, match_libs
from .sourcelines import (RobotNeedUpgrade, print_source_lines,
                          print_test_case_lines)
from .steplistener import is_step_mode, set_step_mode
from .styles import (DEBUG_PROMPT_STYLE, get_debug_prompt_tokens, print_error,
                     print_output)

HISTORY_PATH = os.environ.get('RFDEBUG_HISTORY', '~/.rfdebug_history')

def reset_robotframework_exception():
    """Resume RF after press ctrl+c during keyword running."""
    if STOP_SIGNAL_MONITOR._signal_count:
        STOP_SIGNAL_MONITOR._signal_count = 0
        STOP_SIGNAL_MONITOR._running_keyword = True
        logger.info('Reset last exception of DebugLibrary')


def run_robot_command(robot_instance, command):
    """Run command in robotframewrk environment."""
    if not command:
        return

    result = ''
    try:
        result = run_keyword(robot_instance, command)
    except HandlerExecutionFailed as exc:
        print_error('! keyword:', command)
        print_error('! handler execution failed:', exc.full_message)
    except ExecutionFailed as exc:
        print_error('! keyword:', command)
        print_error('! execution failed:', str(exc))
    except Exception as exc:
        print_error('! keyword:', command)
        print_error('! FAILED:', repr(exc))

    if result:
        head, message = result
        print_output(head, message)


class DebugCmd(PromptToolkitCmd):
    """Interactive debug shell for robotframework."""

    prompt_style = DEBUG_PROMPT_STYLE

    def __init__(self, completekey='tab', stdin=None, stdout=None):
        PromptToolkitCmd.__init__(self, completekey, stdin, stdout,
                                  history_path=HISTORY_PATH)
        self.robot = BuiltIn()

    def get_prompt_tokens(self, prompt_text):
        return get_debug_prompt_tokens(prompt_text)

    def postcmd(self, stop, line):
        """Run after a command."""
        return stop

    def pre_loop_iter(self):
        """Reset robotframework before every loop iteration."""
        reset_robotframework_exception()

    def do_help(self, arg):
        """Show help message."""
        if not arg.strip():
            print('''\
Input Robotframework keywords, or commands listed below.
Use "libs" or "l" to see available libraries,
use "keywords" or "k" see the list of library keywords,
use the TAB keyboard key to autocomplete keywords.
Access https://github.com/xyb/robotframework-debuglibrary for more details.\
''')

        PromptToolkitCmd.do_help(self, arg)

    def get_completer(self):
        """Get completer instance specified for robotframework."""
        # commands
        commands = [(cmd_name, cmd_name, 'DEBUG command: {0}'.format(doc))
                    for cmd_name, doc in self.get_helps()]

        # libraries
        for lib in get_libs():
            commands.append((
                lib.name,
                lib.name,
                'Library: {0} {1}'.format(lib.name, lib.version),
            ))

        # keywords
        for keyword in get_keywords():
            # name with library
            name = '{0}.{1}'.format(keyword['lib'], keyword['name'])
            commands.append((
                name,
                keyword['name'],
                'Keyword: {0}'.format(keyword['summary']),
            ))
            # name without library
            commands.append((
                keyword['name'],
                keyword['name'],
                'Keyword[{0}.]: {1}'.format(keyword['lib'],
                                            keyword['summary']),
            ))

        return CmdCompleter(commands, self)

    def do_selenium(self, arg):
        """Start a selenium webdriver and open url in browser you expect.

        selenium  [<url>]  [<browser>]

        default url is google.com, default browser is firefox.
        """

        for command in start_selenium_commands(arg):
            print_output('#', command)
            run_robot_command(self.robot, command)

    def complete_selenium(self, text, line, begin_idx, end_idx):
        """Complete selenium command."""
        if len(line.split()) == 3:
            command, url, driver_name = line.lower().split()
            return [driver for driver in SELENIUM_WEBDRIVERS
                    if driver.startswith(driver_name)]
        elif len(line.split()) == 2 and line.endswith(' '):
            return SELENIUM_WEBDRIVERS
        return []

    complete_s = complete_selenium

    def default(self, line):
        """Run RobotFramework keywords."""
        command = line.strip()

        run_robot_command(self.robot, command)

    def _print_lib_info(self, lib, with_source_path=False):
        print_output('   {}'.format(lib.name), lib.version)
        if lib.doc:
            logger.console('       {}'.format(lib.doc.split('\n')[0]))
        if with_source_path:
            logger.console('       {}'.format(lib.source))

    def do_libs(self, args):
        """Print imported and builtin libraries, with source if `-s` specified.

        ls( libs ) [-s]
        """
        print_output('<', 'Imported libraries:')
        for lib in get_libs():
            self._print_lib_info(lib, with_source_path='-s' in args)
        print_output('<', 'Builtin libraries:')
        for name in sorted(get_builtin_libs()):
            print_output('   ' + name, '')

    do_ls = do_libs

    def complete_libs(self, text, line, begin_idx, end_idx):
        """Complete libs command."""
        if len(line.split()) == 1 and line.endswith(' '):
            return ['-s']
        return []

    complete_l = complete_libs

    def do_keywords(self, args):
        """Print keywords of libraries, all or starts with <lib_name>.

        k(eywords) [<lib_name>]
        """
        lib_name = args
        matched = match_libs(lib_name)
        if not matched:
            print_error('< not found library', lib_name)
            return
        libs = get_libs_dict()
        for name in matched:
            lib = libs[name]
            print_output('< Keywords of library', name)
            for keyword in get_lib_keywords(lib):
                print_output('   {}\t'.format(keyword['name']),
                             keyword['summary'])

    do_k = do_keywords

    def complete_keywords(self, text, line, begin_idx, end_idx):
        """Complete keywords command."""
        if len(line.split()) == 2:
            command, lib_name = line.split()
            return match_libs(lib_name)
        elif len(line.split()) == 1 and line.endswith(' '):
            return [_.name for _ in get_libs()]
        return []

    complete_k = complete_keywords

    def do_docs(self, keyword_name):
        """Get keyword documentation for individual keywords.

         d(ocs) [<keyword_name>]
        """

        keywords = find_keyword(keyword_name)
        if not keywords:
            print_error('< not find keyword', keyword_name)
        elif len(keywords) == 1:
            logger.console(keywords[0]['doc'])
        else:
            print_error('< found {} keywords'.format(len(keywords)),
                        ', '.join(keywords))

    do_d = do_docs

    def emptyline(self):
        """Repeat last nonempty command if in step mode."""
        self.repeat_last_nonempty_command = is_step_mode()
        return super(DebugCmd, self).emptyline()

    def append_command(self, command):
        """Append a command to queue."""
        self.cmdqueue.append(command)

    def append_exit(self):
        """Append exit command to queue."""
        self.append_command('exit')

    def do_step(self, args):
        """Execute the current line, stop at the first possible occasion."""
        set_step_mode(on=True)
        self.append_exit()  # pass control back to robot runner

    do_s = do_step

    def do_next(self, args):
        """Continue execution until the next line is reached or it returns."""
        self.do_step(args)

    do_n = do_next

    def do_continue(self, args):
        """Continue execution."""
        self.do_exit(args)

    do_c = do_continue

    def do_list(self, args):
        """List source code for the current file."""

        self.list_source(longlist=False)

    do_l = do_list

    def do_longlist(self, args):
        """List the whole source code for the current test case."""

        self.list_source(longlist=True)

    do_ll = do_longlist

    def list_source(self, longlist=False):
        """List source code."""
        if not is_step_mode():
            print('Please run `step` or `next` command first.')
            return

        if longlist:
            print_function = print_test_case_lines
        else:
            print_function = print_source_lines

        try:
            print_function(context.current_source_path,
                           context.current_source_lineno)
        except RobotNeedUpgrade:
            print('Please upgrade robotframework to support list source code:')
            print('    pip install "robotframework>=3.2" -U')

    def do_exit(self, args):
        """Exit debug shell."""
        set_step_mode(on=False)  # explicitly exit REPL will disable step mode
        self.append_exit()
        return super(DebugCmd, self).do_exit(args)

    def onecmd(self, line):
        # restore last command acrossing different Cmd instances
        self.lastcmd = context.last_command
        stop = super(DebugCmd, self).onecmd(line)
        context.last_command = self.lastcmd
        return stop
