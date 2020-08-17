from .robotkeyword import parse_keyword
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from functools import wraps

SELENIUM_WEBDRIVERS = ['firefox', 'chrome', 'ie',
                       'opera', 'safari', 'phantomjs', 'remote']

def start_selenium_commands(arg):
    """Start a selenium webdriver and open url in browser you expect.

    arg:  [<url> or google]  [<browser> or firefox]
    """
    yield 'import library  SeleniumLibrary'

    # Set defaults, overriden if args set
    url = 'http://www.google.com/'
    browser = 'firefox'
    if arg:
        args = parse_keyword(arg)
        if len(args) == 2:
            url, browser = args
        else:
            url = arg
    if '://' not in url:
        url = 'http://' + url

    yield 'open browser  %s  %s' % (url, browser)


def memoize(function):
    """Memoization decorator"""
    memo = {}

    @wraps(function)
    def wrapper(*args, **kwargs):
        key = (args, frozenset(sorted(kwargs.items())))

        if key in memo:
            return memo[key]

        rv = function(*args, **kwargs)
        memo[key] = rv
        return rv
    return wrapper
