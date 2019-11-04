import configparser
import click
import flask
import hashlib
import hmac
import os
import re
import requests

from ghia.logic import GHIA, PrinterObserver


def parse_rules(cfg):
    """
    Parse labels to dict where label is key and list
    of patterns is corresponding value
    cfg: ConfigParser with loaded configuration of labels
    """
    patterns = {
        username: list(filter(None, cfg['patterns'][username].splitlines()))
        for username in cfg['patterns']
    }
    fallback = cfg.get('fallback', 'label', fallback=None)
    for user_patterns in patterns.values():
        for pattern in user_patterns:
            t, p = pattern.split(':', 1)
            assert t in GHIA.MATCHERS.keys()
    return patterns, fallback


def get_rules(ctx, param, config_rules):
    """
    Extract labels from labels config and do the checks
    config_rules: ConfigParser with loaded configuration of labels
    """
    try:
        cfg_rules = configparser.ConfigParser()
        cfg_rules.optionxform = str
        cfg_rules.read_file(config_rules)
        return parse_rules(cfg_rules)
    except Exception:
        raise click.BadParameter('incorrect configuration format')


def get_token(ctx, param, config_auth):
    """
    Extract token from auth config and do the checks
    config_auth: ConfigParser with loaded configuration of auth
    """
    try:
        cfg_auth = configparser.ConfigParser()
        cfg_auth.read_file(config_auth)
        return cfg_auth.get('github', 'token')
    except Exception:
        raise click.BadParameter('incorrect configuration format')


def parse_reposlug(ctx, param, reposlug):
    try:
        owner, repo = reposlug.split('/')
        return owner, repo
    except ValueError:
        raise click.BadParameter('not in owner/repository format')


@click.command('ghia')
@click.argument('reposlug', type=click.STRING, callback=parse_reposlug)
@click.option('-s', '--strategy', default=GHIA.DEFAULT_STRATEGY,
              show_default=True, type=click.Choice(GHIA.STRATEGIES.keys()),
              envvar=GHIA.ENVVAR_STRATEGY,
              help='How to handle assignment collisions.')
@click.option('--dry-run', '-d', is_flag=True, envvar=GHIA.ENVVAR_DRYRUN,
              help='Run without making any changes.')
@click.option('-a', '--config-auth', type=click.File('r'), callback=get_token,
              help='File with authorization configuration.', required=True)
@click.option('-r', '--config-rules', type=click.File('r'), callback=get_rules,
              help='File with assignment rules configuration.', required=True)
def cli(reposlug, strategy, dry_run, config_auth, config_rules):
    """CLI tool for automatic issue assigning of GitHub issues"""
    token = config_auth
    rules, fallback_label = config_rules
    owner, repo = reposlug
    ghia = GHIA(token, rules, fallback_label, dry_run, strategy)
    ghia.add_observer('printer', PrinterObserver)
    ghia.run(owner, repo)
