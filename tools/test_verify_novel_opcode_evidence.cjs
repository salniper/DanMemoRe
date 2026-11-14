'use strict';
const assert=require('node:assert/strict');
const {
  loadEvidence,assertEvidence,classifyOriginalOpcode,verifySixScriptStats
}=require('./verify_novel_opcode_evidence.cjs');

const original=loadEvidence();
const counts=assertEvidence(original);
assert.equal(counts.size,25);
assert.equal([...counts.values()].reduce((a,b)=>a+b,0),801);
assert.equal(original.original_native_handler_class_names.length,34);

for (const observed of [1,11,20,29,41]) {
  const result=classifyOriginalOpcode(observed,original);
  assert.equal(result.status,'ORIGINAL_OPCODE_OBSERVED_HANDLER_UNMAPPED');
  assert.equal(result.can_execute,false);
}
assert.equal(classifyOriginalOpcode(0,original).status,'ORIGINAL_OPCODE_NOT_OBSERVED_IN_SIX_SCRIPTS');
assert.equal(classifyOriginalOpcode(42,original).status,'ORIGINAL_OPCODE_NOT_OBSERVED_IN_SIX_SCRIPTS');
assert.equal(classifyOriginalOpcode(-1,original).status,'REJECT_INVALID_OPCODE');
assert.equal(classifyOriginalOpcode(1.2,original).status,'REJECT_INVALID_OPCODE');
assert.equal(classifyOriginalOpcode('11',original).status,'REJECT_INVALID_OPCODE');

function makeReport(){
  const source=original.source_evidence.canonical_script_histograms;
  const ids=[751040548,751040550,751040806,751040815,751041273,751041275];
  const scripts=ids.map((id,index)=>{
    const owner=index===4 ? '751040548' : index===5 ? '751040550' : String(id);
    const histogram={...source[owner]};
    return {script_id:id,contiguous_record_ids:true,
      command_count:Object.values(histogram).reduce((a,b)=>a+b,0),
      opcode_histogram:histogram};
  });
  return {
    status:'SIX_OWNER_SCRIPTS_STRUCTURAL_SEQUENCE_EVIDENCE_ONLY',
    scripts, data_values_emitted:false,original_import_authorized:false,
    repeated_script_comparisons:[
      {script_id_a:751040548,script_id_b:751041273,
       compared_positions:123,command_code_and_all_params_equal:123,
       first_has_same_length:true,same_content_except_record_and_script_ids:true},
      {script_id_a:751040550,script_id_b:751041275,
       compared_positions:342,command_code_and_all_params_equal:342,
       first_has_same_length:true,same_content_except_record_and_script_ids:true}
    ]
  };
}

const baseline=verifySixScriptStats(makeReport(),original);
assert.equal(baseline.status,'MATCHES_OWNER_SCRIPTS_METADATA_ONLY_NOT_PLAYBACK');
assert.equal(baseline.original_import_authorized,false);
assert.equal(baseline.can_execute,false);
assert.equal(baseline.tested_nonduplicate_rows,801);

{
  const sample=makeReport();sample.scripts[2].opcode_histogram['11']++;
  assert.equal(verifySixScriptStats(sample,original).status,
               'DEVIATES_FROM_CAPTURED_OWNER_SCRIPTS_NO_IMPORT');
}
{
  const sample=makeReport();sample.scripts[0].script_id=751040000;
  assert.equal(verifySixScriptStats(sample,original).status,
               'DEVIATES_FROM_CAPTURED_OWNER_SCRIPTS_NO_IMPORT');
}
{
  const sample=makeReport();sample.repeated_script_comparisons[0].command_code_and_all_params_equal=122;
  assert.equal(verifySixScriptStats(sample,original).status,
               'DEVIATES_FROM_CAPTURED_OWNER_SCRIPTS_NO_IMPORT');
}
{
  const sample=makeReport();sample.original_import_authorized=true;
  assert.equal(verifySixScriptStats(sample,original).status,
               'DEVIATES_FROM_CAPTURED_OWNER_SCRIPTS_NO_IMPORT');
}
{
  const tampered=structuredClone(original);tampered.observed_opcodes[0].verified_native_handler='NovelCommandStillShow';
  assert.throws(()=>assertEvidence(tampered),/Unverified opcode semantic assignment/);
}
{
  const tampered=structuredClone(original);tampered.original_native_libapp_sha256='0'.repeat(64);
  assert.throws(()=>assertEvidence(tampered),/provenance/);
}
{
  const tampered=structuredClone(original);tampered.source_evidence.canonical_script_histograms['751040806']['11']++;
  assert.throws(()=>assertEvidence(tampered),/row count/);
}
{
  const tampered=structuredClone(original);tampered.original_native_handler_class_names.pop();
  assert.throws(()=>assertEvidence(tampered),/provenance/);
}
assert.equal(verifySixScriptStats({},original).status,'NOT_PROVEN_NO_IMPORT');
console.log('Original opcode registry and six-script aggregate evidence: 22 assertions PASS');
