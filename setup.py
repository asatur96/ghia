from setuptools import setup

with open('README') as f:
    long_description = ''.join(f.readlines())

setup(
    name='ghia-asatur96',
    version='0.3.2',
    description='GHIA: pattern-based assigning of GitHub issues',
    author='Asatur Balyan',
    author_email='balyaasa@fit.cvut.cz',
    long_description=long_description,
    license='Public Domain',
    url='https://github.com/asatur96/ghia',
    install_requires=['Flask', 'click>=6', 'requests'],
    packages=['ghia_asatur96'],
    classifiers=[
        'Framework :: Flask',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python'
    ],
    package_data={'ghia_asatur96': ['templates/*.html', 'static/*.css']}
)
