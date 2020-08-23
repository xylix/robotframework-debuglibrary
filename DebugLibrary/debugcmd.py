import cmd
import os
from functools import cached_property

from prompt_toolkit import PromptSession
from robot.api import logger
from robot.libraries import STDLIBS
from robot.libraries.BuiltIn import BuiltIn
from robot.errors import ExecutionFailed, HandlerExecutionFailed
from robot.running.signalhandler import STOP_SIGNAL_MONITOR

from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import CompleteStyle, prompt
from .cmdcompleter import CmdCompleter
from .globals import context
from .robotkeyword import get_lib_keywords, find_keyword, run_keyword
from .robotlib import get_libs, get_libs_dict, match_libs
from .sourcelines import RobotNeedUpgrade, print_source_lines, print_test_case_lines
from .styles import (
    DEBUG_PROMPT_STYLE,
    get_debug_prompt_tokens,
    print_error,
    print_output,
)
from .utils import start_selenium_commands, SELENIUM_WEBDRIVERS

HISTORY_PATH = os.environ.get("RFDEBUG_HISTORY", "~/.rfdebug_history")


def reset_robotframework_exception():
    """Resume RF after press ctrl+c during keyword running."""
    if STOP_SIGNAL_MONITOR._signal_count:
        STOP_SIGNAL_MONITOR._signal_count = 0
        STOP_SIGNAL_MONITOR._running_keyword = True
        logger.info("Reset last exception of DebugLibrary")


def run_robot_command(robot_instance, command):
    """Run command in robotframewrk environment."""
    if not command:
        return

    result = ""
    try:
        result = run_keyword(robot_instance, command)
    except HandlerExecutionFailed as exc:
        print_error("! keyword:", command)
        print_error("! handler execution failed:", exc.full_message)
    except ExecutionFailed as exc:
        print_error("! keyword:", command)
        print_error("! execution failed:", str(exc))
    except Exception as exc:
        print_error("! keyword:", command)
        print_error("! FAILED:", repr(exc))

    if result:
        head, message = result
        print_output(head, message)


def do_pdb():
    """Enter the python debugger pdb. For development only."""
    print("break into python debugger: pdb")
    import pdb

    pdb.set_trace()


def complete_keywords(line):
    """Complete keywords command."""
    if len(line.split()) == 2:
        command, lib_name = line.split()
        return match_libs(lib_name)
    elif len(line.split()) == 1 and line.endswith(" "):
        return [_.name for _ in get_libs()]
    return []


def do_keywords(args) -> None:
    lib_name = args
    matched = match_libs(lib_name)
    if not matched:
        print_error("< not found library", lib_name)
        return
    libs = get_libs_dict()
    for name in matched:
        lib = libs[name]
        print_output("< Keywords of library", name)
        for keyword in get_lib_keywords(lib):
            print_output(f"   {keyword['name']}\t", keyword["summary"])


def complete_libs(line):
    if len(line.split()) == 1 and line.endswith(" "):
        return ["-s"]
    return []


def _print_lib_info(lib, with_source_path=False):
    print_output(f"   {lib.name}", lib.version)
    if lib.doc:
        logger.console("       {}".format(lib.doc.split("\n")[0]))
    if with_source_path:
        logger.console(f"       {lib.source}")


def do_docs(keyword_name):
    keywords = find_keyword(keyword_name)
    if not keywords:
        print_error("< not find keyword", keyword_name)
    elif len(keywords) == 1:
        logger.console(keywords[0]["doc"])
    else:
        print_error(f"< found {len(keywords)} keywords", ", ".join(keywords))


def list_source(longlist=False):
    if not context.in_step_mode:
        print("Please run `step` or `next` command first.")
        return

    if longlist:
        print_function = print_test_case_lines
    else:
        print_function = print_source_lines

    try:
        print_function(context.current_source_path, context.current_source_lineno)
    except RobotNeedUpgrade:
        print("Please upgrade robotframework to support list source code:")
        print('    pip install "robotframework>=3.2" -U')


def do_libs(args):
    print_output("<", "Imported libraries:")
    for lib in get_libs():
        _print_lib_info(lib, with_source_path="-s" in args)
    print_output("<", "Builtin libraries:")
    for name in sorted(list(STDLIBS)):
        print_output("   " + name, "")


def complete_selenium(line):
    if len(line.split()) == 3:
        command, url, driver_name = line.lower().split()
        return [
            driver for driver in SELENIUM_WEBDRIVERS if driver.startswith(driver_name)
        ]
    elif len(line.split()) == 2 and line.endswith(" "):
        return SELENIUM_WEBDRIVERS
    return []


