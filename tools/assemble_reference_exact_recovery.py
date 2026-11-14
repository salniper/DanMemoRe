#!/usr/bin/env python3
"""Conservative offline intake for exact DanMemoRe original resources.

Inputs are the owner's audit, a 40-file verified overlay, and zero or more
independent candidate ZIPs. No originals are modified. Only a complete exact
40+12+1544 set can be staged, and even that is NOT game acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import zipfile

MAX_ENTRIES = 500_000
MAX_MEMBER = 32 * 1024 * 1024
MAX_BYTES_TO_HASH = 2 * 1024 * 1024 * 1024
# These refer to actual owner-supplied audit and the previously verified v2
# overlay, not a generic or reformattable JSON catalogue.
PINNED_OWNER_AUDIT_SHA256 = 'fd929c2ace550fe2b7a59dcff7294be756b29adcf81f92aadd89849b3c5c6f4c'
PINNED_VERIFIED40_SHA256 = 'df39400c3f664546332cb77087373249399a675b878eb460715c8a0f62b40780'
MD5 = re.compile(r'[0-9a-f]{32}\Z')


def load_pinned_owner_inputs(audit_path, overlay_path):
    """Fail closed when either provenance anchor differs from the received files.

    Only the command-line intake uses this pin; synthetic unit fixtures
    intentionally exercise the pure discovery functions without owner bytes.
    """
    for path, expected, label in (
        (audit_path, PINNED_OWNER_AUDIT_SHA256, 'owner audit'),
        (overlay_path, PINNED_VERIFIED40_SHA256, 'verified 40-file overlay'),
    ):
        if path.is_symlink() or not path.is_file():
            raise ValueError(label + ' is missing or a symlink')
        h = hashlib.sha256()
        with path.open('rb') as src:
            for part in iter(lambda: src.read(1024 * 1024), b''):
                h.update(part)
        if h.hexdigest() != expected:
            raise ValueError(label + ' SHA-256 differs from the pinned original')
    return json.loads(audit_path.read_text(encoding='utf-8'))


def checks(audit):
    issues = audit.get('issues')
    if not isinstance(issues, list):
        raise ValueError('invalid audit: issues')
    groups = {'bootstrap': {}, 'phase_manifests': {}, 'remaining': {}, 'backgrounds': {}}
    for row in issues:
        path, status = row.get('path'), row.get('status')
        if status == 'missing_with_historical_entry':
            group = 'bootstrap'
        elif status == 'unverified_bytes':
            group = 'phase_manifests' if isinstance(path,str) and path.startswith('1/manifests/phase.manifest.') else 'remaining'
        elif status == 'missing_from_historical_catalog':
            group = 'backgrounds'
        else:
            continue
        if not isinstance(path, str) or not path or path.startswith('/') or '\\' in path or any(x in ('', '.', '..') for x in path.split('/')):
            raise ValueError('unsafe target in audit')
        size, md5 = row.get('reference_size'), row.get('reference_md5')
        if not isinstance(size,int) or not 0 < size <= MAX_MEMBER or not isinstance(md5,str) or not MD5.fullmatch(md5):
            raise ValueError('invalid reference size or md5 for '+path)
        if path in groups[group]:
            raise ValueError('duplicate reference target '+path)
        if group == 'backgrounds' and not re.fullmatch(r'3/files/lottery/background/\d+\.png',path):
            raise ValueError('unexpected background path')
        if group == 'remaining' and not (path.endswith('.enc') or path in (
                '1/files/font/number.png',
                '3/files/ui_atlas/home_gacha/gacha_top_move_parts_text.json')):
            raise ValueError('unexpected reference mismatch')
        if group in ('bootstrap','phase_manifests','remaining') and (
                row.get('historical_md5')!=md5 or row.get('historical_size')!=size):
            raise ValueError('reference and historical fingerprints disagree')
        groups[group][path]=(size,md5)
    expected = {'bootstrap':33,'phase_manifests':7,'remaining':12,'backgrounds':1544}
    if len({path for group in groups.values() for path in group}) != sum(expected.values()):
        raise ValueError('duplicate path across recovery classes')
    if {k:len(v) for k,v in groups.items()} != expected:
        raise ValueError('unexpected recovery population')
    return groups


def safe_member(info):
    name = info.filename
    mode = info.external_attr >> 16
    return (not info.is_dir() and not info.flag_bits & 1 and name and
            not name.startswith('/') and '\\' not in name and
            all(x not in ('', '.', '..') for x in name.split('/')) and
            not stat.S_ISLNK(mode) and stat.S_IFMT(mode) in (0,stat.S_IFREG))


def member_bytes(zf, info, limit=MAX_MEMBER):
    if not 0 < info.file_size <= limit:
        raise ValueError('candidate member outside size limit')
    with zf.open(info) as stream:
        data=stream.read(info.file_size+1)
    if len(data)!=info.file_size:
        raise ValueError('decompressed file size changed')
    return data


def verify_base40(archive, groups):
    expected = {**groups['bootstrap'],**groups['phase_manifests']}
    if archive.is_symlink() or not archive.is_file():
        raise ValueError('40-file overlay must be an ordinary file')
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):
            raise ValueError('duplicate 40-file overlay path')
        selected={info.filename:info for info in z.infolist() if info.filename in expected}
        if set(selected)!=set(expected):
            raise ValueError('40-file overlay missing or extra exact targets')
        for name,(size,md5) in expected.items():
            info=selected[name]
            if not safe_member(info) or info.file_size!=size or hashlib.md5(member_bytes(z,info)).hexdigest()!=md5:
                raise ValueError('verified overlay byte mismatch: '+name)
    return len(expected)


def read_direct_candidate(root, relative):
    """Read an exact catalogue path from owner-extracted contents.

    Does not enumerate the large game tree, follow symlinks or rewrite bytes.
    """
    if root.is_symlink() or not root.is_dir():
        raise ValueError('candidate root must be a real directory')
    path=root
    for part in relative.split('/'):
        if part in ('', '.', '..'):
            raise ValueError('unsafe candidate path')
        path=path/part
        if path.is_symlink():
            raise ValueError('symlink in candidate directory path')
        if not path.exists():
            return None
    if not path.is_file():
        raise ValueError('candidate path is not a regular file')
    if path.stat().st_size>MAX_MEMBER:
        raise ValueError('candidate file exceeds read bound')
    with path.open('rb') as source:
        raw=source.read(MAX_MEMBER+1)
    if len(raw)>MAX_MEMBER:
        raise ValueError('candidate changed or exceeds read bound')
    return raw


def discover(audit, overlay, archives, directories=()):
    groups=checks(audit)
    base_count=verify_base40(overlay,groups)
    target={**groups['remaining'],**groups['backgrounds']}
    by_size={}
    for path,attrs in groups['remaining'].items():
        by_size.setdefault(attrs[0],[]).append((path,attrs[1]))
    hits={path:[] for path in target}
    inspected=0
    total_bytes=0
    for archive in archives:
        if archive.is_symlink() or not archive.is_file():
            raise ValueError('candidate ZIP must be a regular non-symlink file')
        with zipfile.ZipFile(archive) as z:
            infos=z.infolist()
            if len(infos)>MAX_ENTRIES:
                raise ValueError('too many candidate ZIP members')
            for info in infos:
                name=info.filename
                # Backgrounds require exactly the expected original path.
                rel=name[len('contents/'):] if name.startswith('contents/') else name
                is_background=rel in groups['backgrounds']
                possible=by_size.get(info.file_size,[])
                if not is_background and not possible:
                    continue
                if not safe_member(info):
                    raise ValueError('unsafe candidate member at matching size/path')
                if is_background and info.file_size!=groups['backgrounds'][rel][0]:
                    # Wrong-size file is evidence of a mismatch, not a hit.
                    continue
                total_bytes+=info.file_size
                if total_bytes>MAX_BYTES_TO_HASH:
                    raise ValueError('candidate read budget exceeded')
                inspected+=1
                content=member_bytes(z,info)
                digest=hashlib.md5(content).hexdigest()
                if is_background and digest==groups['backgrounds'][rel][1]:
                    if len(hits[rel])<4: hits[rel].append((str(archive),name))
                for path,expected_md5 in possible:
                    if digest==expected_md5 and len(hits[path])<4:
                        hits[path].append((str(archive),name))
    # Existing 14 GB owner extracts do not need to be repacked as a ZIP.
    # Directory sources use exact paths; renamed candidates remain ZIP-only.
    for directory in directories:
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('candidate directory must exist and be non-symlink')
        for base in (directory, directory/'contents'):
            if base.is_symlink():
                raise ValueError('candidate contents root is a symlink')
            if not base.is_dir():
                continue
            for name,(size,expected_md5) in target.items():
                raw=read_direct_candidate(base,name)
                if raw is None or len(raw)!=size:
                    continue
                total_bytes+=len(raw)
                if total_bytes>MAX_BYTES_TO_HASH:
                    raise ValueError('candidate read budget exceeded')
                inspected+=1
                if hashlib.md5(raw).hexdigest()==expected_md5 and len(hits[name])<4:
                    hits[name].append((str(base),None))
    missing={key:sorted(path for path in group if not hits[path])
             for key,group in [('remaining',groups['remaining']),('backgrounds',groups['backgrounds'])]}
    result={
        'status':'REFERENCE_EXACT_SOURCE_READY_STAGING_ONLY' if not any(missing.values()) else 'INCOMPLETE_REFERENCE_SOURCES_NOT_IMPORTABLE',
        'verified_base_overlay_files':base_count,
        'found_reference_exact_remaining':12-len(missing['remaining']),
        'found_reference_exact_backgrounds':1544-len(missing['backgrounds']),
        'missing_reference_exact_remaining':missing['remaining'],
        'missing_reference_exact_background_count':len(missing['backgrounds']),
        'missing_reference_exact_background_paths':missing['backgrounds'],
        'candidate_entries_hashed':inspected,
        'candidate_bytes_hashed':total_bytes,
        'independent_source_provenance_verified':False,
        'gameplay_verified':False,
        'original_import_authorized':False,
        'note':'A byte match alone does not prove independent historical origin or game compatibility. Never overwrite original contents.',
    }
    return groups,hits,result


def stage_all(overlay, groups, hits, destination):
    expected={**groups['bootstrap'],**groups['phase_manifests'],**groups['remaining'],**groups['backgrounds']}
    if any(path not in hits or not hits[path] for path in {**groups['remaining'],**groups['backgrounds']}):
        raise ValueError('not all 1556 missing references have exact candidate bytes')
    # Recheck after discovery: an altered 40-file ZIP must NEVER be copied
    # merely because its pathname was already verified once.
    verify_base40(overlay, groups)
    if destination.is_symlink() or destination.exists():
        raise ValueError('destination must be a new nonexisting directory')
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError('output parent not a real directory')
    parent=destination.parent.resolve(strict=True)
    if destination.resolve(strict=False).parent!=parent:
        raise ValueError('output path not an immediate child of parent')
    tmp=Path(tempfile.mkdtemp(prefix='.danmemore-exact-',dir=parent))
    try:
        with zipfile.ZipFile(overlay) as z:
            for name, (size, expected_md5) in {
                **groups['bootstrap'], **groups['phase_manifests']
            }.items():
                matches=[info for info in z.infolist() if info.filename == name]
                if len(matches)!=1 or not safe_member(matches[0]) or matches[0].file_size!=size:
                    raise ValueError('40-file source changed during staging: '+name)
                raw=member_bytes(z,matches[0])
                if len(raw)!=size or hashlib.md5(raw).hexdigest()!=expected_md5:
                    raise ValueError('40-file source fingerprint changed during staging: '+name)
                output=tmp/name; output.parent.mkdir(parents=True,exist_ok=True)
                output.write_bytes(raw)
        for name in {**groups['remaining'],**groups['backgrounds']}:
            src,member=hits[name][0]
            if member is None:
                raw=read_direct_candidate(Path(src),name)
                if raw is None:
                    raise ValueError('candidate file disappeared since discovery')
            else:
                with zipfile.ZipFile(src) as z:
                    infos=[i for i in z.infolist() if i.filename==member]
                    if len(infos)!=1 or not safe_member(infos[0]):
                        raise ValueError('source member ambiguous or unsafe')
                    raw=member_bytes(z,infos[0])
            # Both directory and ZIP candidates must pass exactly the same
            # immutable reference gate immediately before they are written.
            size,md5=expected[name]
            if len(raw)!=size or hashlib.md5(raw).hexdigest()!=md5:
                raise ValueError('candidate changed since discovery')
            output=tmp/name; output.parent.mkdir(parents=True,exist_ok=True)
            output.write_bytes(raw)
        (tmp/'RESTORE_STATUS.json').write_text(json.dumps({
            'verified_reference_exact_file_count':len(expected),
            'original_import_authorized':False,
            'original_game_playable':False,
            'owner_archive_modified':False,
            'warning':'Complete 1596-file overlay, not complete original 14GB archive; run separate source and native acceptance checks.'
        },indent=2)+'\n',encoding='utf-8')
        if destination.exists() or destination.is_symlink():
            raise ValueError('output appeared while staging')
        os.rename(tmp,destination)
    except BaseException:
        shutil.rmtree(tmp,ignore_errors=True)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--verified40',type=Path,required=True)
    parser.add_argument('--candidate-zip',type=Path,action='append',default=[])
    parser.add_argument('--candidate-dir',type=Path,action='append',default=[],
                        help='already-extracted contents directory, exact reference paths only')
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if args.apply and not args.output_dir:
        parser.error('--apply requires --output-dir')
    audit=load_pinned_owner_inputs(args.audit,args.verified40)
    groups,hits,report=discover(audit,args.verified40,
                                args.candidate_zip,args.candidate_dir)
    if args.apply:
        if report['status']!='REFERENCE_EXACT_SOURCE_READY_STAGING_ONLY':
            raise ValueError('incomplete sources: refusing to write an invalid recovery overlay')
        stage_all(args.verified40,groups,hits,args.output_dir)
        report['staged_overlay']=str(args.output_dir)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()