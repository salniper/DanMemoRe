'use strict';
// Synthetic FlatBuffers only. This fixture never includes an original asset,
// playable script, user dialogue, secret key or original decryption material.
const assert = require('node:assert/strict');
const { encodeBlock } = require('./decode_master_data.cjs');
const { profileStoryFields, classifyField } = require('./inspect_story_field_profile.cjs');

const NUMERIC_KEY = Buffer.alloc(16, 7);

function fixture() {
  const blob = Buffer.alloc(400);
  blob.writeUInt32LE(20, 0);
  blob.writeUInt16LE(6, 12); blob.writeUInt16LE(8, 14);
  blob.writeUInt16LE(4, 16); blob.writeInt32LE(8, 20);
  blob.writeUInt32LE(8, 24);
  blob.writeUInt32LE(2, 32);
  blob.writeUInt32LE(28, 36);
  blob.writeUInt32LE(80, 40);
  for (const [vtable, table] of [[48, 64], [104, 120]]) {
    blob.writeUInt16LE(8, vtable);
    blob.writeUInt16LE(20, vtable + 2);
    blob.writeUInt16LE(4, vtable + 4);
    blob.writeUInt16LE(12, vtable + 6);
    blob.writeInt32LE(16, table);
    const first = Buffer.alloc(4);
    first.writeInt32LE(123, 0);
    encodeBlock(first, NUMERIC_KEY, 8).copy(blob, table + 4);
    const second = Buffer.alloc(4);
    second.writeInt32LE(456, 0);
    encodeBlock(second, NUMERIC_KEY, 8).copy(blob, table + 12);
  }
  return blob;
}

const p = profileStoryFields(fixture(), NUMERIC_KEY);
assert.equal(p.status, 'STRUCTURAL_FIELD_CANDIDATES_ONLY_NOT_SCHEMA');
assert.equal(p.row_count, 2);
assert.equal(p.max_vtable_slots, 2);
assert.equal(p.total_present_fields, 4);
assert.equal(p.slots.length, 2);
assert.deepEqual(p.slots.map(x => x.present_rows), [2, 2]);
assert.equal(p.slots[0].candidate_kinds.INT32_OR_FLOAT, 2);
assert.equal(p.slots[1].candidate_kinds.INT32_OR_FLOAT, 2);
assert.equal(p.data_values_emitted, false);
assert.equal(p.import_authorized, false);
assert(!JSON.stringify(p).includes('123'));
assert(!JSON.stringify(p).includes('456'));

{
  const blob = fixture();
  const string = encodeBlock(Buffer.from('scene\0'), NUMERIC_KEY, 12);
  blob.writeUInt32LE(300 - 132, 132);
  blob.writeUInt32LE(string.length, 300);
  string.copy(blob, 304);
  const result = profileStoryFields(blob, NUMERIC_KEY);
  assert.equal(result.row_count, 2);
  assert.equal(result.slots[1].candidate_kinds.UTF8_STRING_CANDIDATE, 1);
  assert.equal(result.slots[1].candidate_kinds.INT32_OR_FLOAT, 1);
  assert(!JSON.stringify(result).includes('scene'));
}
{
  const bad = fixture();
  bad.writeUInt16LE(3, 104 + 4); // illegal offset less than four
  assert.equal(profileStoryFields(bad, NUMERIC_KEY).status,
               'STRUCTURE_INVALID_NO_FIELD_PROFILE');
}
{
  const bad = fixture();
  bad.writeUInt32LE(200001, 32);
  assert.equal(profileStoryFields(bad, NUMERIC_KEY).status,
               'STRUCTURE_INVALID_NO_FIELD_PROFILE');
}
{
  const bad = fixture();
  bad.writeUInt16LE(0, 104 + 6); // missing second slot in one row
  const result = profileStoryFields(bad, NUMERIC_KEY);
  assert.equal(result.slots[1].present_rows, 1);
}
assert.throws(() => profileStoryFields(fixture(), Buffer.alloc(15)), /Invalid bounded/);
assert.equal(profileStoryFields(Buffer.alloc(0), NUMERIC_KEY).status,
             'STRUCTURE_INVALID_NO_FIELD_PROFILE');
assert.equal(classifyField(fixture(), 390, 2, NUMERIC_KEY), 'UNCLASSIFIED_ENCODING');
console.log('Synthetic novel FlatBuffers field profiling: 19 checks PASS');
