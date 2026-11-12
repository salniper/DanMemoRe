'use strict';
// Evidence boundary for original novelCommand opcode semantics.
// A source-file handler name is NOT an opcode mapping. This module never
// executes, renders, imports, rewrites or grants anything in the game.
const fs = require('node:fs');
const path = require('node:path');
const PINNED_SOURCE = 'e49a8cc7991f8946365a28aebad605ce566b034826dd4b34a982ab18b38303b3';
const CANONICAL_SCRIPTS = [751040548,751040550,751040806,751040815];
const ALL_SCRIPTS = [...CANONICAL_SCRIPTS,751041273,751041275];
const REPEATED = [[751040548,751041273,123],[751040550,751041275,342]];
const RECORDED_ROWS = 1266, UNIQUE_ROWS = 801, PAIR_ROWS = 465;
const MAX_CLASSES = 128, MAX_OPCODES = 256;

function loadEvidence(file = path.join(__dirname,'../data/danmemore-novel-opcode-evidence.json')) {
  return JSON.parse(fs.readFileSync(file,'utf8'));
}
function assertEvidence(e) {
  if (!e || e.format !== 'DANMEMORE_NATIVE_NOVEL_OPCODE_EVIDENCE_V1' ||
      e.original_native_libapp_sha256 !== PINNED_SOURCE ||
      e.unknown_opcode_behavior !== 'FAIL_CLOSED_NO_GAMEPLAY_EXECUTION' ||
      !Array.isArray(e.observed_opcodes) || e.observed_opcodes.length !== 25 ||
      !Array.isArray(e.original_native_handler_class_names) ||
      e.original_native_handler_class_names.length !== 34 ||
      e.original_native_handler_class_names.length > MAX_CLASSES ||
      !e.source_evidence || e.source_evidence.original_story_record_count !== RECORDED_ROWS ||
      e.source_evidence.unique_script_record_count !== UNIQUE_ROWS ||
      e.source_evidence.repeated_script_record_count !== PAIR_ROWS ||
      e.source_evidence.original_reference_md5_passed !== false ||
      e.source_evidence.real_client_opcode_dispatch_verified !== false ||
      e.source_evidence.ayn_thor_playback_verified !== false)
    throw new Error('Invalid original-opcode evidence provenance');
  const counts = new Map();
  let total = 0, previous = -1;
  for (const item of e.observed_opcodes) {
    if (!item || !Number.isSafeInteger(item.opcode) || item.opcode < 0 ||
        item.opcode >= MAX_OPCODES || item.opcode <= previous ||
        !Number.isSafeInteger(item.nonduplicate_record_count) ||
        item.nonduplicate_record_count <= 0 ||
        item.handler_mapping_status !== 'UNMAPPED_OPCODE_ONLY' ||
        item.verified_native_handler !== null)
      throw new Error('Unverified opcode semantic assignment or invalid record count');
    counts.set(item.opcode,item.nonduplicate_record_count);
    total += item.nonduplicate_record_count;
    previous = item.opcode;
  }
  if (total !== UNIQUE_ROWS || counts.size !== 25)
    throw new Error('Invalid native owner-script opcode totals');
  // The four unique script files also have a pinned per-script distribution.
  // This prevents an aggregate-equivalent yet reordered/altered script mix
  // from being incorrectly attributed to the owner's six actual files.
  const perScript=e.source_evidence.canonical_script_histograms;
  if (!perScript || Object.keys(perScript).length !== CANONICAL_SCRIPTS.length)
    throw Error('Missing canonical original script distribution');
  const perCode = new Map(), perTotal = 0;
  const perCounts = [123,342,90,246];
  for (let i=0;i<CANONICAL_SCRIPTS.length;i++) {
    const h=perScript[String(CANONICAL_SCRIPTS[i])];
    if (!h || typeof h !== 'object' || Array.isArray(h))
      throw Error('Invalid canonical original script histogram');
    let scriptTotal=0;
    for(const [codeText,num] of Object.entries(h)) {
      const code=Number(codeText);
      if (!Number.isSafeInteger(code) || String(code)!==codeText ||
          !counts.has(code) || !Number.isSafeInteger(num) || num<=0)
        throw Error('Invalid original script numeric histogram');
      scriptTotal+=num;
      perCode.set(code,(perCode.get(code)||0)+num);
    }
    if (scriptTotal!==perCounts[i])
      throw Error('Invalid original script row count');
    perTotal+=scriptTotal;
  }
  if (perTotal!==UNIQUE_ROWS || perCode.size!==counts.size ||
      [...counts].some(([code,num])=>perCode.get(code)!==num))
    throw Error('Owner script opcode distribution is internally inconsistent');
  const repeats=e.source_evidence.repeat_pair_identical_command_rows;
  if (!repeats ||
      repeats['751041273']?.same_as!=='751040548' || repeats['751041273']?.rows!==123 ||
      repeats['751041275']?.same_as!=='751040550' || repeats['751041275']?.rows!==342)
    throw Error('Original repeated-script metadata is incomplete');
  const classes = e.original_native_handler_class_names;
  if (new Set(classes).size !== classes.length ||
      classes.some((name,i) => typeof name !== 'string' ||
        !/^NovelCommand[A-Za-z0-9_]+$/.test(name) ||
        (i && name <= classes[i-1])))
    throw new Error('Invalid original native handler name evidence');
  return counts;
}
function classifyOriginalOpcode(code, evidence) {
  const counts = assertEvidence(evidence);
  if (!Number.isSafeInteger(code) || code < 0 || code >= MAX_OPCODES)
    return { status:'REJECT_INVALID_OPCODE', can_execute:false };
  return counts.has(code)
    ? {status:'ORIGINAL_OPCODE_OBSERVED_HANDLER_UNMAPPED', can_execute:false}
    : {status:'ORIGINAL_OPCODE_NOT_OBSERVED_IN_SIX_SCRIPTS', can_execute:false};
}
function verifySixScriptStats(report, evidence) {
  const expected = assertEvidence(evidence);
  if (!report || report.status !== 'SIX_OWNER_SCRIPTS_STRUCTURAL_SEQUENCE_EVIDENCE_ONLY' ||
      !Array.isArray(report.scripts) || report.scripts.length !== ALL_SCRIPTS.length ||
      !Array.isArray(report.repeated_script_comparisons))
    return { status:'NOT_PROVEN_NO_IMPORT', differences:['INVALID_SCRIPT_EVIDENCE'] };
  const actual = new Map(), differences = [];
  for(let i = 0;i < ALL_SCRIPTS.length;i++) {
    const script = report.scripts[i];
    if (!script || script.script_id !== ALL_SCRIPTS[i] ||
        !Number.isSafeInteger(script.command_count) || !script.contiguous_record_ids ||
        typeof script.opcode_histogram !== 'object' || !script.opcode_histogram) {
      differences.push('INVALID_SCRIPT_ID_OR_ORDER');
      continue;
    }
    const canonicalId=String(i >= CANONICAL_SCRIPTS.length ?
      (i===4 ? CANONICAL_SCRIPTS[0] : CANONICAL_SCRIPTS[1]) : ALL_SCRIPTS[i]);
    const expectedPerScript=evidence.source_evidence.canonical_script_histograms[canonicalId];
    const expectedScriptRows=i===0||i===4 ? 123 : i===1||i===5 ? 342 : i===2 ? 90 : 246;
    if (script.command_count!==expectedScriptRows ||
        Object.keys(script.opcode_histogram).length!==Object.keys(expectedPerScript).length ||
        Object.entries(expectedPerScript).some(([key,count])=>
          script.opcode_histogram[key]!==count))
      differences.push('OWNER_SCRIPT_PER_FILE_OPCODE_COUNTS_CHANGED');
    if (i >= CANONICAL_SCRIPTS.length) continue;
    for (const [str,num] of Object.entries(script.opcode_histogram)) {
      const code = Number(str);
      if (!Number.isSafeInteger(code) || code < 0 || code >= MAX_OPCODES ||
          !Number.isSafeInteger(num) || num < 0) {
        differences.push('INVALID_SCRIPT_OPCODE_HISTOGRAM');
        continue;
      }
      actual.set(code,(actual.get(code)||0)+num);
    }
  }
  const mismatch = new Set([...expected.keys(),...actual.keys()]);
  for(const code of mismatch)
    if (expected.get(code)!==actual.get(code))
      differences.push('OWNER_SCRIPT_OPCODE_AGGREGATE_CHANGED');
  for (const [left,right,rows] of REPEATED) {
    if (!report.repeated_script_comparisons.some(pair=>
        pair.script_id_a === left && pair.script_id_b === right &&
        pair.compared_positions === rows &&
        pair.command_code_and_all_params_equal === rows &&
        pair.first_has_same_length === true &&
        pair.same_content_except_record_and_script_ids === true))
      differences.push('OWNER_REPEAT_PAIR_NOT_IDENTICAL');
  }
  if (report.data_values_emitted !== false ||
      report.original_import_authorized !== false)
    differences.push('UNSAFE_SCRIPT_OUTPUT_OR_IMPORT');
  return differences.length
    ? {status:'DEVIATES_FROM_CAPTURED_OWNER_SCRIPTS_NO_IMPORT',differences:[...new Set(differences)]}
    : {status:'MATCHES_OWNER_SCRIPTS_METADATA_ONLY_NOT_PLAYBACK',differences:[],
       tested_nonduplicate_rows:UNIQUE_ROWS,
       original_import_authorized:false,can_execute:false};
}
module.exports = {loadEvidence,assertEvidence,classifyOriginalOpcode,verifySixScriptStats};
if (require.main === module) {
  const source = loadEvidence();
  assertEvidence(source);
  console.log(JSON.stringify({
    status:'ORIGINAL_OPCODE_REGISTRY_VALIDATED_ALL_HANDLERS_UNMAPPED',
    observed_numeric_codes:source.observed_opcodes.length,
    original_handler_class_names:source.original_native_handler_class_names.length,
    can_execute:false,reference_md5_authenticated:false
  }));
}
