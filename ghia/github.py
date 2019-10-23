import enum
import re
import itertools
import requests


class GitHub:
    """
    This class can communicate with the GitHub API
    just give it a token and go.
    """
    API = 'https://api.github.com'

    def __init__(self, token, session=None):
        """
        token: GitHub token
        session: optional requests session
        """
        self.token = token
        self.session = session or requests.Session()
        self.session.headers = {'User-Agent': 'ghia'}
        self.session.auth = self._token_auth

    def _token_auth(self, req):
        """
        This alters all our outgoing requests
        """
        req.headers['Authorization'] = 'token ' + self.token
        return req

    def _issues_json_get(self, url, params=None):
        r = self.session.get(url, params=params)
        r.raise_for_status()
        json = r.json()
        if 'next' in r.links and 'url' in r.links['next']:
            json += self._issues_json_get(r.links['next']['url'], params)
        return json

    def user(self):
        """
        Get current user authenticated by token
        """
        return self._issues_json_get(f'{self.API}/user')

    def issues(self, owner, repo):
        try:
            params = {'state': 'open'}
            url = f'{self.API}/repos/{owner}/{repo}/issues'
            return self._issues_json_get(url, params)
        except:
            error_msg = click.style('ERROR', fg='red', bold=True)
            error_msg = f'{error_msg}: Could not list issues for repository {repo_path}'
            click.secho(error_msg, err=True)
            sys.exit(10)
    
    def get_issue_labels(self, owner, repo, issue_number):
        url = f'{self.API}/repos/{owner}/{repo}/issues/{issue_number}/labels'
        return self._issues_json_get(url)
    
    def reset_issue_label(self, owner, repo, issue_number, label):
        url = f'{self.API}/repos/{owner}/{repo}/issues/{issue_number}'
        r = self.session.patch(url, json={"labels": label})
        r.raise_for_status()

    def post_assignees(self, owner, repo, number, assignees):
        url = f'{self.API}/repos/{owner}/{repo}/issues/{number}/assignees'
        r = self.session.post(url, json={'assignees': assignees})
        r.raise_for_status()
        return r.json()['assignees']

    def remove_assignees(self, owner, repo, number, assignees):
        url = f'{self.API}/repos/{owner}/{repo}/issues/{number}/assignees'
        r = self.session.delete(url, json={'assignees': assignees})
        r.raise_for_status()
        return r.json()['assignees']