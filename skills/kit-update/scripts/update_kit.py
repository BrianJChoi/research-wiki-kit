# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Install a verified release archive while keeping the previous install as backup."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import urllib.request
import zipfile

REPOSITORY = 'BrianJChoi/research-wiki-kit'
API = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
REQUIRED_SKILLS = ('zotero-add-paper', 'paper-note', 'research-search', 'storm-perspectives',
                   'manuscript-draft', 'cite-check', 'manuscript-export', 'kit-update',
                   'wiki-setup', 'ingest', 'query')


def version(value):
    if not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('정식 x.y.z 버전만 설치합니다.')
    return tuple(map(int, value.split('.')))


def manifest(root):
    data = json.loads((root / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
    if data.get('name') != 'research-wiki-kit':
        raise ValueError('키트 이름이 맞지 않습니다.')
    version(data['version'])
    return data


def download(url, destination):
    request = urllib.request.Request(url, headers={'User-Agent': 'research-wiki-kit-updater',
                                                  'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open('wb') as out:
        shutil.copyfileobj(response, out)


def validate_extract(archive, directory, expected):
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if not entries or sum(i.file_size for i in entries) > 100_000_000:
            raise ValueError('빈 압축본이거나 압축 해제 크기가 너무 큽니다.')
        roots = set()
        seen = set()
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename
                    or ':' in entry.filename or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError('안전하지 않은 압축 경로입니다.')
            if not path.parts:
                raise ValueError('빈 압축 경로입니다.')
            key = str(path).casefold()
            if key in seen:
                raise ValueError('중복 압축 경로입니다.')
            seen.add(key)
            roots.add(path.parts[0])
        if len(roots) != 1:
            raise ValueError('키트 루트 폴더가 하나여야 합니다.')
        bundle.extractall(directory)
    kit = directory / roots.pop()
    data = manifest(kit)
    if data['version'] != expected:
        raise ValueError('태그와 plugin.json 버전이 다릅니다.')
    for name in REQUIRED_SKILLS:
        if not (kit / 'skills' / name / 'SKILL.md').is_file():
            raise ValueError(f'스킬 파일이 없습니다: {name}')
    for relative in ['references/vault-layout.md', 'NOTICE.md', 'LICENSE']:
        if not (kit / relative).is_file():
            raise ValueError(f'필수 파일이 없습니다: {relative}')
    return kit


def replace_install(kit, target):
    # Keep all moves on one filesystem; a Windows rename can fail when files are open.
    target.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = target.with_name(f'{target.name}.backup-{stamp}-{os.getpid()}')
    if backup.exists():
        raise ValueError('백업 이름이 이미 있습니다. 다시 실행합니다.')
    with tempfile.TemporaryDirectory(prefix='.rwk-install-', dir=target.parent) as temp:
        staged = Path(temp) / 'research-wiki-kit'
        shutil.copytree(kit, staged)
        had_old = target.exists()
        if had_old:
            target.rename(backup)
        try:
            staged.rename(target)
        except OSError:
            if had_old:
                backup.rename(target)
            raise
    return backup if had_old else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=Path.home() / '.claude/skills/research-wiki-kit')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--archive', type=Path, help='검증할 오프라인 태그 zip')
    parser.add_argument('--expected-version', help='오프라인 태그의 x.y.z 버전')
    args = parser.parse_args()
    target = args.target.expanduser().absolute()
    if target.name != 'research-wiki-kit' or any(p.is_symlink() for p in [target, *target.parents]):
        raise ValueError('설치 폴더 이름은 research-wiki-kit이어야 하며 심볼릭 링크를 사용할 수 없습니다.')
    if (target / '.git').exists():
        raise ValueError('Git 작업 저장소는 업데이트하지 않습니다. 복사 설치 폴더를 지정합니다.')
    current = manifest(target)['version'] if target.exists() else '0.0.0'
    with tempfile.TemporaryDirectory(prefix='rwk-release-') as temp:
        temp = Path(temp)
        if args.archive:
            if not args.expected_version:
                parser.error('--archive에는 --expected-version이 필요합니다.')
            latest = args.expected_version
            archive = args.archive.resolve()
        else:
            release_json = temp / 'release.json'
            download(API, release_json)
            release = json.loads(release_json.read_text(encoding='utf-8'))
            tag = release.get('tag_name', '')
            if release.get('draft') or release.get('prerelease') or not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
                raise ValueError('정식 릴리스 태그가 아닙니다.')
            latest = tag[1:]
            archive = temp / 'release.zip'
        version(latest)
        print(f'현재 {current} → 정식 릴리스 {latest}')
        if version(latest) <= version(current):
            print('이미 같거나 더 최신 버전입니다. 설치본을 유지합니다.')
            return 0
        if args.check:
            print('업데이트할 수 있습니다. --check를 빼고 실행합니다.')
            return 0
        if not args.archive:
            download(f'https://github.com/{REPOSITORY}/archive/refs/tags/v{latest}.zip', archive)
        kit = validate_extract(archive, temp / 'extracted', latest)
        backup = replace_install(kit, target)
        print(f'설치: {target}\n백업: {backup or "이전 설치 없음"}')
        changelog = kit / 'CHANGELOG.md'
        if changelog.is_file():
            text = changelog.read_text(encoding='utf-8')
            section = re.search(rf'^## {re.escape(latest)}\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
            if section:
                print(section.group(1).strip())
        print('새 대화를 여세요.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f'업데이트 실패: {exc}\n기존 설치본과 백업을 확인합니다.', file=sys.stderr)
        sys.exit(1)
