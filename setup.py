from setuptools import find_packages, setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='micro',
    version='0.28.0',
    url='https://github.com/noyainrain/micro',
    maintainer='Sven James',
    maintainer_email='sven.jms AT gmail.com',
    packages=find_packages(),
    package_data={'micro': ['doc/*']},
    install_requires=requirements
)
