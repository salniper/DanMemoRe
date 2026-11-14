#!/usr/bin/env python3
"""Synthetic only: no original game assets, passwords or cache bytes."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble_reference_exact_recovery as recover

def md5(data):
    return hashlib.md5(data).hexdigest()

STORIES = ['751040548','751040550','751040806','751040815','751041273','751041275']
MASTERS = ['adventureMission','downloadVoicePhase','lotteryWeightGroup','subscription']

def fixture(folder):
    audit={'issues':[]}
    base={}
    missing={}
    def add(path, category):
        raw=('synthetic-test:'+path).encode()
        record={'path':path,'reference_size':len(raw),'reference_md5':md5(raw)}
        record['status'] = ('missing_with_historical_entry' if category=='bootstrap'
            else 'missing_from_historical_catalog' if category=='background'
            else 'unverified_bytes')
        if category!='background':
            record.update(historical_size=len(raw), historical_md5=md5(raw))
        audit['issues'].append(record)
        (base if category in ('bootstrap','manifest') else missing)[path]=raw
    for i in range(33):
        add(f'1/files/ui_atlas/fixture/fixture_{i:02d}.json','bootstrap')
    for phase in (1,2,3,4,6,7,8):
        add(f'1/manifests/phase.manifest.{phase}','manifest')
    for id in STORIES:
        add(f'1/master/divide_novel_command_enc/novelCommand{id}.enc','remaining')
    for name in MASTERS:
        add(f'1/master/divide_enc/{name}.enc','remaining')
    add('1/files/font/number.png','remaining')
    add('3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json','remaining')
    for i in range(1544):
        add(f'3/files/lottery/background/{171000001+i}.png','background')
    overlay=folder/'overlay.zip'
    with zipfile.ZipFile(overlay,'w') as z:
        for path,raw in base.items(): z.writestr(path,raw)
    candidates=folder/'candidates.zip'
    with zipfile.ZipFile(candidates,'w') as z:
        for path,raw in missing.items():
            z.writestr('contents/'+path if '/lottery/background/' in path
                       else 'renamed/'+path.replace('/','-'),raw)
    return audit,overlay,candidates,base,missing

class ExactRestorationTests(unittest.TestCase):
    def test_complete_exact_set_stages_fresh_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit,overlay,candidate,base,missing=fixture(root)
            original=(md5(overlay.read_bytes()),md5(candidate.read_bytes()))
            groups,hits,report=recover.discover(audit,overlay,[candidate])
            self.assertEqual(report['status'],'REFERENCE_EXACT_SOURCE_READY_STAGING_ONLY')
            self.assertEqual(report['verified_base_overlay_files'],40)
            self.assertEqual(report['found_reference_exact_remaining'],12)
            self.assertEqual(report['found_reference_exact_backgrounds'],1544)
            result=root/'new-overlay'
            recover.stage_all(overlay,groups,hits,result)
            files=[x for x in result.rglob('*') if x.is_file()]
            self.assertEqual(len(files),1597) # 1596 exact originals + one status
            self.assertEqual((result/'1/files/ui_atlas/fixture/fixture_00.json').read_bytes(),
                             base['1/files/ui_atlas/fixture/fixture_00.json'])
            self.assertEqual((result/'3/files/lottery/background/171000001.png').read_bytes(),
                             missing['3/files/lottery/background/171000001.png'])
            self.assertEqual(original,(md5(overlay.read_bytes()),md5(candidate.read_bytes())))
            with self.assertRaisesRegex(ValueError,'nonexisting'):
                recover.stage_all(overlay,groups,hits,result)

    def test_missing_candidates_cannot_stage_partial_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit,overlay,_,_,_=fixture(root)
            groups,hits,report=recover.discover(audit,overlay,[])
            self.assertEqual(report['found_reference_exact_remaining'],0)
            self.assertEqual(report['missing_reference_exact_background_count'],1544)
            with self.assertRaisesRegex(ValueError,'not all 1556'):
                recover.stage_all(overlay,groups,hits,root/'should-not-exist')
            self.assertFalse((root/'should-not-exist').exists())

    def test_corrupt_overlay_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit,overlay,candidate,_,_=fixture(root)
            bad=root/'corrupt.zip'
            with zipfile.ZipFile(overlay) as original,zipfile.ZipFile(bad,'w') as writer:
                for i,name in enumerate(original.namelist()):
                    data=original.read(name)
                    writer.writestr(name,data+(b'TAMPER' if i==0 else b''))
            with self.assertRaisesRegex(ValueError,'overlay byte mismatch'):
                recover.discover(audit,bad,[candidate])

    def test_overlay_changed_after_discovery_is_not_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit,overlay,candidate,_,_=fixture(root)
            groups,hits,report=recover.discover(audit,overlay,[candidate])
            self.assertEqual(report['status'],'REFERENCE_EXACT_SOURCE_READY_STAGING_ONLY')
            entries={}
            with zipfile.ZipFile(overlay) as z:
                for name in z.namelist():
                    entries[name]=z.read(name)
            changed=next(iter(entries))
            entries[changed]+=b'TAMPER_AFTER_DISCOVERY'
            with zipfile.ZipFile(overlay,'w') as z:
                for name,raw in entries.items():
                    z.writestr(name,raw)
            output=root/'must-not-be-written'
            with self.assertRaisesRegex(ValueError,'overlay byte mismatch'):
                recover.stage_all(overlay,groups,hits,output)
            self.assertFalse(output.exists())

    def test_exact_directory_contents_without_rezipping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit,overlay,_,_,missing=fixture(root)
            extracted=root/'extracted'
            contents=extracted/'contents'
            for name,raw in missing.items():
                path=contents/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(raw)
            groups,hits,report=recover.discover(audit,overlay,[],[extracted])
            self.assertEqual(report['found_reference_exact_remaining'],12)
            self.assertEqual(report['found_reference_exact_backgrounds'],1544)
            output=root/'from-extracted-source'
            recover.stage_all(overlay,groups,hits,output)
            self.assertEqual((output/'1/files/font/number.png').read_bytes(),
                             missing['1/files/font/number.png'])
            self.assertEqual((output/'3/files/lottery/background/171000001.png').read_bytes(),
                             missing['3/files/lottery/background/171000001.png'])

    def test_directory_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit,overlay,_,_,_=fixture(root)
            contents=root/'contents'
            contents.mkdir()
            (contents/'1').symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):
                recover.discover(audit,overlay,[],[contents])

    def test_pinned_owner_inputs_reject_altered_catalogue(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit,overlay,_,_,_=fixture(root)
            audit_path=root/'audit.json'
            import json
            audit_path.write_text(json.dumps(audit),encoding='utf-8')
            owner_sha=hashlib.sha256(audit_path.read_bytes()).hexdigest()
            overlay_sha=hashlib.sha256(overlay.read_bytes()).hexdigest()
            with (
                patch.object(recover,'PINNED_OWNER_AUDIT_SHA256',owner_sha),
                patch.object(recover,'PINNED_VERIFIED40_SHA256',overlay_sha),
            ):
                self.assertEqual(len(recover.load_pinned_owner_inputs(
                    audit_path,overlay)['issues']),1596)
                audit_path.write_text(audit_path.read_text()+' ',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'SHA-256'):
                    recover.load_pinned_owner_inputs(audit_path,overlay)

    def test_traversal_match_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            audit,overlay,_,_,_=fixture(root)
            item=next(row for row in audit['issues']
                      if row['path']=='1/files/font/number.png')
            bad=root/'unsafe.zip'
            with zipfile.ZipFile(bad,'w') as writer:
                writer.writestr('../unsafe.bin',b'X'*item['reference_size'])
            with self.assertRaisesRegex(ValueError,'unsafe'):
                recover.discover(audit,overlay,[bad])

if __name__=='__main__':
    unittest.main()
