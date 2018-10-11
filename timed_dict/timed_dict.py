'''
This is the ``TimedDict`` class and its various methods and helpers.

``TimedDict`` instances are dictionaries (``MutableMapping`` objects, to be
more precise) whose keys expire after a predetermined time has elapsed. When
they expire, a callback function may optionally be executed. The callback
function is passed the key and value that have just expired.

Using the class is pretty simple.

::

    import time
    from timed_dict.timed_dict import TimedDict

    d = TimedDict(timeout=10)
    d['foo'] = 'bar'

    print('Retrieving the key right away...')
    print(d['foo'])
    print('Waiting 11 seconds...')
    time.sleep(11)
    print('The key is expired, so we get an `Empty()` object.')
    print(d['foo'])


Running this code produces the following output:

::

    Retrieving the key right away...
    bar
    Waiting 11 seconds...
    The key is expired, so we get an `Empty()` object.
    <timed_dict.timed_dict.Empty object at 0x7ff82003a860>


That's the simplest use-case. Often, you'll want something to happen when a
key expires. For this, you specify a callback function, like so:

::

    import time
    from timed_dict.timed_dict import TimedDict

    def my_callback(key, value):  # Key and value are required arguments
	print('The key {key} has expired. Its value was {value}.'.format(
	    key=str(key), value=str(value)))


    d = TimedDict(timeout=10, callback=my_callback)  # Specify callback here
    d['foo'] = 'bar'

    print('Retrieving the key right away..')
    print(d['foo'])
    print('Waiting 11 seconds...')
    time.sleep(11)
    print('The key is expired, so we get an `Empty()` object.')
    print(d['foo'])


Running the new code, with the callback function, produces this:

::

    Retrieving the key right away..
    bar
    Waiting 11 seconds...
    The key foo has expired. Its value was bar.
    The key is expired, so we get an `Empty()` object.
    <timed_dict.timed_dict.Empty object at 0x7f0a56cfccf8>


As you can see, the behavior is identical, except that we now see the output
from the callback function (on the fourth line).

Other arguments may be passed to the ``TimedDict`` constructor. They are
documented in its ``__init__`` function below.
'''

import threading
import time
import collections
import types
import logging
import random


logging.basicConfig(level=logging.INFO)


class Empty:
    '''
    Just to provide a unique default class when asking for a key
    that's been deleted.
    '''
    pass


def my_callback(key, value):
    '''
    Simple test of callback function.
    '''
    print('hi there:', str(key))


