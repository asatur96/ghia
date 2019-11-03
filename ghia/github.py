import configparser
import click
import flask
import hashlib
import hmac
import os
import re
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
        self.session.headers = {'User-Agent': 'python/ghia'}
        self.session.auth = self._token_auth

    def _token_auth(self, req):
        """
        This alters all our outgoing requests
        """
        req.headers['Authorization'] = 'token ' + self.token
        return req

    def _paginated_json_get(self, url, params=None):
        r = self.session.get(url, params=params)
        r.raise_for_status()
        json = r.json()
        if 'next' in r.links and 'url' in r.links['next']:
            json += self._paginated_json_get(r.links['next']['url'], params)
        return json

    def user(self):
        """
        Get current user authenticated by token
        """
        return self._paginated_json_get(f'{self.API}/user')

    def issues(self, owner, repo, state='open', assignee=None):
        """
        Get issues of a repo
        owner: GitHub user or org
        repo: repo name
        state: open, closed, all (default open)
        assignee: optional filter for assignees (None, "none", "<username>", or "*")
        """
        params = {'state': state}
        if assignee is not None:
            params['assignee'] = assignee
        url = f'{self.API}/repos/{owner}/{repo}/issues'
        return self._paginated_json_get(url, params)

    def set_issue_assignees(self, owner, repo, number, assignees):
        """
        Sets assignees for the issue. Replaces all existing assignees.
        owner: GitHub user or org
        repo: repo name
        number: issue id
        assignees: list of usernames (as strings)
        """
        url = f'{self.API}/repos/{owner}/{repo}/issues/{number}'
        r = self.session.patch(url, json={'assignees': assignees})
        r.raise_for_status()
        return r.json()['assignees']

    def set_issue_labels(self, owner, repo, number, labels):
        """
        Sets labels for the issue. Replaces all existing labels.
        owner: GitHub user or org
        repo: repo name
        number: issue id
        labels: list of labels (as strings)
        """
        url = f'{self.API}/repos/{owner}/{repo}/issues/{number}'
        r = self.session.patch(url, json={'labels': labels})
        r.raise_for_status()
        return r.json()['labels']

