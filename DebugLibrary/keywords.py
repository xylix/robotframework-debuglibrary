import sys

from robot.libraries.BuiltIn import run_keyword_variant

from .debugcmd import DebugCmd
from .globals import context
from .robotkeyword import run_debug_if
from .steplistener import RobotLibraryStepListener
from .styles import print_output


class DebugKeywords(RobotLibraryStepListener):
    """Debug Keywords for RobotFramework."""

    def debug(self):
        """Open a interactive shell, run any RobotFramework keywords.

        Keywords separated by two space or one tab, and Ctrl-D to exit.
        """
        # re-wire stdout so that we can use the cmd module and have readline
        # support
        old_stdout = sys.stdout
        sys.stdout = sys.__stdout__

        show_intro = not context.in_step_mode
        if show_intro:
            print_output('\n>>>>>', 'Enter interactive shell')

        self.debug_cmd = DebugCmd()
        if show_intro:
            self.debug_cmd.cmdloop()
        else:
            self.debug_cmd.cmdloop(intro='')

        show_intro = not context.in_step_mode
        if show_intro:
            print_output('\n>>>>>', 'Exit shell.')

        # put stdout back where it was
        sys.stdout = old_stdout

    @run_keyword_variant(resolve=1)
    def debug_if(self, condition, *args):
        """Runs the Debug keyword if condition is true."""
        return run_debug_if(condition, *args)
