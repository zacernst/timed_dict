.. Timed Dictionary documentation master file, created by
   sphinx-quickstart on Thu Oct 11 01:26:40 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Documentation for Timed Dictionary
==================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   Module documentation <modules>

Overview
--------

What it is
^^^^^^^^^^

"Timed Dictionary" provides a class -- ``TimedDict`` -- which is a
dictionary whose keys time out. After a pre-determined number
of seconds, the key and value will be deleted from the dictionary.
Optionally, a callback function may be specified, which is called whenever
a key is expired.

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

What it is not
^^^^^^^^^^^^^^

This module is **not** a replacement for Redis, MEMCACHE, or any
other such things. It is intended to be simple, lightweight, free of any
infrastructure requirements, stand-alone, pure Python, and above
all, functional. If you need failover, distributed caching, guarantees,
a magical solution to the CAP theorem, or you're processing huge volumes
of data, you should not use this.

Why it is
^^^^^^^^^

As a data engineer, I'm constantly coming across use-cases that look
like they require heavyweight tools, but which aren't demanding enough
to justify the investment. Redis, although it isn't exactly "heavyweight",
requires a server to run, with a dedicated IP address, and so on for
virtually any production use-case. So engineers who would like to have
a key-value store with expiration and callbacks either roll their own
one-off kludgey solution, or they stand up a Redis instance somewhere
and have one more thing to worry about.

This module provides that core functionality, implemented as a Python
dictionary. But it does not require anything other than the standard
Python library to run. It is dead-simple, reliable, and tested.

Limitations
^^^^^^^^^^^

If you need strong guarantees or tremendous precision, you won't want to
use this module. The expiration algorithm is probabilistic, so it's likely that
keys could expire in a somewhat different order than they were added, for
example. Keys could also hang around longer than their expiration time.

Generally, these slight imprecisions are not a big deal. Delays in expiring
keys are usually not more than half a second or so. We're trading off a little
precision for better performance and simplicity (which translates into
reliability).

Then there's the GIL. This module uses threading instead of multiprocessing,
which will send some people into fits of consternation and bitter indignation. But
if your application is so demanding that the GIL really poses a problem, then
you're probably better off using a more sophisticated tool, anyway. The GIL
is fine. Really.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
