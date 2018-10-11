import os
import logging
import time

import pytest
from timed_dict.timed_dict import TimedDict, Empty

os.environ['PYTHONPATH'] = '.'
logging.basicConfig(level=logging.INFO)


def test_sanity_check():
    assert 1 == 1

@pytest.fixture(scope='function')  # By function because we terminate it
def simple_timed_dict():
    '''
    Fixture. Returns a `TimedDict` with a few values set.
    '''
    d = TimedDict(timeout=1)
    return d

def test_instantiate_timed_dict(simple_timed_dict):
    pass

def test_insert_key_and_value(simple_timed_dict):
    simple_timed_dict['foo'] = 'bar'
    assert simple_timed_dict['foo'] == 'bar'

def test_instantiate_empty():
    e = Empty()
    assert isinstance(e, (Empty,))

def test_delete_key_and_value(simple_timed_dict):
    simple_timed_dict['foo'] = 'bar'
    del simple_timed_dict['foo']
    assert isinstance(simple_timed_dict['foo'], (Empty,))

def test_key_expires(simple_timed_dict):
    simple_timed_dict['foo'] = 'bar'
    time.sleep(2)
    assert isinstance(simple_timed_dict['foo'], (Empty,))

def test_stop_sweep(simple_timed_dict):
    simple_timed_dict.stop_sweep()
    time.sleep(1)  # Threads don't die instantly
    assert simple_timed_dict.sweep_thread.is_alive() is False

def test_keys_do_not_expire_after_stop_sweep(simple_timed_dict):
    simple_timed_dict['foo'] = 'bar'
    simple_timed_dict.stop_sweep()
    time.sleep(2)
    assert 'foo' in simple_timed_dict
