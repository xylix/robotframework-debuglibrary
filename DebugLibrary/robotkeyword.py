import re

from robot.libraries.BuiltIn import BuiltIn
from robot.libdocpkg.robotbuilder import KeywordDocBuilder, LibraryDocBuilder
from robot.libdocpkg.model import LibraryDoc

from .robotlib import get_libs

try:
    from robot.variables.search import is_variable
except ImportError:
    from robot.variables import is_var as is_variable  # robotframework < 3.2

KEYWORD_SEP = re.compile("  +|\t")

_lib_keywords_cache = {}


def assign_variable(robot_instance, variable_name, args):
    """Assign a robotframework variable."""
    variable_value = robot_instance.run_keyword(*args)
    robot_instance._variables.__setitem__(variable_name, variable_value)
    return variable_value


def parse_keyword(command):
    """Split a robotframework keyword string."""
    # TODO use robotframework functions
    return KEYWORD_SEP.split(command)


class ImportedLibraryDocBuilder(LibraryDocBuilder):
    def build(self, lib):
        libdoc = LibraryDoc(
            name=lib.name, doc=self._get_doc(lib), doc_format=lib.doc_format,
        )
        libdoc.inits = self._get_initializers(lib)
        libdoc.keywords = KeywordDocBuilder().build_keywords(lib)
        return libdoc


def get_lib_keywords(library):
    """Get keywords of imported library."""
    if library.name in _lib_keywords_cache:
        return _lib_keywords_cache[library.name]

    lib = ImportedLibraryDocBuilder().build(library)
    keywords = []
    for keyword in lib.keywords:
        keywords.append(
            {
                "name": keyword.name,
                "lib": library.name,
                "doc": keyword.doc,
                "summary": keyword.doc.split("\n")[0],
            }
        )

    _lib_keywords_cache[library.name] = keywords
    return keywords


def get_keywords():
    """Get all keywords of libraries."""
    for lib in get_libs():
        yield from get_lib_keywords(lib)


def find_keyword(keyword_name):
    keyword_name = keyword_name.lower()
    return [
        keyword
        for lib in get_libs()
        for keyword in get_lib_keywords(lib)
        if keyword["name"].lower() == keyword_name
    ]


def _execute_variable(robot_instance, variable_name, keyword, args):
    variable_only = not args
    if variable_only:
        display_value = ["Log to console", keyword]
        robot_instance.run_keyword(*display_value)
    else:
        variable_value = assign_variable(robot_instance, variable_name, args,)
        echo = "{0} = {1!r}".format(variable_name, variable_value)
        return ("#", echo)


def run_keyword(robot_instance, keyword):
    """Run a keyword in robotframewrk environment."""
    if not keyword:
        return

    keyword_args = parse_keyword(keyword)
    keyword = keyword_args[0]
    args = keyword_args[1:]

    is_comment = keyword.strip().startswith("#")
    if is_comment:
        return

    variable_name = keyword.rstrip("= ")
    if is_variable(variable_name):
        return _execute_variable(robot_instance, variable_name, keyword, args)
    else:
        output = robot_instance.run_keyword(keyword, *args)
        if output:
            return ("<", repr(output))


def run_debug_if(condition, *args):
    """Runs DEBUG if condition is true."""

    return BuiltIn().run_keyword_if(condition, "DebugLibrary.DEBUG", *args)
