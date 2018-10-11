import setuptools

long_description = \
'''
A Python 3 module that provides a `TimedDict` class, which is designed to
mimic the functionality of Redis's `EXPIRE`. Keys are
set to expire after a certain number of seconds, and a callback function
may optionally be called. Keys are continuously checked for expiration in
a separate thread, so stale keys do not pile up in memory.
'''

setuptools.setup(
    name="timeddictionary",
    version="0.1.1",
    author="Zachary Ernst",
    author_email="zac.ernst@gmail.com",
    description="A dictionary with key expiration and callbacks.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zacernst/timed_dict",
    packages=['timed_dict'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
