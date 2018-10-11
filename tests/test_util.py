import os
import logging
import time

import pytest
from timed_dict.timed_dict import TimedDict

os.environ['PYTHONPATH'] = '.'
logging.basicConfig(level=logging.INFO)


def test_test_sanity():
    assert 1 == 1


@pytest.fixture(scope='function')  # By function because we terminate it
def simple_timed_dict():
    '''
    Fixture. Returns a `TimedDict` with a few values set.
    '''
    d = TimedDict(timeout=3)
    return d
