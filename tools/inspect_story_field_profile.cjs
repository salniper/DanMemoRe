'use strict';
// Read-only field-shape profiling of *already authenticated and decrypted*
// original novel-command FlatBuffers. This never emits decoded values,
// original strings, decrypted bytes, executable instructions or secret keys.
// A structural profile does NOT assert a publisher schema or script semantics.
const { decodeBlock, rows } = require('./decode_master_data.cjs');
const { inspectRootVector } = require('./inspect_story_flatbuffer_shape.cjs');

const MAX_ROWS = 4096;
const MAX_SLOTS = 96;
const MAX_TOTAL_FIELDS = 120000;
const MAX_TEXT_BLOCK = 65536;
const MAX_PLAIN = 64 * 1024 * 1024;

function inside(blob, start, count) {
  return Number.isSafeInteger(start) && Number.isSafeInteger(count) &&
    start >= 0 && count >= 0 && start <= blob.length &&
    count <= blob.length - start;
}

function tableLayout(blob, at) {
  if (!inside(blob, at, 4)) throw Error('Invalid FlatBuffers table offset');
  const back = blob.readInt32LE(at);
  const vtable = at - back;
  if (!inside(blob, vtable, 4)) throw Error('Invalid FlatBuffers vtable pointer');
  const vbytes = blob.readUInt16LE(vtable);
  const obytes = blob.readUInt16LE(vtable + 2);
  if (vbytes < 4 || vbytes % 2 || vbytes > 4 + MAX_SLOTS * 2 ||
      obytes < 4 || !inside(blob, vtable, vbytes) ||
      !inside(blob, at, obytes))
    throw Error('Invalid FlatBuffers table dimensions');
  const fields = [];
  for (let n = 0; n < (vbytes - 4) / 2; n++) {
    const field = blob.readUInt16LE(vtable + 4 + n * 2);
    if (field && (field < 4 || field >= obytes))
      throw Error('Invalid FlatBuffers field offset');
    fields.push(field);
  }
  return { obytes, fields };
}

function candidateText(blob, fieldAt, limit, key) {
  if (limit < 4 || !inside(blob, fieldAt, 4)) return false;
  const rel = blob.readUInt32LE(fieldAt);
  if (rel < 4 || rel > blob.length - fieldAt - 4) return false;
  const at = fieldAt + rel;
  if (!inside(blob, at, 4)) return false;
  const length = blob.readUInt32LE(at);
  if (length < 8 || length > MAX_TEXT_BLOCK || length % 4 ||
      !inside(blob, at + 4, length)) return false;
  try {
    const value = decodeBlock(blob.subarray(at + 4, at + 4 + length), key);
    // The client's string values can carry trailing C NUL, but are not
    // necessarily intended as display strings. Validate UTF-8 only.
    new TextDecoder('utf-8', { fatal: true }).decode(value);
    return true;
  } catch (_) { return false; }
}

function candidateScalar(blob, fieldAt, limit, key) {
  const possibilities = [];
  for (const width of [8, 12]) {
    if (limit < width || !inside(blob, fieldAt, width)) continue;
    try {
      const plain = decodeBlock(blob.subarray(fieldAt, fieldAt + width), key);
      if (width === 8 && plain.length === 1) possibilities.push('BYTE_OR_BOOL');
      if (width === 8 && plain.length === 4) possibilities.push('INT32_OR_FLOAT');
      if (width === 12 && plain.length === 8) possibilities.push('INT64');
    } catch (_) { /* No evidence for this width. */ }
  }
  return possibilities;
}

function classifyField(blob, at, room, key) {
  const text = candidateText(blob, at, room, key);
  const numbers = candidateScalar(blob, at, room, key);
  if (text && numbers.length) return 'AMBIGUOUS_TEXT_OR_' + numbers.join('_');
  if (text) return 'UTF8_STRING_CANDIDATE';
  if (numbers.length > 1) return 'AMBIGUOUS_NUMERIC_WIDTH';
  if (numbers.length) return numbers[0];
  return 'UNCLASSIFIED_ENCODING';
}

function profileStoryFields(blob, numericKey) {
  if (!Buffer.isBuffer(blob) || blob.length > MAX_PLAIN ||
      !Buffer.isBuffer(numericKey) || numericKey.length !== 16)
    throw Error('Invalid bounded story profiling input');
  const shape = inspectRootVector(blob);
  if (shape.status !== 'FLATBUFFERS_ROOT_VECTOR_NESTED_TABLES_CONSISTENT')
    return { status: 'STRUCTURE_INVALID_NO_FIELD_PROFILE' };
  if (shape.row_count > MAX_ROWS)
    return { status: 'ROW_CAP_EXCEEDED_NO_FIELD_PROFILE' };
  const items = rows(blob);
  if (items.length !== shape.row_count) throw Error('Inconsistent story row counts');
  const slots = new Map();
  let total = 0;
  let maxVtableSlots = 0;
  for (const row of items) {
    const layout = tableLayout(blob, row);
    maxVtableSlots = Math.max(maxVtableSlots, layout.fields.length);
    const ordered = layout.fields.filter(Boolean).sort((a, b) => a - b);
    for (let index = 0; index < layout.fields.length; index++) {
      const position = layout.fields[index];
      if (!position) continue;
      total++;
      if (total > MAX_TOTAL_FIELDS)
        return { status: 'FIELD_CAP_EXCEEDED_NO_FIELD_PROFILE' };
      const larger = ordered.find(x => x > position);
      const room = (larger === undefined ? layout.obytes : larger) - position;
      const kind = classifyField(blob, row + position, room, numericKey);
      if (!slots.has(index)) slots.set(index, { field_index: index, present_rows: 0, candidate_kinds: {} });
      const stats = slots.get(index);
      stats.present_rows++;
      stats.candidate_kinds[kind] = (stats.candidate_kinds[kind] || 0) + 1;
    }
  }
  return {
    status: 'STRUCTURAL_FIELD_CANDIDATES_ONLY_NOT_SCHEMA',
    row_count: items.length,
    max_vtable_slots: maxVtableSlots,
    total_present_fields: total,
    slots: [...slots.values()].sort((a, b) => a.field_index - b.field_index),
    data_values_emitted: false,
    import_authorized: false,
    limitations: 'No decoded field values or semantic names. INT32_OR_FLOAT, BYTE_OR_BOOL and UTF8 are candidates only; no publisher command schema, order semantics, playback or reference-MD5 proof.'
  };
}

module.exports = { profileStoryFields, tableLayout, classifyField, candidateText, candidateScalar };
