#!/usr/bin/env python

import pytest

import pexpect
from robot.version import get_version

TIMEOUT_SECONDS = 2

child = None


def check_result(pattern):
    index = child.expect([pattern, pexpect.EOF, pexpect.TIMEOUT],
                         timeout=TIMEOUT_SECONDS)
    try:
        assert index == 0
    except AssertionError:
        print('\n==== Screen buffer raw ====\n',
              child._buffer.getvalue(),
              '\n^^^^ Screen buffer raw ^^^^')
        print('==== Screen buffer ====\n',
              child._buffer.getvalue().decode('utf8'),
              '\n^^^^ Screen buffer ^^^^')
        raise


def check_prompt(keys, pattern):
    child.write(keys)
    check_result(pattern)
    child.write('\003')  # ctrl-c: reset inputs


def check_command(command, pattern):
    child.sendline(command)
    check_result(pattern)

@pytest.fixture
def child():
    global child
    child = pexpect.spawn('coverage', ['run', '--append', 'DebugLibrary/shell.py'])
    child.expect('Enter interactive shell', timeout=TIMEOUT_SECONDS * 3)
    yield child

    check_command('exit', 'Exit shell.')
    child.wait()

@pytest.fixture
def robot_child():
    global child
    # Command "coverage run robot tests/step.robot" does not work,
    # so start the program using DebugLibrary's shell instead of "robot".
    child = pexpect.spawn('coverage',
                          ['run', '--append', 'DebugLibrary/shell.py',
                           'tests/step.robot'])
    child.expect('Type "help" for more information.*>',
                 timeout=TIMEOUT_SECONDS * 3)
    yield child
    # Exit the debug mode started by Debug keyword.
    check_command('c',  # continue
                  'Exit shell.*'
                  'another test case.*'
                  'end')
    # Exit the interactive shell started by "DebugLibrary/shell.py".
    check_command('c', 'Report: ')
    child.wait()



def test_autocomplete(child):
    check_prompt('key\t', 'keywords')
    check_prompt('key\t', 'Keyword Should Exist')
    check_prompt('k \t', 'keywords.*Keyword Should Exist')
    check_prompt('keywords  \t', 'BuiltIn.*DebugLibrary')
    check_prompt('keywords  debug\t', 'DebugLibrary')
    #check_prompt('debu\t', 'DebugLibrary')
    #check_prompt('DebugLibrary.\t', 'Debug If')
    check_prompt('get\t', 'Get Count')
    check_prompt('get\t', 'Get Time')
    # check_prompt('selenium  http://google.com  \t', 'firefox.*chrome')
    # check_prompt('selenium  http://google.com  fire\t', 'firefox')

def test_help(child):
    check_command('libs',
                  'Imported libraries:.*DebugLibrary.*Builtin libraries:')
    check_command('help libs', 'Print imported and builtin libraries,')
    check_command('libs  \t', '-s')
    check_command('libs  -s', 'ibraries/BuiltIn.py.*Builtin libraries:')
    check_command('?keywords', 'Print keywords of libraries,')
    check_command('k debuglibrary', 'Debug')
    check_command('k nothing', 'not found library')
    check_command('d Debug', 'Open a interactive shell,')

def test_variables(child):
    check_command('@{{list}} =  Create List    hello    world',
                  "@{{list}} = ['hello', 'world']")
    check_command('${list}', "['hello', 'world']")
    check_command('&{dict} =  Create Dictionary    name=admin',
                  "&{dict} = {'name': 'admin'}")
    check_command('${dict.name}', 'admin')

def test_auto_suggest(child):
    check_prompt('g', 'et time')

def test_errors(child):
    check_command('fail', 'AssertionError')
    check_command('nothing', "No keyword with name 'nothing' found.")
    check_command('get', "execution failed:.*No keyword with name 'get' found.")

def test_debug_if(child):
    check_command('${secs} =  Get Time  epoch', 'secs.* = ')
    check_command('Debug If  ${secs} > 1', 'Enter interactive shell')
    check_command('exit', 'Exit shell.')
    check_command('Debug If  ${secs} < 1', '> ')

def test_some_rf_core_keywords(child):
    check_command('log to console  hello', 'hello')
    check_command('get time', '.*-.*-.* .*:.*:.*')


def test_step_functionality(robot_child):
    check_command('list', 'Please run `step` or `next` command first.')

    support_source_lineno = get_version() >= '3.2'

    if support_source_lineno:
        check_command('s',  # step
                      '/tests/step.robot.7..*'
                      '-> log to console  working.*'
                      '=> BuiltIn.Log To Console  working')
        check_command('l',  # list
                      '  7 ->	    log to console  working')
        check_command('n',  # next
                      '/tests/step.robot.8..*'
                      '@.* =  Create List    hello    world.*'
                      '@.* = BuiltIn.Create List  hello  world')
        check_command('',  # just repeat last command
                      '/tests/step.robot.11..*'
                      '-> log to console  another test case.*'
                      '=> BuiltIn.Log To Console  another test case')
        check_command('l',  # list
                      '  6   	    debug.*'
                      '  7   	    log to console  working.*'
                      '  8   	    @.* =  Create List    hello    world.*'
                      '  9.*'
                      ' 10   	test2.*'
                      ' 11 ->	    log to console  another test case.*'
                      ' 12   	    log to console  end')
        check_command('ll',  # longlist
                      ' 10   	test2.*'
                      ' 11 ->	    log to console  another test case.*'
                      ' 12   	    log to console  end')
    else:
        check_command('s',  # step
                      '=> BuiltIn.Log To Console  working')
        check_command('l',  # list
                      'Please upgrade robotframework')
        check_command('n',  # next
                      '@.* = BuiltIn.Create List  hello  world')
        check_command('',  # repeat last command
                      '=> BuiltIn.Log To Console  another test case')

