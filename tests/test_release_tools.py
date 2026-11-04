"""Offline behavior tests. No Zotero writes, account keys, or network required."""
import importlib.util
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / 'skills/manuscript-export/scripts/export_manuscript.py'
UPDATE = ROOT / 'skills/kit-update/scripts/update_kit.py'
spec = importlib.util.spec_from_file_location('updater', UPDATE)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rwk-한글 시험-')
        self.directory = Path(self.temp.name).resolve()
        self.source = self.directory / '원고 공백.md'
        self.bib = self.directory / 'references.bib'
        self.output = self.directory / '결과 공백.docx'
        self.source.write_text('''---
title: "시험 원고"
lang: ko-KR
---

# 서론

합성 시험 근거 [@Tian2024, p. 5].
위키 인용 [[Literature/@Tian2024|저자 별칭]].
키 직접 링크 [[@Tian2024]].
노트 링크 [[Topic/연구 메모|연구 메모]].

> [!note]+ 제목
> ==강조 내용==
''', encoding='utf-8')
        self.bib.write_text('@article{Tian2024,author={Tian, Alice and Kim, Bob and Lee, Cara},'
                            'title={Synthetic test evidence},year={2024},journal={Test Journal}}', encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def run_export(self, *extra):
        return subprocess.run([sys.executable, str(EXPORT), str(self.source), '--mode', 'fixed',
                               '--bibliography', str(self.bib), '--output', str(self.output), *extra],
                              capture_output=True, text=True)

    def test_three_formats_render_english_citations_and_keep_korean_language(self):
        for form in ['korean', 'imrad', 'proposal']:
            with self.subTest(form=form):
                self.output = self.directory / f'{form}.docx'
                result = self.run_export('--format', form)
                self.assertEqual(result.returncode, 0, result.stderr)
                text = subprocess.check_output(['pandoc', str(self.output), '-t', 'plain'], text=True)
                self.assertIn('Tian et al., 2024', text)
                self.assertIn('Synthetic test evidence', text)
                self.assertIn('연구 메모', text)
                self.assertIn('강조 내용', text)
                self.assertNotIn('기타', text)
                self.assertNotIn('[!note]', text)
                self.assertNotIn('[[', text)
                with zipfile.ZipFile(self.output) as z:
                    self.assertIn('ko-KR', z.read('word/styles.xml').decode())
                    self.assertIn('맑은 고딕', z.read('word/styles.xml').decode())

    def test_missing_key_creates_reviewable_output_and_nonzero_status(self):
        self.source.write_text(self.source.read_text() + '\n없는 근거 [@MissingKeyForTest].\n')
        result = self.run_export()
        self.assertEqual(result.returncode, 2)
        self.assertTrue(self.output.is_file())
        log = Path(str(self.output) + '.warnings.txt').read_text()
        self.assertIn('MissingKeyForTest', log)
        self.assertIn('not found', log)

    def test_output_is_never_overwritten(self):
        self.output.write_bytes(b'keep existing bytes')
        result = self.run_export()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_bytes(), b'keep existing bytes')

    def test_missing_bibliography_does_not_create_word(self):
        self.bib.unlink()
        result = self.run_export()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_source_and_bib_preserved(self):
        before = (self.source.read_bytes(), self.bib.read_bytes())
        self.assertEqual(self.run_export().returncode, 0)
        self.assertEqual(before, (self.source.read_bytes(), self.bib.read_bytes()))

    def test_old_wikilink_title_representation(self):
        data = json.loads(subprocess.check_output(['pandoc', '-f', 'markdown', '-t', 'json'], input='x', text=True))
        data['blocks'] = [{'t': 'Para', 'c': [{'t': 'Link', 'c': [['', [], []],
                           [{'t': 'Str', 'c': 'alias'}], ['Literature/@Tian2024', 'wikilink']]}]}]
        result = subprocess.run(['pandoc', '-f', 'json', '-t', 'json', '--lua-filter',
                                 str(EXPORT.parent.parent/'assets/obsidian-cite.lua')],
                                input=json.dumps(data), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        cite = json.loads(result.stdout)['blocks'][0]['c'][0]
        self.assertEqual(cite['t'], 'Cite')
        self.assertEqual(cite['c'][0][0]['citationId'], 'Tian2024')


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rwk-update-한글 ')
        self.directory = Path(self.temp.name).resolve()
        self.old = self.directory / 'research-wiki-kit'
        self.old.mkdir()
        self.write_manifest(self.old, '0.2.1')
        (self.old/'custom.txt').write_text('my settings')
        self.bundle = self.directory / 'release.zip'
        self.make_bundle()

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self, directory, version):
        path = directory / '.claude-plugin/plugin.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'name': 'research-wiki-kit', 'version': version}))

    def make_bundle(self, version='0.3.0', extra=None):
        with zipfile.ZipFile(self.bundle, 'w') as z:
            prefix = 'research-wiki-kit-0.3.0/'
            z.writestr(prefix+'.claude-plugin/plugin.json', json.dumps({'name':'research-wiki-kit','version':version}))
            for name in updater.REQUIRED_SKILLS:
                z.writestr(prefix+f'skills/{name}/SKILL.md', 'test skill')
            for name in ['references/vault-layout.md','NOTICE.md','LICENSE']:
                z.writestr(prefix+name,'test')
            if extra:
                z.writestr(*extra)

    def run_update(self, *extra):
        return subprocess.run([sys.executable, str(UPDATE), '--archive', str(self.bundle),
                               '--expected-version', '0.3.0', '--target', str(self.old), *extra],
                              capture_output=True, text=True)

    def test_upgrade_keeps_backup_and_reports_restart(self):
        result = self.run_update()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(updater.manifest(self.old)['version'], '0.3.0')
        backups = list(self.directory.glob('research-wiki-kit.backup-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0]/'custom.txt').read_text(), 'my settings')
        self.assertIn('새 대화를 여세요', result.stdout)

    def test_check_does_not_mutate(self):
        result = self.run_update('--check')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(updater.manifest(self.old)['version'], '0.2.1')
        self.assertFalse(list(self.directory.glob('*.backup-*')))

    def test_version_mismatch_preserves_old_install(self):
        self.make_bundle(version='0.4.0')
        self.assertNotEqual(self.run_update().returncode, 0)
        self.assertEqual(updater.manifest(self.old)['version'], '0.2.1')

    def test_no_downgrade(self):
        self.write_manifest(self.old, '0.4.0')
        self.assertEqual(self.run_update().returncode, 0)
        self.assertEqual(updater.manifest(self.old)['version'], '0.4.0')

    def test_archive_paths_and_symlinks_rejected(self):
        for name in ['../escape.txt','root/../../escape.txt','root\\escape.txt','C:/escape.txt']:
            with self.subTest(name=name):
                self.make_bundle(extra=(name,'escape'))
                self.assertNotEqual(self.run_update().returncode,0)
                self.assertEqual(updater.manifest(self.old)['version'],'0.2.1')
        self.make_bundle()
        with zipfile.ZipFile(self.bundle,'a') as z:
            info=zipfile.ZipInfo('research-wiki-kit-0.3.0/link')
            info.create_system=3
            info.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(info,'/etc/passwd')
        self.assertNotEqual(self.run_update().returncode,0)

    def test_missing_skill_rejected(self):
        with zipfile.ZipFile(self.bundle,'w') as z:
            z.writestr('root/.claude-plugin/plugin.json',json.dumps({'name':'research-wiki-kit','version':'0.3.0'}))
        self.assertNotEqual(self.run_update().returncode,0)
        self.assertTrue((self.old/'custom.txt').is_file())

    def test_git_checkout_rejected(self):
        (self.old/'.git').write_text('gitdir: somewhere')
        self.assertNotEqual(self.run_update().returncode,0)

    def test_failed_move_restores_previous_install(self):
        kit = updater.validate_extract(self.bundle,self.directory/'extract','0.3.0')
        real = Path.rename
        def fail_new(path,target):
            if path.parent.name.startswith('.rwk-install-'):
                raise OSError('simulated locked file')
            return real(path,target)
        with patch.object(Path,'rename',fail_new):
            with self.assertRaises(OSError):
                updater.replace_install(kit,self.old)
        self.assertEqual(updater.manifest(self.old)['version'],'0.2.1')
        self.assertEqual((self.old/'custom.txt').read_text(),'my settings')

    def test_online_uses_release_tag_url(self):
        urls=[]
        def fake_download(url,destination):
            urls.append(url)
            if url==updater.API:
                destination.write_text(json.dumps({'tag_name':'v0.3.0','draft':False,'prerelease':False}))
            else:
                shutil.copy2(self.bundle,destination)
        with patch.object(updater,'download',fake_download), patch.object(sys,'argv',['update','--target',str(self.old)]):
            self.assertEqual(updater.main(),0)
        self.assertEqual(urls,[updater.API,'https://github.com/BrianJChoi/research-wiki-kit/archive/refs/tags/v0.3.0.zip'])

    def test_prerelease_does_not_replace(self):
        def fake_download(url,destination):
            destination.write_text(json.dumps({'tag_name':'v0.4.0-beta','prerelease':True}))
        with patch.object(updater,'download',fake_download), patch.object(sys,'argv',['update','--target',str(self.old)]):
            with self.assertRaises(ValueError):
                updater.main()
        self.assertEqual(updater.manifest(self.old)['version'],'0.2.1')


if __name__=='__main__':
    unittest.main(verbosity=2)
