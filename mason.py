#!/usr/bin/env python2
import sys

import getpass
import pkg_resources
import click
import requests
import colorama

import masonlib.external.apk_parse.apk
from masonlib.platform import Platform
from masonlib.imason import IMason


class Config(object):
    """
    Global config object, utilized to set verbosity of logging events
    and other flags.
    """

    def __init__(self):
        self.verbose = False
        self.no_colorize = False
        self.output = None

pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.option('--debug', '-d', is_flag=True, help='show additional debug information where available')
@click.option('--verbose', '-v', help='show verbose artifact and command details', is_flag=True)
@click.option('--access-token', help='optional access token if already available')
@click.option('--id-token', help='optional id token if already available')
@click.option('--no-color', is_flag=True, help='turn off colorized output')
@pass_config
def cli(config, debug, verbose, id_token, access_token, no_color):
    """mason-cli provides command line interfaces that allow you to register, query, build, and deploy
your configurations and packages to your devices in the field."""
    _check_version()
    config.debug = debug
    config.verbose = verbose
    config.no_colorize = no_color
    if not no_color:
        colorama.init(autoreset=True)
    platform = Platform(config)
    config.mason = platform.get(IMason)
    config.mason.set_id_token(id_token)
    config.mason.set_access_token(access_token)


@cli.group()
@pass_config
def apk(config):
    """APK commands"""
    pass


@apk.command(help='get a key value from the specified apk')
@click.argument(
    'key',
    type=click.Choice(('versionName', 'versionCode', 'package')))
@click.argument('apk')
@pass_config
def get(config, apk, key):
    apk_obj = masonlib.external.apk_parse.apk.APK(apk)
    key_map = {
        'versionName': apk_obj.get_androidversion_name(),
        'versionCode': apk_obj.get_androidversion_code(),
        'package': apk_obj.get_package()
    }
    print(key_map[key])


@cli.group()
@click.option('--skip-verify', '-s', is_flag=True, help='skip verification of artifact details')
@pass_config
def register(config, skip_verify):
    """Register artifacts to the mason platform."""
    config.skip_verify = skip_verify


@register.command()
@click.argument('apks', nargs=-1)
@pass_config
def apk(config, apks):
    """Register apk artifacts.

         APK - One or many apk's to be registered to the mason platform.

       ex:\n
         mason register apk test.apk

       multiple in a directory:\n
         mason register apk apks/*.apk
    """
    for app in apks:
        if config.verbose:
            click.echo('Registering {}...'.format(app))
        if config.mason.parse_apk(app):
            if not config.mason.register(app):
                sys.exit(1)


@register.command()
@click.argument('yamls', nargs=-1)
@pass_config
def config(config, yamls):
    """Register config artifacts.

         YAML - One or more yaml file describing a configuration.

       ex:\n
         mason register config test.yml

       multiple in a directory:\n
         mason register config configs/*.yml
    """
    for yaml in yamls:
        if config.verbose:
            click.echo('Registering {}...'.format(yaml))
        if config.mason.parse_os_config(yaml):
            if not config.mason.register(yaml):
                sys.exit(1)


@register.command()
@click.argument('binary')
@click.argument('name')
@click.argument('type')
@click.argument('version')
@pass_config
def media(config, binary, name, type, version):
    """Register media artifacts.

         NAME - The name of the media artifact.\n
         TYPE - The given type of the media artifact.\n
            supported:\n
                - bootanimation\n
         VERSION - The version of the media artifact.

       ex:\n
          mason register media bootanimation.zip bootanimation 1
    """
    if config.verbose:
        click.echo('Registering {}...'.format(binary))
    if config.mason.parse_media(name, type, version, binary):
        if not config.mason.register(binary):
            sys.exit(1)


@cli.command()
@click.argument('project')
@click.argument('version')
@pass_config
def build(config, project, version):
    """Build a registered project.

         PROJECT - The name of the configuration project\n
         VERSION - The version of the configuration project

       The name and the version of the configuration project
       can be found in the YAML definition which was registered
       to the mason platform.

       As an example, a registered yaml:\n
         os:\n
           name: mason-test\n
           version: 5

       becomes a build command:\n
         mason build mason-test 5
    """
    if config.verbose:
        click.echo('Starting build for {}:{}...'.format(project, version))
    if not config.mason.build(project, version):
        exit('Unable to start build')


@cli.group()
@click.option('--output', type=click.Choice(('text', 'json')), default='text', help='Output format of the command')
@pass_config
def info(config, output):
    """Get info from various services."""
    config.output = output


@info.command()
@click.option('--build-id', help='Optional build id')
@pass_config
def build(config, build_id):
    """Get info about builds.
    """
    if not config.mason.build_info(build_id, config.output):
        exit('Unable to get build info')


@info.command()
@click.option('--type', 'artifact_type', help='Artifact type to show', default=None)
@pass_config
def artifact(config, artifact_type):
    """Get info about artifacts.
    """
    if not config.mason.artifact_info(artifact_type, output=config.output):
        exit('Unable to get apk info')


@cli.group()
@click.option('--skip-verify', '-s', is_flag=True, help='skip verification of deployment')
@click.option('--push', '-p', is_flag=True, default=False, help='push the deployment to devices in the field')
@pass_config
def deploy(config, skip_verify, push):
    """Deploy artifacts to groups."""
    config.skip_verify = skip_verify
    config.push = push


