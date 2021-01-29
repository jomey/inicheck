#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_checkers
----------------------------------

Tests for `inicheck.checkers` module.
"""

import inicheck
import pytest
from inicheck.checkers import *
from inicheck.config import MasterConfig, UserConfig


class CheckerTester():
    def __init__(self):
        tests_p = os.path.join(os.path.dirname(inicheck.__file__), '../tests')
        self.mcfg = MasterConfig(path=os.path.join(tests_p,
                                                   'test_configs/master.ini'))

        self.ucfg = UserConfig(os.path.join(tests_p, "test_configs/base_cfg.ini"),
                               mcfg=self.mcfg)

    def run_a_checker(self, valids, invalids, checker, section='basic',
                      item='item',
                      extra_config={}):
        """
        Runs a loop over all the valids and applies the checker and asserts
        theyre true. Same thing is done for the invalids
        Args:
            valids: List of valid entries to check
            invalids: List of invalid entries to check
            checker: any class in inicheck.checkers
            ucfg: inicheck.config.UserConfig instance (optional)
            is_list: is it expected to be a list?
            section: section name the item being checked is occurring
            item: Item name in the config
            extra_config: Pass in contextual config info to test more
                          complicated checkers. E.g. ordered datetime pair.
        """

        cfg = self.ucfg.cfg
        cfg.update({section: {item: " "}})

        # Added info for testing e.g. ordered datetime pair
        if extra_config:
            cfg.update(extra_config)

        for z, values in enumerate([valids, invalids]):
            for v in values:

                cfg[section][item] = v
                b = checker(config=self.ucfg, section=section, item=item)
                msgs = b.check()

                if len([True for m in msgs if m is None]) == len(msgs):
                    valid = True
                else:
                    valid = False

                # Expected valid
                if z == 0:
                    assert valid
                else:
                    assert not valid


@pytest.fixture
def check_tester():
    """
    Create some key structures for testing
    """
    cls = CheckerTester()
    return cls


def test_string(check_tester):
    """
    Test we see strings as strings
    """

    # Confirm we these values are valid
    valids = ['test']
    check_tester.run_a_checker(valids, [], CheckString, item='username')

    # Confirm that casting a string with uppers will auto produce lowers
    check_tester.ucfg.cfg['basic']['username'] = 'Test'

    b = CheckString(config=check_tester.ucfg, section='basic', item='username')
    result = b.cast()
    assert result == 'test'

    # Check we can capture a single item list for strings
    b.is_list = True
    result = b.cast()
    assert result == ['test']

    # Check we capture the when alist is passed and were not expecting one
    b.is_list = False
    result = b.cast()
    assert not isinstance(result, list)


def test_bool(check_tester):
    """
    Test we see booleans as booleans
    """

    # Confirm we these values are valid
    valids = [True, False, 'true', 'FALSE', 'yes', 'y', 'no', 'n']
    invalids = ['Fasle', 'treu']
    check_tester.run_a_checker(valids, invalids, CheckBool, item='debug')


def test_float(check_tester):
    """
    Test we see floats as floats
    """
    valids = [-1.5, '2.5']
    invalids = ['tough']

    check_tester.run_a_checker(valids, invalids, CheckFloat, item='time_out')


def test_int(check_tester):
    """
    Test we see int as ints and not floats
    """

    # Confirm we these values are valid
    valids = [10, '2', 1.0]
    invalids = ['tough', '1.5', '']
    check_tester.run_a_checker(valids, invalids, CheckInt, item='num_users')


def test_datetime(check_tester):
    """
    Test we see datetime as datetime
    """

    valids = ['2018-01-10 10:10', '10-10-2018', "October 10 2018"]
    invalids = ['Not-a-date', 'Wednesday 5th']
    check_tester.run_a_checker(
        valids,
        invalids,
        CheckDatetime,
        item='start_date')


def test_list(check_tester):
    """
    Test our listing methods using lists of dates.
    """

    valids = ['10-10-2019', ['10-10-2019'], ['10-10-2019', '11-10-2019']]
    check_tester.run_a_checker(valids, [], CheckDatetime, item='epochs')


def test_directory(check_tester):
    """
    Tests the base class for path based checkers
    """

    valids = ["./"]
    invalids = ['./somecrazy_location!/']
    check_tester.run_a_checker(valids, invalids, CheckDirectory, item='tmp')

    # ISSUE #44 check for default when string is empty
    check_tester.ucfg.cfg.update({'basic': {'tmp': ''}})
    b = CheckDirectory(config=check_tester.ucfg, section='basic', item='tmp')
    value = b.cast()
    assert os.path.split(value)[-1] == 'temp'


def test_filename(check_tester):
    """
    Tests the base class for path based checkers
    """
    # Remember paths are relative to the config
    valids = ["../test_checkers.py"]
    invalids = ['dumbfilename']
    check_tester.run_a_checker(valids, invalids, CheckFilename, item='log')

    # ISSUE #44 check for default when string is empty
    check_tester.ucfg.cfg.update({'basic': {'log': ''}})
    check_tester.ucfg.mcfg.cfg['basic']['log'].default = None
    b = CheckFilename(config=check_tester.ucfg, section='basic', item='log')
    value = b.cast()
    assert value is None

    # ISSUE #44 check for default when string is empty but default is a
    # path
    check_tester.ucfg.cfg.update({'basic': {'log': ''}})
    check_tester.ucfg.mcfg.cfg['basic']['log'].default = 'log.txt'
    b = CheckFilename(config=check_tester.ucfg, section='basic', item='log')
    value = b.cast()
    assert os.path.split(value)[-1] == 'log.txt'


def test_url(check_tester):
    """
    Test our url checking.
    """
    valids = ["https://google.com"]
    invalids = ["https://micah_subnaught_is_awesome.com"]
    check_tester.run_a_checker(valids, invalids, CheckURL,
                               item='favorite_web_site')


def test_datetime_ordered_pairs(check_tester):
    """
    Tests the ordered datetime pair checker which looks for <keyword>_start
    <keyword>_end pairs and confirms they occurs in the correct order.

    """

    # Test end dates com after start dates
    starts = ["1-01-2019", "2019-10-01", "1998-01-14 15:00:00"]
    ends = ["1-02-2019", "2019-10-02", "1998-01-14 19:00:00"]

    invalids_starts = ["01-01-2020", "2020-06-01", "1998-01-14 20:00:00"]
    invalids_ends = ["01-01-2018", "2018-10-01", "1998-01-14 10:00:00", ]

    # Check for starts being before the end date
    for start, end, error_start, error_end in zip(starts, ends,
                                                  invalids_starts,
                                                  invalids_ends):
        # Check start values are before end values
        acfg = {'basic': {'end_date': end}}
        check_tester.run_a_checker([start], [error_start], CheckDatetimeOrderedPair,
                                   item="start_date",
                                   extra_config=acfg)

        # Check start values are before end values
        acfg = {'basic': {'start_date': start}}
        check_tester.run_a_checker([end], [error_end], CheckDatetimeOrderedPair,
                                   item="end_date",
                                   extra_config=acfg)

    # Check start end values are equal error
    acfg = {'basic': {'start_date': '2020-10-01'}}
    check_tester.run_a_checker(["2020-10-02"], ["2020-10-01"],
                               CheckDatetimeOrderedPair,
                               item="end_date",
                               extra_config=acfg)


def test_bounds(check_tester):
    """
    MasterConfig options now have max and min values to constrain continuous
    types. This tests whether that works
    """

    check_tester.run_a_checker([1.0, 0.0, '0.5'], [1.1, -1.0, '10'], CheckFloat,
                               item='fraction')


if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
