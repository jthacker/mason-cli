from setuptools import setup
import os

version_file = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION'))

setup(
    name='mason-cli',
    version=version_file.read().strip(),
    py_modules=['mason', 'masonlib.imason', 'masonlib.platform', 'masonlib.internal.mason', 'masonlib.internal.persist', 'masonlib.internal.store',
                'masonlib.internal.utils', 'masonlib.internal.artifacts', 'masonlib.internal.apk', 'masonlib.internal.media', 'masonlib.internal.os_config',
                'masonlib.external.apk_parse', 'masonlib.external.apk_parse.apk', 'masonlib.external.apk_parse.bytecode', 'masonlib.external.apk_parse.androconf',
                'masonlib.external.apk_parse.dvm_permissions', 'masonlib.external.apk_parse.util'],
    include_package_data=True,
    install_requires=[
        'click',
        'requests',
        'tqdm',
        'pyyaml',
        'six',
        'colorama'
    ],
    entry_points='''
        [console_scripts]
        mason=mason:cli
    ''',
)
