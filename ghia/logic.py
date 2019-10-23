import enum
import re
import itertools
import requests
import click

from ghia.github import GitHub


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

                if not answers and self.fallback is not None:
                    existing_labels = set(l['name'] for l in issue['labels'])
                    
                    is_exist_fallback_label = False
                    label = self.fallback['label'][0]
                    for el in existing_labels:
                        if el == label:
                            is_exist_fallback_label = True
                            cur_report.fallback = f'already has label "{label}"'
                            break
                    if not is_exist_fallback_label:
                        label = self.fallback['label'][0]
                        cur_report.fallback = f'added label "{label}"'
                        if self.dryrun is False:
                            existing_labels.add(label)
                            self.github.reset_issue_label(reposlug[0], reposlug[1], issue['number'], list(existing_labels))

                for k in sorted(answers.keys(), key=str.casefold):
                    cur_report.msgs.append(answers[k])
                    cur_report.msgs.append(k)
                issue_reports.append(cur_report)
            except Exception:
                cur_report.ok = False
                issue_reports.append(cur_report)
                pass
        return issue_reports