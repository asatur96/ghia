import enum
import re
import itertools
import requests
import click


class Report:
    """
    Simple container for reporting repo-pr label changes
    """
    def __init__(self, repo):
        self.repo = repo
        self.ok = True
        self.msgs = []
        self.is_exit = False
        self.number = int()
        self.fallback = None


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
    
    def post_issue_label(self, owner, repo, issue_number, label):
        url = f'{self.API}/repos/{owner}/{repo}/issues/{issue_number}/labels'
        r = self.session.post(url, json={"labels": label})
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


class Ghia:
    def __init__(self, token, rules,
            strategy = 'append', dryrun = None, fallback = None):
        self.github = GitHub(token)
        self.rules = rules
        self.strategy = strategy
        self.dryrun = dryrun
        self.fallback = fallback

    @property
    def defined_rules(self):
        return set(self.rules.keys())

    def _pattern_matching(self, rule, issue):
        pattern = re.compile(rule)
        if re.search(rule, issue, re.IGNORECASE) is not None:
            return True
        return False

    def _matching_rules(self, rules, issue):
        users = set()
        for user, patterns in rules.items():
            for rule in patterns:
                r = rule.split(':', 1)
                if r[0] == 'title':
                    if self._pattern_matching(r[1], issue['title']):
                        users.add(user)
                        break
                if r[0] == 'text':
                    if self._pattern_matching(r[1], issue['body']):
                        users.add(user)
                if r[0] == 'label':
                    found = False
                    for issue_label in issue['labels']:
                        if self._pattern_matching(r[1], issue_label['name']):
                            users.add(user)
                            found = True
                            break
                    if found:
                        break
                if r[0] == 'any':
                    if self._pattern_matching(r[1], issue['title']) or self._pattern_matching(r[1], issue['body']):
                        users.add(user)
                        break
                    found = False
                    for issue_label in issue['labels']:
                        if self._pattern_matching(r[1], issue_label['name']):
                            users.add(user)
                            found = True
                            break
                    if found:
                        break
        return sorted(users)

    def run_issue(self, owner, repo, issue):
        users = set(self._matching_rules(self.rules, issue))
        existing = set(l['login'] for l in issue['assignees'])
        new_users = users - existing
        ui = users & existing
        ud = existing - users 
        number = issue['number']
        res = {}
        if self.strategy == 'append':
            if new_users:
                if self.dryrun is False:
                    self.github.post_assignees(owner, repo, issue['number'], list(new_users))
            for u in existing:
                res[u] = '='
            for u in new_users:
                res[u] = '+'
        elif self.strategy == 'set':
            if self.dryrun is False:
                self.github.post_assignees(owner, repo, issue['number'], list(users))
            for u in ud:
                res[u] = '='
            for u in users:
                res[u] = '+'
        else:
            if self.dryrun is False:
                self.github.remove_assignees(owner, repo, issue['number'], list(ud))
                self.github.post_assignees(owner, repo, issue['number'], list(new_users))
            for u in ui:
                res[u] = '='
            for u in ud:
                res[u] = '-'
            for u in new_users:
                res[u] = '+'
        return res

    def run_repo(self, reposlug):
        repo_path = f'{reposlug[0]}/{reposlug[1]}'
        report = Report(repo_path)
        try:
            issues = self.github.issues(reposlug[0], reposlug[1])
        except Exception:
            error_msg = click.style('ERROR', fg = 'red', bold = True)
            click.secho(f'{error_msg}: Could not list issues for repository {report.repo}', err = True)
            exit(10)
        issue_reports = []
        for issue in issues:
            try:
                cur_report = Report(repo_path)
                url = issue['html_url']
                cur_report.number = issue['number']
                cur_report.msgs.append(f'({url})')

                answers = self.run_issue(reposlug[0], reposlug[1], issue)
                existing_labels = self.github.get_issue_labels(reposlug[0], reposlug[1], issue['number'])
                if not answers and self.fallback is not None:
                    existing_labels = self.github.get_issue_labels(reposlug[0], reposlug[1], issue['number'])
                    
                    is_exist_fallback_label = False
                    label = self.fallback['label'][0]
                    for el in existing_labels:
                        if el['name'] == label:
                            is_exist_fallback_label = True
                            cur_report.fallback = f'already has label "{label}"'
                            break
                    if not is_exist_fallback_label:
                        label = self.fallback['label'][0]
                        cur_report.fallback = f'added label "{label}"'
                        if self.dryrun is False:
                            self.github.post_issue_label(reposlug[0], reposlug[1], issue['number'], self.fallback['label'])

                for k in sorted(answers.keys(), key=str.casefold):
                    cur_report.msgs.append(answers[k])
                    cur_report.msgs.append(k)
                issue_reports.append(cur_report)
            except Exception:
                cur_report.ok = False
                issue_reports.append(cur_report)
                pass
        return issue_reports
