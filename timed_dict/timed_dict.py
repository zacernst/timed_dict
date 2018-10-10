"""
Copyright (C) 2016 Zachary Ernst
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

import threading
import time
import collections
import types
import logging
import random
import atexit


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
    """
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
    """
    def __init__(
            self, timeout=10, checks_per_second=.5,
            sample_probability=.25, callback=None,
            expired_keys_ratio=.25, sweep_flag=True, callback_args=None,
            callback_kwargs=None):
        self.timeout = timeout
        self.callback_args = callback_args or tuple()
        self.callback_kwargs = callback_kwargs or {}
        self.checks_per_second = 1. / checks_per_second
        self.base_dict = {}
        self.expired_keys_ratio = expired_keys_ratio
        self.time_dict = {}
        self.sweep_flag = sweep_flag
        self.callback =  callback
        self.sample_probability = sample_probability
        self.sweep_thread = threading.Thread(daemon=True, target=self.sweep)
        self.sweep_thread.start()

    def __len__(self):
        '''
        Returns the number of items currently in the ``TimedDict``.
        '''

        return len(self.base_dict)

    def __delitem__(self, key):
        del self.base_dict[key]
        del self.time_dict[key]

    def __getitem__(self, key):
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
            self.callback(key, value)

    def stop_sweep(self):
        '''
        Stops the thread that periodically tests the keys for expiration.
        '''

        self.sweep_flag = False

    def __iter__(self):
        return self.base_dict.__iter__()


def cleanup_sweep_threads():
    for dict_name, obj in globals().items():
        if isinstance(obj, (TimedDict,)):
            logging.info('Stopping thread for TimedDict {dict_name}'.format(
                dict_name=dict_name))
            obj.stop_sweep()


if __name__ == '__main__':
    d = TimedDict(timeout=10, callback=my_callback)
    d['foo'] = 'bar'
    print(d)
    counter = 0
    while counter < 100:
        d[counter] = random.random()
        time.sleep(random.random() / 100)
        if random.random() < .1 and len(d) > 0:
            try:
                random_key = random.choice(list(d.keys()))
                print(d[random_key])
            except:
                pass
        counter += 1
    print('printing...')
    for i in d.items():
        print(i)

    cleanup_sweep_threads()


