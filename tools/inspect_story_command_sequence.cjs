'use strict';
// Original novelCommand slot-shape evidence only. This does not execute scripts,
// expose dialogue, bypass reference MD5, or claim publisher opcode semantics.
const { decodeTable, field, rows } = require('./decode_master_data.cjs');
const { profileStoryFields } = require('./inspect_story_field_profile.cjs');

const IDS = ['751040548','751040550','751040806','751040815','751041273','751041275'];
const PAIRS = [['751040548','751041273'],['751040550','751041275']];
const schema = [
  ['recordId','long'], ['scriptId','long'], ['opcode','int'],
  ...Array.from({length:7},(_,i)=>['param'+(i+3),'string'])
];
const MAX_STRLEN = 4096;
const MAX_OPCODES = 256;

// Only summary statistics are returned. Original param content is held in
// memory until the comparison is complete; never hash/export raw dialogue.
function analyzeOne(plain, numericKey, expectedId) {
  if (!IDS.includes(String(expectedId))) throw Error('unknown script identity');
  const prof = profileStoryFields(plain, numericKey);
  if (prof.status !== 'STRUCTURAL_FIELD_CANDIDATES_ONLY_NOT_SCHEMA' ||
      prof.row_count < 1 || prof.max_vtable_slots > 11 ||
      prof.slots.length !== 10 ||
      prof.slots.some((slot,i) =>
        slot.field_index !== i || slot.present_rows !== prof.row_count))
    throw Error('original story field layout is not the validated ten-slot shape');
  const ptrs=rows(plain);
  for (const ptr of ptrs) {
    // The script's 11th vtable slot exists but is never present in the
    // user's six samples. Any populated extra field is new evidence.
    if (field(plain,ptr,10)!==null)
      throw Error('unrecognized populated extra command slot');
  }
  const decoded = decodeTable(plain,schema,numericKey);
  if (decoded.length !== prof.row_count) throw Error('decoded row count mismatch');
  const counts={};
  const paramNonempty=Array(7).fill(0);
  const paramPresenceByOpcode={};
  let first=null,previous=null;
  const commandSignatures=[];
  for (const item of decoded) {
    if (!Number.isSafeInteger(item.recordId) || item.recordId <= 0 ||
        !Number.isSafeInteger(item.scriptId) ||
        item.scriptId !== Number(expectedId) ||
        !Number.isInteger(item.opcode) || item.opcode<0 ||
        item.opcode>MAX_OPCODES)
      throw Error('novel record identity or numeric opcode invalid');
    if (first===null) first=item.recordId;
    else if (item.recordId!==previous+1) throw Error('noncontiguous story command order');
    previous=item.recordId;
    counts[item.opcode]=(counts[item.opcode]||0)+1;
    if(!paramPresenceByOpcode[item.opcode]) paramPresenceByOpcode[item.opcode]=Array(7).fill(0);
    const params=Array.from({length:7},(_,i)=>item['param'+(i+3)]);
    for (let i=0;i<params.length;i++) {
      if (typeof params[i]!=='string' || params[i].length>MAX_STRLEN)
        throw Error('invalid or oversized decoded command parameter');
      if (params[i]) {
        paramNonempty[i]++;
        paramPresenceByOpcode[item.opcode][i]++;
      }
    }
    // Private compare-only representation; nothing based on it is written.
    commandSignatures.push([item.opcode,...params]);
  }
  return {
    publicReport:{
      status:'NATIVE_DECODER_SCRIPT_SLOT_LAYOUT_CONSISTENT_NOT_PLAYBACK_PROOF',
      script_id:Number(expectedId),
      command_count:decoded.length,
      first_record_id:first,
      last_record_id:previous,
      contiguous_record_ids:true,
      opcode_histogram:counts,
      distinct_opcode_count:Object.keys(counts).length,
      opcode_parameter_presence:Object.fromEntries(
        Object.entries(paramPresenceByOpcode).map(([code,counts])=>[code,
          Object.fromEntries(counts.map((n,i)=>['slot'+(i+3),n]))])),
      string_parameter_nonempty_rows:Object.fromEntries(
        paramNonempty.map((n,i)=>['slot'+(i+3),n])),
      original_reference_md5_replaced:false,
      playback_verified:false
    },
    privateSignatures:commandSignatures
  };
}

function analyzeSix(plainById,numericKey) {
  if (!(plainById instanceof Map) || plainById.size!==IDS.length)
    throw Error('expected exactly six original novel scripts');
  const data = new Map();
  for (const id of IDS) {
    if (!plainById.has(id)) throw Error('missing original novel script '+id);
    data.set(id,analyzeOne(plainById.get(id),numericKey,id));
  }
  const repeatComparisons = PAIRS.map(([a,b])=>{
    const x=data.get(a).privateSignatures;
    const y=data.get(b).privateSignatures;
    const n=Math.min(x.length,y.length);
    let equal=0;
    for(let i=0;i<n;i++)
      if (JSON.stringify(x[i])===JSON.stringify(y[i])) equal++;
    return {
      script_id_a:Number(a),script_id_b:Number(b),
      compared_positions:n,command_code_and_all_params_equal:equal,
      first_has_same_length:x.length===y.length,
      same_content_except_record_and_script_ids:
        x.length===y.length&&equal===n
    };
  });
  return {
    status:'SIX_OWNER_SCRIPTS_STRUCTURAL_SEQUENCE_EVIDENCE_ONLY',
    scripts:IDS.map(id=>data.get(id).publicReport),
    repeated_script_comparisons:repeatComparisons,
    data_values_emitted:false,
    original_import_authorized:false,
    limitations:'Inferred slot 2 is a numeric opcode candidate, not an identified command operation. 7 string slots have no verified publisher names. Full original-game playback and reference MD5 remain unproven.'
  };
}
module.exports={analyzeOne,analyzeSix,IDS};
