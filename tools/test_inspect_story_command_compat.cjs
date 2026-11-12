'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { inspect, IDS } = require('./inspect_story_command_compat.cjs');
const md5 = data => crypto.createHash('md5').update(data).digest('hex');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'danmemore-story-check-'));
try {
  const contents = path.join(root,'contents');
  const issues = IDS.map((id, i) => {
    const name = '1/master/divide_novel_command_enc/novelCommand' + id + '.enc';
    const file = path.join(contents,name);
    fs.mkdirSync(path.dirname(file),{recursive:true});
    const bytes = Buffer.alloc(32,i+1), reference = Buffer.alloc(32,100+i);
    fs.writeFileSync(file,bytes);
    return {path:name,status:'unverified_bytes', actual_md5:md5(bytes),
      reference_md5:md5(reference), historical_md5:md5(reference),
      actual_size:32,reference_size:32,historical_size:32};
  });
  const audit={issues};
  const before=issues.map(x=>fs.readFileSync(path.join(contents,x.path)));
  const report=inspect(audit,contents);
  assert.equal(report.file_count,6);
  assert.equal(report.verdict,'DO_NOT_IMPORT_UNVERIFIED_BYTES');
  assert(report.results.every(x=>x.audit_recheck==='MATCH' &&
    x.decode_probe==='NOT_RUN' && x.reference_md5_match===false &&
    x.verdict==='UNVERIFIED_DO_NOT_IMPORT'));
  assert(before.every((bytes,i)=>bytes.equals(fs.readFileSync(path.join(contents,issues[i].path)))));
  fs.writeFileSync(path.join(contents,issues[0].path),Buffer.alloc(32,77));
  const changed=inspect(audit,contents);
  assert.equal(changed.results[0].audit_recheck,'CHANGED_SINCE_AUDIT');
  fs.writeFileSync(path.join(contents,issues[0].path),before[0]);
  assert.throws(()=>inspect({issues:issues.slice(1)},contents),/exactly six/);
  assert.throws(()=>inspect({issues:[...issues.slice(0,5),issues[0]]},contents),/duplicate/);
  assert.throws(()=>inspect({issues:issues.map((x,i)=>i===0?{...x,reference_md5:'x'}:x)},contents),/invalid audit fingerprints/);
  assert.throws(()=>inspect({issues:issues.map((x,i)=>i===0?{...x,actual_size:17*1024*1024,reference_size:17*1024*1024,historical_size:17*1024*1024}:x)},contents),/invalid audit fingerprints/);
  const overlong = path.join(contents,issues[0].path);
  fs.writeFileSync(overlong,Buffer.alloc(16*1024*1024+1));
  assert.throws(()=>inspect(audit,contents),/exceeds diagnostic limit/);
  fs.writeFileSync(overlong,before[0]);
  const target=path.join(contents,issues[0].path);
  fs.unlinkSync(target);
  fs.symlinkSync(path.join(contents,issues[1].path),target);
  assert.throws(()=>inspect(audit,contents),/symlink refused/);
  console.log('Story command read-only diagnostics: 9 checks PASS (synthetic only)');
} finally {
  fs.rmSync(root,{recursive:true,force:true});
}
