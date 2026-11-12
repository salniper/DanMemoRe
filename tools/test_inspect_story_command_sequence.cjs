'use strict';
const assert=require('node:assert/strict');
const {encodeBlock,encodeNumber}=require('./decode_master_data.cjs');
const {analyzeOne,analyzeSix,IDS}=require('./inspect_story_command_sequence.cjs');

const KEY=Buffer.alloc(16,5);
function syntheticScript(id,{badOrder=false,badIdentity=false,changedParam=false}={}) {
  const b=Buffer.alloc(2048);
  b.writeUInt32LE(20,0); // Root table and its two-row vector
  b.writeUInt16LE(6,12);b.writeUInt16LE(8,14);b.writeUInt16LE(4,16);
  b.writeInt32LE(8,20);b.writeUInt32LE(8,24);
  b.writeUInt32LE(2,32);
  b.writeUInt32LE(160-36,36);
  b.writeUInt32LE(320-40,40);
  let stringAt=600;
  for (const [index,table] of [[0,160],[1,320]]) {
    const vt=table-24;
    b.writeUInt16LE(24,vt);b.writeUInt16LE(64,vt+2);
    b.writeInt32LE(24,table);
    const offsets=[4,16,28,36,40,44,48,52,56,60];
    offsets.forEach((off,i)=>b.writeUInt16LE(off,vt+4+i*2));
    const base=75240548001;
    encodeNumber(base+index+(badOrder&&index?2:0),'long',KEY).copy(b,table+4);
    encodeNumber(Number(id)+(badIdentity&&index?1:0),'long',KEY).copy(b,table+16);
    encodeNumber(index===0?19:11,'int',KEY).copy(b,table+28);
    for(let i=0;i<7;i++) {
      const at=table+36+i*4;
      const raw=(changedParam && index===1 && i===3 ? 'changed' :
        (index===0?'alpha':'beta'))+'\0';
      const plain=Buffer.from(raw);
      const width=Math.max(8,Math.ceil((plain.length+4)/4)*4);
      const enc=encodeBlock(plain,KEY,width);
      b.writeUInt32LE(stringAt-at,at);
      b.writeUInt32LE(enc.length,stringAt);
      enc.copy(b,stringAt+4);
      stringAt+=4+enc.length;
    }
  }
  return b;
}

const all=new Map(IDS.map(id=>[id,syntheticScript(id)]));
const report=analyzeSix(all,KEY);
assert.equal(report.status,'SIX_OWNER_SCRIPTS_STRUCTURAL_SEQUENCE_EVIDENCE_ONLY');
assert.equal(report.scripts.length,6);
assert(report.scripts.every(x=>x.command_count===2&&x.contiguous_record_ids));
assert.equal(report.scripts[0].distinct_opcode_count,2);
assert.equal(report.scripts[0].opcode_histogram[19],1);
assert.equal(report.scripts[0].opcode_histogram[11],1);
assert.deepEqual(report.scripts[0].string_parameter_nonempty_rows,
  Object.fromEntries(Array.from({length:7},(_,i)=>['slot'+(i+3),2])));
assert.equal(report.repeated_script_comparisons.length,2);
assert(report.repeated_script_comparisons.every(x=>
  x.same_content_except_record_and_script_ids&&x.command_code_and_all_params_equal===2));
assert.equal(report.data_values_emitted,false);
assert.equal(report.original_import_authorized,false);
assert(!JSON.stringify(report).includes('alpha'));
assert(!JSON.stringify(report).includes('beta'));

assert.throws(()=>analyzeOne(syntheticScript(IDS[0],{badOrder:true}),KEY,IDS[0]),/noncontiguous/);
assert.throws(()=>analyzeOne(syntheticScript(IDS[0],{badIdentity:true}),KEY,IDS[0]),/identity/);
assert.throws(()=>analyzeOne(syntheticScript(IDS[0]),KEY,'not-an-id'),/unknown/);
assert.throws(()=>analyzeSix(new Map([[IDS[0],all.get(IDS[0])]]),KEY),/exactly six/);
assert.throws(()=>analyzeSix(all,Buffer.alloc(15)),/Invalid bounded/);
const other=new Map(all);
other.set(IDS[5],syntheticScript(IDS[5],{changedParam:true}));
const changed=analyzeSix(other,KEY);
assert.equal(changed.repeated_script_comparisons[1].command_code_and_all_params_equal,1);
assert.equal(changed.repeated_script_comparisons[1].same_content_except_record_and_script_ids,false);
console.log('Synthetic novel command identity, ordering and cross-script pairing: 20 checks PASS');
