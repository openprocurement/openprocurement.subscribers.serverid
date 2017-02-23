from setuptools import setup, find_packages
import os

version = '1.0'

entry_points = {
    'openprocurement.subscribers.newrequest': [
        'server_id = openprocurement.subscribers.serverid.serverid:includeme'
    ]
}

requires = [
    'pycrypto',
    'pyramid',
    'pytz',
    'setuptools',
    'webob',
]

test_requires = requires + [
    'webtest',
    'coverage',
    'python-coveralls',
    'nose',
]

setup(name='openprocurement.subscribers.serverid',
      version=version,
      description="openprocurement.subscribers.serverid",
      long_description=open("README.md").read() + "\n" +
      open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
          "Programming Language :: Python",
      ],
      keywords='',
      author='Quintagroup, Ltd.',
      author_email='info@quintagroup.com',
      url='https://github.com/openprocurement/openprocurement.subscribers.serverid',
      license='Apache License 2.0',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['openprocurement', 'openprocurement.subscribers'],
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=test_requires,
      test_suite="openprocurement.subscribers.serverid.tests.serverid.suite",
      entry_points=entry_points
      )