class TimedDict(collections.MutableMapping):
    '''
    A dictionary whose keys time out. After a pre-determined number
    of seconds, the key and value will be deleted from the dictionary.
    Optionally, a callback function is executed, which is passed
    the key and the associated value.

    When it is instantiated, this class creates a thread which runs
    all the time, looking for expired keys. Each ``TimedDict`` object
    gets its own thread.

    The algorithm is the same one that Redis uses. It is semi-lazy
    and probabilistic. After sleeping for a set interval, it
    iterates through a random sample of the keys (which is determined
    by the ``sample_probability`` kwarg in the class constructor).
    It expires any keys it finds during the sweep which have existed
    for more then ``timeout`` seconds. If at least ``expired_keys_ratio``
    of the sampled keys have to be expired, then the process is repeated
    again immediately. If not, then it sleeps for the interval again
    before restarting.

    Additionally, a check is made to any specific key that's accessed.
    If the key should be expired, then it does so and returns an
    ``Empty`` object.
    '''

    def __init__(
            self, timeout=None, checks_per_second=.5,
            sample_probability=.25, callback=None,
            expired_keys_ratio=.25, sweep_flag=True, callback_args=None,
            callback_kwargs=None):
        '''
        Init function for ``TimedDict``. This automatically creates and starts
        a thread which intermittantly sweeps through the keys, looking for
        things to expire.

        Args:
            timeout (float): Number of seconds after which keys will expire.
            checks_per_second (float): Approximstely how many timed per second
                to scan for expired keys.
            sample_probability (float): Keys are scanned randomly. This is the
                proportion of keys that will be checked on any given sweep.
            callback (function): Function to be executed whenever a key expires.
                The function will be passed the arguments ``key`` and ``value``
                as (non-keyword) arguments.
            expired_keys_ratio (float): If the proportion of expired keys that
                are discovered on a given sweep exceeds this number, then
                another sweep is executed immediately. This on the theory that
                if there are many keys to be expired within a random sample,
                then there are probably a lot more.
            sweep_flag (bool): If ``True``, the thread runs which starts
                sweeping through the keys. It is not normally necessary for
                the user to fuss with this.
            callback_args (tuple): Positional arguments to be passed to the
                callback function.
            callback_kwargs (dict): Dictionary of keyword arguments to be
                passed to the callback function.
        '''
        if timeout is None:
            raise Exception(
                'Must set `timeout` when instantiating `TimedDict`.')
        self.timeout = timeout
        self.callback_args = callback_args or tuple()
        self.callback_kwargs = callback_kwargs or {}
        self.checks_per_second = 1. / checks_per_second
        self.base_dict = {}
        self.expired_keys_ratio = expired_keys_ratio
        self.time_dict = {}
        self.callback_dict = {}
        self.sweep_flag = sweep_flag
        self.callback =  callback
        self.sample_probability = sample_probability
        self.sweep_thread = threading.Thread(
            daemon=True, target=self.sweep)
        self.sweep_thread.start()

    def __len__(self):
        '''
        Returns the number of items currently in the ``TimedDict``.
        '''

        return len(self.base_dict)

    def __delitem__(self, key):
        '''
        Deletes the key and value from both the ``base_dict``
        and the ``timed_dict``.
        '''
        del self.base_dict[key]
        del self.time_dict[key]

    def set_expiration(self, key, ignore_missing=False,
            additional_seconds=None, seconds=None):
        '''
        Alters the expiration time for a key. If the key is not
        present, then raise an Exception unless `ignore_missing`
        is set to `True`.

        Args:
            key: The key whose expiration we are changing.
            ignore_missing (bool): If set, then return silently
                if the key does not exist. Default is `False`.
            additional_seonds (int): Add this many seconds to the
                current expiration time.
            seconds (int): Expire the key this many seconds from now.
        '''
        if key not in self.time_dict and ignore_missing:
            return
        elif key not in self.time_dict and not ignore_missing:
            raise Exception('Key missing from `TimedDict` and '
                '`ignore_missing` is False.')
        if additional_seconds is not None:
            self.time_dict[key] += additional_seconds
        elif seconds is not None:
            self.time_dict[key] = time.time() + seconds

    def __getitem__(self, key):
        '''
        Gets the item. Before it does so, checks whether the key
        has expired. If so, it expires the key **first**, before
        returning a value.

        If the key does not exist (or gets expired during this call)
        the method returns an instance of the `Empty` class. We use
        the `Empty` class (defined above) because we want to avoid
        raising exceptions, but we also want to allow that the
        legitimate value of a key might be `None` (or any other default
        value we like).
        '''

        if key not in self.base_dict:
            return Empty()
        if time.time() >= self.time_dict[key]:
            logging.debug(
                'deleting expired key: {key}'.
                format(key=str(key)))
            self.expire_key(key)
        try:
            out = self.base_dict[key]
        except KeyError:
            out = Empty()
        return out

    def __setitem__(self, key, value):
        '''
        Replaces the ``__setitem__`` from the parent class. Sets both
        the ``base_dict`` (which holds the values) and the ``timed_dict``
        (which holds the expiration time.
        '''
        self.base_dict[key] = value
        self.time_dict[key] = time.time() + self.timeout

    def keys(self):
        '''
        Replaces the ``keys`` method. There's probably a better way to
        accomplish this.
        '''

        for i in self.base_dict.keys():
            yield i

    def values(self):
        '''
        Replaces the ``values`` method. There's probably a better way to
        accomplish this.
        '''
        for i in self.base_dict.values():
            yield i

    def __repr__(self):
        '''
        String representation of the ``TimedDict``. It returns the
        keys, values, and time of expiration for each.
        '''

        d = {
            key: (self.base_dict[key], self.time_dict[key],)
            for key in self.base_dict.keys()}
        return d.__repr__()

    def sweep(self):
        '''
        This methods runs in a separate thread. So long as
        `self.sweep_flag` is set, it expires keys according to
        the process explained in the docstring for the `TimedDict`
        class. The thread is halted by calling `self.stop_sweep()`,
        which sets the `self.sweep_flag` to `False`.
        '''

        while self.sweep_flag:
            current_time = time.time()
            expire_keys = set()
            keys_checked = 0.
            items = list(self.time_dict.items())
            for key, expire_time in items:
                if random.random() > self.sample_probability:
                    continue
                keys_checked += 1
                if current_time >= expire_time:
                    expire_keys.add(key)
                    logging.debug(
                        'marking key for deletion: {key}'.
                        format(key=str(key)))
            for key in expire_keys:
                self.expire_key(key)
            expired_keys_ratio = (
                len(expire_keys) / keys_checked
                if keys_checked > 0 else 0.)
            if expired_keys_ratio < self.expired_keys_ratio:
                time.sleep(1. / self.checks_per_second)

    def expire_key(self, key):
        '''
        Expire the key, delete the value, and call the callback function
        if one is specified.

        Args:
            key: The ``TimedDict`` key
        '''
        value = self.base_dict[key]
        del self[key]
        if self.callback is not None:
            self.callback(
                key, value, *self.callback_args, **self.callback_kwargs)

    def stop_sweep(self):
        '''
        Stops the thread that periodically tests the keys for expiration.
        '''

        self.sweep_flag = False

    def __iter__(self):
        return self.base_dict.__iter__()


def cleanup_sweep_threads():
    '''
    Not used. Keeping this function in case we decide not to use
    daemonized threads and it becomes necessary to clean up the
    running threads upon exit.
    '''

    for dict_name, obj in globals().items():
        if isinstance(obj, (TimedDict,)):
            logging.info(
                'Stopping thread for TimedDict {dict_name}'.format(
                    dict_name=dict_name))
            obj.stop_sweep()


if __name__ == '__main__':
    LICENSE = \
    """
    Copyright (C) 2018 Zachary Ernst
    zac.ernst@gmail.com

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    """
    print(LICENSE)
