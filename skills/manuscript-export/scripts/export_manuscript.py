# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Convert a Markdown manuscript without overwriting its source or output."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manuscript', type=Path)
    parser.add_argument('--mode', choices=['fixed', 'zotero'], default='fixed')
    parser.add_argument('--bibliography', type=Path)
    parser.add_argument('--format', choices=['korean', 'imrad', 'proposal'], default='proposal')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.manuscript.resolve()
    output = args.output.resolve()
    warnings = Path(str(output) + '.warnings.txt')
    assets = Path(__file__).resolve().parent.parent / 'assets'
    if not source.is_file() or source.suffix.lower() != '.md':
        parser.error('Markdown 원고 파일이 필요합니다.')
    if output.suffix.lower() != '.docx':
        parser.error('출력 파일은 .docx여야 합니다.')
    if output.exists() or warnings.exists():
        parser.error('출력 또는 경고 파일이 이미 있습니다. 새 파일명을 사용합니다.')
    pandoc = shutil.which('pandoc')
    if not pandoc:
        parser.error('Pandoc이 없습니다. 설치한 뒤 새 대화를 엽니다.')
    bib = args.bibliography.resolve() if args.bibliography else None
    if args.mode == 'fixed' and (not bib or not bib.is_file()):
        parser.error('고정 방식에는 --bibliography로 실제 bib 파일을 지정합니다.')
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [pandoc, str(source), '-f', 'markdown+wikilinks_title_after_pipe+mark',
               '--standalone', '--lua-filter', str(assets / 'obsidian-cite.lua'),
               '--reference-doc', str(assets / f'{args.format}.docx')]
    if args.mode == 'fixed':
        command += ['--bibliography', str(bib), '--csl', str(assets / 'apa.csl'),
                    '--lua-filter', str(assets / 'english-citations.lua')]
    else:
        command += ['--lua-filter', str(assets / 'zotero.lua'), '-M', 'zotero_csl_style=apa']
    # Create on the output filesystem, then publish only a completed conversion.
    with tempfile.TemporaryDirectory(prefix='.rwk-export-', dir=output.parent) as temp:
        draft = Path(temp) / 'output.docx'
        result = subprocess.run(command + ['-o', str(draft)], cwd=source.parent,
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
        log = '\n'.join(part.strip() for part in [result.stdout, result.stderr] if part.strip())
        warnings.write_text(log + '\n' if log else '경고 없음\n', encoding='utf-8')
        if log:
            print(log, file=sys.stderr)
        if result.returncode or not draft.is_file():
            print(f'내보내기에 실패했습니다. 기존 파일은 보존합니다. 경고: {warnings}', file=sys.stderr)
            return result.returncode or 1
        # Exclusive creation also prevents another process from overwriting a new output.
        with output.open('xb') as target, draft.open('rb') as incoming:
            shutil.copyfileobj(incoming, target)
    unresolved = any(word in log.lower() for word in ['not found', 'not in zotero', 'duplicates found', 'could not fetch'])
    print(f'Word: {output}\n방식: {args.mode} · 양식: {args.format}\n경고 기록: {warnings}')
    if unresolved:
        print('미해결 인용이 있습니다. 경고 기록을 확인합니다.', file=sys.stderr)
        return 2  # Output exists for teaching the missing-key case; not a clean success.
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.SubprocessError) as exc:
        print(f'내보내기 오류: {exc}', file=sys.stderr)
        sys.exit(1)
