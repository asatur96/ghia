import configparser
import flask
import hashlib
import hmac
import jinja2
import os

from ghia.utils import parse_rules
from ghia.utils import parse_fallback
from ghia.logic import Ghia

def webhook_verify_signature(payload, signature, secret, encoding='utf-8'):
    h = hmac.new(secret.encode(encoding), payload, hashlib.sha1)
    return hmac.compare_digest('sha1=' + h.hexdigest(), signature)

def process_webhook_issues(payload):
    ghia = flask.current_app.config['ghia']
    print('process webhook issues')
    try:
        action = payload['action']
        issues = payload['issues']
        issue_number = payload['number']
        issue_url = ['url'].split('/')
        owner = issue_url[-4]
        repo = issue_url[-3]
        reposlug = f'{owner}/{repo}'

        if action not in ('opened', 'synchronize'):
            flask.current_app.logger.info(
                f'Action {action} from {reposlug}#{issue_number} skipped'
            )
            return 'Accepted but action not processed', 202

        ghia.run_repo(owner, repo)

        flask.current_app.logger.info(
            f'Action {action} from {reposlug}#{issue_number} processed'
        )
        return 'Issue successfully filabeled', 200
    except (KeyError, IndexError):
        flask.current_app.logger.info(
            f'Incorrect data entity from IP {flask.request.remote_addr}'
        )
        flask.abort(422, 'Missing required payload fields')
    except Exception:
        flask.current_app.logger.error(
            f'Error occurred while processing {repo}#{issue_number}'
        )
        flask.abort(500, 'Processing issue error')

def process_webhook_ping(payload):
    try:
        repo = payload['repository']['full_name']
        hook_id = payload['hook_id']
        flask.current_app.logger.info(
            f'Accepting PING from {repo}#WH-{hook_id}'
        )
        return 'PONG', 200
    except KeyError:
        flask.current_app.logger.info(
            f'Incorrect data entity from IP {flask.request.remote_addr}'
        )
        flask.abort(422, 'Missing payload contents')

webhook_processors = {
    'issues': process_webhook_issues,
    'ping': process_webhook_ping
}

def create_app(*args, ** kwargs):
    app = flask.Flask(__name__)
    cfg = configparser.ConfigParser()
    if 'GHIA_CONFIG' not in os.environ:
        app.logger.critical('Config not supplied by envvar FILABEL_CONFIG')
        exit(1)
    configs = os.environ['GHIA_CONFIG'].split(':')
    cfg.read(configs)

    try:
        app.config['rules'] = parse_rules(cfg)
    except Exception:
        app.logger.critical('incorrect configuration format', err=True)
        exit(1)

    try:
        app.config['github_token'] = cfg.get('github', 'token')
        app.config['secret'] = cfg.get('github', 'secret', fallback=None)
    except Exception:
        app.logger.critical('incorrect configuration format', err=True)
        exit(1)

    ghia = Ghia(app.config['github_token'], app.config['rules'])

    try:
        app.config['github_user'] = ghia.github.user()
        app.config['ghia'] = ghia
    except Exception:
        app.logger.critical('Bad token: could not get GitHub user!', err=True)
        exit(1)
    
    @app.template_filter('github_user_link')
    def github_user_link_filter(github_user):
        url = flask.escape(github_user['html_url'])
        login = flask.escape(github_user['login'])
        return jinja2.Markup(f'<a href="{url}" target="_blank">{login}</a>')
    
    @app.route('/', methods=['GET'])
    def index():
        print('method get')
        return flask.render_template(
            'infopage.html',
            rules=flask.current_app.config['rules'],
            user=flask.current_app.config['github_user']
        )
    
    @app.route('/', methods=['POST'])
    def webhook_listener():
        print('method post')
        signature = flask.request.headers.get('X-Hub-Signature', '')
        event = flask.request.headers.get('X-GitHub-Event', '')
        payload = flask.request.get_json()

        secret = flask.current_app.config['secret']

        if secret is not None and not webhook_verify_signature(
                flask.request.data, signature, secret
        ):
            flask.current_app.logger.warning(
                f'Attempt with bad secret from IP {flask.request.remote_addr}'
            )
            flask.abort(401, 'Bad webhook secret')

        if event not in webhook_processors:
            supported = ', '.join(webhook_processors.keys())
            flask.abort(400, f'Event not supported (supported: {supported})')

        return webhook_processors[event](payload)

    return app
