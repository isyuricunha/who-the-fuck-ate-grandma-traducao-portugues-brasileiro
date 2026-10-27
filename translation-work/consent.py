"""Affirmative contributor permission gate; reporting a bug is not consent."""
import json
import os
import sys
from native import require
from release import API

ATTESTATION = '- [x] I grant the contribution permissions in CONTRIBUTING.md and GAME-DEVELOPER-PERMISSION.md for my own contributions in this pull request.'


def validate(body, author, commits, records=()):
    require(ATTESTATION in body.splitlines(), 'Explicit checked contributor permission is missing')
    for commit in commits:
        login = (commit.get('author') or {}).get('login')
        require(bool(login), 'Unlinked commit author needs a separately recorded permission')
        if login != author:
            require(any(r.get('login') == login and commit['sha'] in r.get('commits', [])
                        and r.get('affirmative') is True and r.get('evidence_url') for r in records),
                    'No recorded permission for co-contributor: ' + login)
    return True


if __name__ == '__main__':
    try:
        from toolkit import ROOT, load
        event = load(__import__('pathlib').Path(os.environ['GITHUB_EVENT_PATH']))
        pr = event['pull_request']
        api = API(os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN'])
        commits, page = [], 1
        while True:
            chunk = api.request('GET', f'/pulls/{pr["number"]}/commits?per_page=100&page={page}')
            commits += chunk
            if len(chunk) < 100:
                break
            page += 1
        records = load(ROOT / '.github/contributor-consents.json')['consents']
        validate(pr.get('body') or '', pr['user']['login'], commits, records)
        print('Affirmative contributor permission recorded in pull request; preserve PR and commit links before merge.')
    except (ValueError, KeyError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
