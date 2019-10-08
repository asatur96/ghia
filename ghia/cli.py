import configparser
import click
import re
import sys

from ghia.utils import parse_rules, parse_fallback
from ghia.logic import Ghia, Report


def print_report(report):
    issue = click.style(f'{report.repo}#{report.number}', fg = 'white', bold = True)
    click.secho(f'-> {issue} {report.msgs[0]}')

    if report.ok is False:
        error_msg = click.style('ERROR', fg = 'red', bold = True)
        click.secho(f'   {error_msg}: Could not update issue {report.repo}#{report.number}', err = True)
        return
    
    if report.fallback is not None:
        fb_msg = click.style('FALLBACK', fg = 'yellow', bold = True)
        click.secho(f'   {fb_msg}: {report.fallback}')
    
    i = 1    
    while i < len(report.msgs):
        msg_txt = ''
        if report.msgs[i] == '+':
            msg_txt = click.style('+', fg = 'green', bold = True)
        elif report.msgs[i] == '=':
            msg_txt = click.style('=', fg = 'blue', bold = True)
        else:
            msg_txt = click.style('-', fg = 'red', bold = True)
        click.secho(f'   {msg_txt} {report.msgs[i + 1]}')
        i += 2


def get_token(config_auth):
    try:
        cfg_auth = configparser.ConfigParser()
        cfg_auth.read_file(config_auth)
        return cfg_auth.get('github', 'token')
    except Exception:
        raise click.BadParameter('incorrect configuration format')


def get_rules(config_rules):
    try:
        cfg_rules = configparser.ConfigParser()
        cfg_rules.optionxform = str
        cfg_rules.read_file(config_rules)
        fallback = None
        if cfg_rules.has_section('fallback'):
            fallback = parse_fallback(cfg_rules)

        return (parse_rules(cfg_rules), fallback)
    except Exception:
        raise click.BadParameter('incorrect configuration format')


def validate_reposlug(ctx, param, value):
    try:
        userorg, repo = value.split('/')
        return (userorg, repo)
    except ValueError:
        raise click.BadParameter('not in owner/repository format')
        

def validate_config_files(ctx, param, value):
   pattern = re.compile('.*\.cfg')
   if pattern.fullmatch(value.name) is not None:
       return value
   raise click.BadParameter('incorrect configuration format')

def validate_auth_config(ctx, param, value):
    value = validate_config_files(ctx, param, value)
    token = get_token(value)
    return token

def validate_rules_config(ctx, param, value):
    value = validate_config_files(ctx, param, value)
    rules = get_rules(value)
    return rules


@click.command('ghia')
@click.argument('reposlug',
        required = True,
        callback = validate_reposlug)
@click.option('-s', '--strategy',
        type = click.Choice(['append', 'set', 'change']),
        default = 'append',
        show_default = True,
        help = 'How to handle assignment collisions.')
@click.option('-d', '--dry-run', 'dryrun',
        is_flag = True,
        help = 'Run without making any changes.')
@click.option('-a', '--config-auth', 'config_auth',
        type = click.File('r'),
        required = True,
        callback = validate_auth_config,
        help = 'File with authorization configuration.')
@click.option('-r', '--config-rules', 'config_rules',
        type = click.File('r'),
        required = True,
        callback = validate_rules_config,
        help = 'File with assignment rules configuration.')
def cli(reposlug, strategy, dryrun, config_auth, config_rules):
    """CLI tool for automatic issue assigning of GitHub issues"""
        
    token = config_auth
    repo_path = f'{reposlug[0]}/{reposlug[1]}'
    rules = config_rules[0]
    fallback = config_rules[1]

    ghia = Ghia(token, rules, strategy, dryrun, fallback)
    reports = ghia.run_repo(reposlug)
    for report in reports:
        print_report(report)