class PromptToolkitCmd(cmd.Cmd):
    """CMD shell using prompt-toolkit."""

    prompt_style = DEBUG_PROMPT_STYLE
    intro = """\
Only accepted plain text format keyword separated with two or more spaces.
Type "help" for more information.\
"""
    prompt = "> "
    repeat_last_nonempty_command = False

    def __init__(self):
        # Defaults are tab completion with stdin None stdout None
        super().__init__()
        self.robot = BuiltIn()
        self.history = FileHistory(os.path.expanduser(HISTORY_PATH))

    def help_help(self):
        """Help of Help command"""
        print("Show help message.")

    def get_cmd_names(self):
        """Get all command names of CMD shell."""
        pre = "do_"
        cut = len(pre)
        return [_[cut:] for _ in self.get_names() if _.startswith(pre)]

    def get_help_string(self, command_name):
        """Get help document of command."""
        func = getattr(self, f"do_{command_name}", None)
        if not func:
            return ""
        return func.__doc__

    def get_helps(self):
        """Get all help documents of commands."""
        return [
            (name, self.get_help_string(name) or name) for name in self.get_cmd_names()
        ]

    def _get_input(self):
        if self.cmdqueue:
            return self.cmdqueue.pop(0)
        else:
            try:
                return self.get_input()
            except KeyboardInterrupt:
                return

    @cached_property
    def session(self):
        session = PromptSession(
            history=self.history,
            auto_suggest=AutoSuggestFromHistory(),
            enable_history_search=True,
            completer=self.get_completer(),
            complete_style=CompleteStyle.MULTI_COLUMN,
            style=self.prompt_style,
            message=get_debug_prompt_tokens(self.prompt)
        )
        return session

    def get_input(self):
        try:
            line = self.session.prompt()
        except EOFError:
            line = "EOF"
        return line

    def postcmd(self, stop, line):
        """Run after a command."""
        return stop

    def pre_loop_iter(self):
        """Reset robotframework before every loop iteration."""
        reset_robotframework_exception()

    def do_help(self, arg):
        """Show help message."""
        if not arg.strip():
            print(
                """\
Input Robotframework keywords, or commands listed below.
Use "libs" or "l" to see available libraries,
use "keywords" or "k" see the list of library keywords,
use the TAB keyboard key to autocomplete keywords.
Access https://github.com/xyb/robotframework-debuglibrary for more details.\
"""
            )
        super().do_help(arg)

    def _print_lib_info(self, lib, with_source_path):
        return _print_lib_info(lib, with_source_path)

    def get_completer(self):
        """Get completer instance specified for robotframework."""
        return CmdCompleter(self)

    def do_selenium(self, arg):
        """Start a selenium webdriver and open url in browser you expect.

        selenium  [<url>]  [<browser>]

        default url is google.com, default browser is firefox.
        """

        for command in start_selenium_commands(arg):
            print_output("#", command)
            run_robot_command(self.robot, command)

    def complete_selenium(self, text, line, begin_idx, end_idx):
        """Complete selenium command."""
        complete_selenium(line)

    def default(self, line):
        """Run RobotFramework keywords."""
        command = line.strip()

        run_robot_command(self.robot, command)

    def complete_libs(self, text, line, begin_idx, end_idx):
        """Complete  libs """
        return complete_libs(line)

    def do_libs(self, args):
        """Print imported and builtin libraries, with source if `-s` specified.

        ls( libs ) [-s]
        """
        return do_libs(args)

    def complete_keywords(self, text, line, begin_idx, end_idx):
        """Complete keywords command."""
        """ Is the interface necessary for robot support?"""
        return complete_keywords(line)

    def do_keywords(self, args):
        """Print keywords of libraries, all or starts with <lib_name>.

         k(eywords) [<lib_name>]
         """
        return do_keywords(args)

    def do_docs(self, keyword_name):
        """Get keyword documentation for individual keywords.

         d(ocs) [<keyword_name>]
        """
        return do_docs(keyword_name)

    def emptyline(self):
        """Repeat last nonempty command if in step mode."""
        self.repeat_last_nonempty_command = context.in_step_mode
        if self.repeat_last_nonempty_command:
            return super().emptyline()

    def append_command(self, command):
        """Append a command to queue."""
        self.cmdqueue.append(command)

    def append_exit(self):
        """Append exit command to queue."""
        self.append_command("exit")

    def do_step(self, args):
        """Execute the current line, stop at the first possible occasion."""
        context.in_step_mode = True
        self.append_exit()  # pass control back to robot runner

    def do_next(self, args):
        """Continue execution until the next line is reached or it returns."""
        self.do_step(args)

    def do_continue(self, args):
        """Continue execution."""
        self.do_exit(args)

    def list_source(self, longlist=False):
        """List source code."""
        return list_source(longlist)

    def do_list(self, args):
        """List source code for the current file."""

        return list_source(longlist=False)

    def do_longlist(self, args):
        """List the whole source code for the current test case."""

        return list_source(longlist=True)

    def do_exit(self, args):
        """Exit the interpreter. You can also use the Ctrl-D shortcut."""
        context.in_step_mode = False  # explicitly exit REPL will disable step mode
        self.append_exit()
        return True

    def onecmd(self, line):
        # restore last command acrossing different Cmd instances
        self.lastcmd = context.last_command
        stop = super().onecmd(line)
        context.last_command = self.lastcmd
        return stop

    def loop_once(self):
        self.pre_loop_iter()
        line = self._get_input()
        if line is None:
            return

        if line == "exit":
            line = "EOF"

        line = self.precmd(line)
        if line == "EOF":
            # do not run 'EOF' command to avoid override 'lastcmd'
            stop = True
        else:
            stop = self.onecmd(line)
        stop = self.postcmd(stop, line)
        return stop

    def cmdloop(self, intro=None):
        """Better command loop.

        override default cmdloop method
        """
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(self.intro)
            self.stdout.write("\n")

        self.preloop()

        stop = None
        while not stop:
            stop = self.loop_once()

        self.postloop()

    def do_pdb(self, arg):
        """Enter the python debugger pdb. For development only."""
        do_pdb()

    do_EOF = do_exit
    do_ll = do_longlist
    do_l = do_list
    do_c = do_continue
    do_n = do_next
    do_s = do_step
    do_d = do_docs
    complete_k = complete_keywords
    do_k = do_keywords
    complete_l = complete_libs
    do_ls = do_libs
    complete_s = complete_selenium


class DebugCmd(PromptToolkitCmd):
    """Interactive debug shell for robotframework."""
