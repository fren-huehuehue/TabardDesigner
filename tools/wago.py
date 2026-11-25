"""Small cached client for wago.tools: DB2 tables (CSV), listfile search and game files from CASC.

Downloads land in a cache outside the repo (they are large and must stay off Google Drive):
TABARD_CACHE if set, else ~/.cache/tabard-designer. wago.tools rate-limits bursts; curl retries on 429.
"""
import csv
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get('TABARD_CACHE') or os.path.join(os.path.expanduser('~'), '.cache', 'tabard-designer')
DOCS = os.path.normpath(os.path.join(HERE, '..', 'docs'))


def download(url, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    r = subprocess.run(['curl', '-s', '-L', '-f', '--retry', '20', '--retry-delay', '3', '--retry-all-errors', url, '-o', out])
    if r.returncode != 0:
        if os.path.exists(out):
            os.remove(out)
        raise RuntimeError(f'download failed: {url}')
    return out


def file(fid, build=None):
    """Path to a game file by FileDataID. Pass build when the latest copy does not match its siblings."""
    name = f'{fid}.dat' if not build else f'{fid}@{build}.dat'
    url = f'https://wago.tools/api/casc/{fid}?download' + (f'&build={build}' if build else '')
    return download(url, os.path.join(CACHE, 'files', name))


def table(name, build=None):
    """A DB2 table as a list of dicts: the current retail build, or the given build."""
    url = f'https://wago.tools/db2/{name}/csv' + (f'?build={build}' if build else '')
    out = download(url, os.path.join(CACHE, 'db2', f'{name}.csv' if not build else f'{name}@{build}.csv'))
    with open(out, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def search(query):
    """Listfile search: {FileDataID: path}."""
    out = download(f'https://wago.tools/api/files?search={query}', os.path.join(CACHE, 'search', query.replace('/', '_') + '.json'))
    return {int(k): v for k, v in json.load(open(out)).items()}
