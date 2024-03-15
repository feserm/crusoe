from setuptools import setup, find_packages

setup(
    name='crusoe',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'click',
        'openstacksdk',
        'pyyaml',
        'icecream'
    ],
    entry_points={
        'console_scripts': [
            'crusoe=main:cli'
        ]
    }
)