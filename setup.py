from setuptools import setup

with open('README') as f:
    long_description = ''.join(f.readlines())

setup(
    name='GHIA',
    version='0.3',
    description='GHIA: pattern-based assigning of GitHub issues',
    author='Asatur Balyan',
    author_email='balyaasa@fit.cvut.cz',
    long_description=long_description,
    license='Public Domain',
    url='https://github.com/asatur96/ghia',
    install_requires=['Flask', 'click>=6', 'requests'],
    packages=['ghia'],
    classifiers=[
        'Framework :: Flask',
        'Environment :: Console',
        'Environment :: Web Environment'
    ]
)