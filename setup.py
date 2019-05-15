from setuptools import setup, find_packages

LONG_DESCRIPTION = """
Python oricura is a tool for generating custom rankings (general standings) from orienteering race
results in IOF format. It is intended to be easy to extend with custom rules for computing the final scores.
Rankings are generated automatically in different file format, such as CSV, HTML, PDF.
""".strip()

SHORT_DESCRIPTION = """
A tool for generating custom rankings from orienteering race results in IOF format.""".strip()

DEPENDENCIES = [
    'requests',
    'pandas>=0.24',
    'jinja2',
    'weasyprint',
    'fire',
]

TEST_DEPENDENCIES = [
    'hypothesis',
    'mock',
    'python-Levenshtein',
]

VERSION = '0.1'
URL = 'https://github.com/mldv/oricura'

setup(
    name='oricura',
    version=VERSION,
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    url=URL,

    author='Marco Della Vedova',
    author_email='marco.dellavedova@gmail.com',
    license='GNU General Public License v3 (GPLv3)',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Utilities',

        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        'Programming Language :: Python :: 3',

        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
    ],

    keywords='sport orienteering',

    packages=find_packages(),

    install_requires=DEPENDENCIES,
    tests_require=TEST_DEPENDENCIES,
)