@deploy.command()
@click.argument('name')
@click.argument('version')
@click.argument('groups', nargs=-1)
@pass_config
def apk(config, name, version, groups):
    """Deploy apk artifacts.

         NAME - The package name of the apk to be deployed\n
         VERSION - The versionCode of the apk\n
         GROUP(s) - The target group(s) to deploy to

       As an example, a registered apk:\n
           package_name: com.test.app\n
           version_code: 3

       to deploy to group `development` becomes:\n
         mason deploy apk com.test.app 3 development\n

       or to deploy to multiple groups:\n
         mason deploy apk com.test.app 3 development staging production

       this can be used in conjunction with the --push argument
    """
    for group in groups:
        if config.verbose:
            click.echo('Deploying {}:{}...'.format(name, version))
        if not config.mason.deploy("apk", name, version, group, config.push):
            exit('Unable to deploy item')


@deploy.command()
@click.argument('name')
@click.argument('version')
@click.argument('groups', nargs=-1)
@pass_config
def ota(config, name, version, groups):
    """Deploy ota artifacts.

         NAME - The name of the ota to be deployed (usually mason-os)\n
         VERSION - The release version (semantic version) of the ota  \n
         GROUP(s) - The target group(s) to deploy to

       As an example, Mason OS 2.0.0 (Nougat Release):\n
           name: mason-os\n
           release version: 2.0.0

       to deploy to group `development` becomes:\n
         mason deploy ota mason-os 2.0.0 development\n

       or to deploy to multiple groups:\n
         mason deploy ota mason-os 2.0.0 development staging production

       this can be used in conjunction with the --push argument
    """
    for group in groups:
        if config.verbose:
            click.echo('Deploying {}:{}...'.format(name, version))
        if not config.mason.deploy("ota", name, version, group, config.push):
            exit('Unable to deploy item')


@deploy.command()
@click.argument('name')
@click.argument('version')
@click.argument('groups', nargs=-1)
@pass_config
def config(config, name, version, groups):
    """Deploy config artifacts.

         NAME - The name of the configuration to be deployed\n
         VERSION - The version of the configuration to be deployed\n
         GROUP(s) - The target group(s) to deploy to

       As an example, a registered yaml:\n
         os:\n
           name: mason-test\n
           version: 5\n

       to deploy to group `development` becomes:\n
         mason deploy config mason-test 5 development

       or to deploy to multiple groups:\n
         mason deploy config mason-test 5 development staging production

       this can be used in conjunction with the --push argument
    """
    for group in groups:
        if config.verbose:
            click.echo('Deploying {}:{}...'.format(name, version))
        if not config.mason.deploy("config", name, version, group, config.push):
            exit('Unable to deploy item')


@cli.command()
@click.option('--skip-verify', '-s', is_flag=True, help='skip verification of config stage')
@click.argument('yaml')
@pass_config
def stage(config, skip_verify, yaml):
    """Stage a project.

         YAML - The configuration file to register and build.

       The stage commands allows you to register a configuration file and immediately start a build for it.
    """
    config.skip_verify = skip_verify
    if config.verbose:
        click.echo('Staging {}...'.format(yaml))
    if config.mason.parse_os_config(yaml):
        if not config.mason.stage(yaml):
            sys.exit(1)


@cli.command()
@click.option('--user', default=None, help='pass in user')
@click.option('--password', default=None, help='pass in password')
@pass_config
def login(config, user, password):
    """Authenticate via user/password."""
    if not user or not password:
        # Prompt for user name
        response = raw_input('User: ')

        # Exit on empty user
        if not response:
            exit('Authentication requires a valid user')

        user = response

        # Prompt for password
        response = getpass.getpass()

        # Exit on empty password
        if not response:
            exit('Authentication requires a valid password')

        password = response
    if config.verbose:
        click.echo('Authing ' + user)
    if not config.mason.authenticate(user, password):
        exit('Unable to authenticate')
    else:
        click.echo('User authenticated.')


@cli.command()
@pass_config
def logout(config):
    """Log out of current session."""
    if config.mason.logout():
        click.echo('Successfully logged out')


@cli.command()
def version():
    """Display mason-cli version."""
    try:
        version = pkg_resources.require("mason-cli")[0].version
        click.echo('mason (Mason America) ' + version)
        click.echo('Copyright (C) 2018 Mason America')
        click.echo('License Apache 2.0 <https://www.apache.org/licenses/LICENSE-2.0>')
    except pkg_resources.DistributionNotFound:
        click.echo('Unable to retrieve version information')


def _check_version():
    r = requests.get('https://raw.githubusercontent.com/MasonAmerica/mason-cli/master/VERSION')
    current_version = float(pkg_resources.require("mason-cli")[0].version)
    if r.status_code == 200:
        if r.text:
            remote_version = float(r.text)
            if remote_version > current_version:
                msg = (
                    '\n==================== NOTICE ====================\n' \
                    'A newer version \'{}\' of the mason-cli is available.\n' \
                    'Run:\n' \
                    '    `pip install --upgrade git+https://git@github.com/MasonAmerica/mason-cli.git`\n' \
                    'to upgrade to the latest version.\n' \
                    '\n' \
                    'Release notes: https://github.com/MasonAmerica/mason-cli/releases' \
                    '\n' \
                    '==================== NOTICE ====================\n'.format(remote_version))
                sys.stderr.write(msg)
                sys.stderr.flush()


if __name__ == '__main__':
    cli()
