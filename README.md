[![Build Status](https://travis-ci.org/zacernst/timed_dict.svg?branch=master)](https://travis-ci.org/zacernst/timed_dict)

# TimedDict: Dictionary that mimics Redis's EXPIRE

This package provides the `TimedDict` class, which is a dictionary.
However, when it is instantiated, you provide a `timeout` parameter, which
is the number of seconds that items in the dictionary are allowed
to live. After their time has elapsed, the key and value are deleted.

Checks for expired keys are done continuously in a background thread.
The algorithm for this is the same as the one used by Redis. At a set
time interval, the keys are randomly sampled and any that should be
expired are deleted. If a large percentage of the sampled keys are
expired, then the process is run again immediately. If not, then it
is repeated only after the time interval has elapsed.

Any key that is accessed is also checked and expired if necessary. Thus,
this process is probabilistic and sort of lazy.

The ability to expire keys even when they're not actively being
accessed means that you can use this class to execute a function
when a key is expired. Thus, you can provide an optional `callback`
parameter to the `TimedDict`, which should be a function. Whenever
a key is expired, the key and its associate value are passed to the
callback function, which executes immediately. Other arguments to be
passed to the callback function may be specified when the `TimedDict`
is instantiated.

`TimedDict` is easy to use:

```
>>> from timed_dict import TimedDict                                    
>>> d = TimedDict(timeout=30)  # Expire keys after thirty seconds
>>> d['foo'] = 'bar'
>>> d['foo']
'bar'
>>> # get a cup of coffee
... d
{}
>>> d['foo']
<timed_dict.timed_dict.Empty object at 0x7f9db1c05278>
>>> def say_hi(key, value):
...     print('hi ' + key)
>>> d = TimedDict(timeout=30, callback=say_hi)  # Specify callback function
>>> d['foo'] = 'bar'
>>> # wait for a while
>>> hi foo
```

zac.ernst@gmail.com

