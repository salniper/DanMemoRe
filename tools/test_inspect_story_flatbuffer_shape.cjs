'use strict';
const assert=require('node:assert/strict');
const {inspectRootVector}=require('./inspect_story_flatbuffer_shape.cjs');
function fixture(){
  const b=Buffer.alloc(128);
  b.writeUInt32LE(20,0); // root table
  b.writeUInt16LE(6,12);b.writeUInt16LE(8,14);b.writeUInt16LE(4,16);
  b.writeInt32LE(8,20);b.writeUInt32LE(8,24);
  b.writeUInt32LE(2,32);b.writeUInt32LE(28,36);b.writeUInt32LE(48,40);
  for(const [vt,table] of [[56,64],[80,88]]){
    b.writeUInt16LE(6,vt);b.writeUInt16LE(8,vt+2);
    b.writeUInt16LE(4,vt+4);b.writeInt32LE(8,table);
  }
  return b;
}
const good=inspectRootVector(fixture());
assert.equal(good.status,'FLATBUFFERS_ROOT_VECTOR_NESTED_TABLES_CONSISTENT');
assert.equal(good.row_count,2);
assert.equal(good.checked_nested_tables,2);
assert.equal(Object.hasOwn(good,'plaintext'),false);
assert.equal(inspectRootVector(Buffer.alloc(0)).status,'NOT_STRUCTURALLY_PROVEN');
{
 const invalid=fixture();invalid.writeUInt32LE(0xffffffff,0);
 assert.equal(inspectRootVector(invalid).status,'NOT_STRUCTURALLY_PROVEN');
}
{
 const invalid=fixture();invalid.writeUInt32LE(200001,32);
 assert.equal(inspectRootVector(invalid).status,'NOT_STRUCTURALLY_PROVEN');
}
{
 const invalid=fixture();invalid.writeUInt32LE(0xffffffff,36);
 assert.equal(inspectRootVector(invalid).status,'NOT_STRUCTURALLY_PROVEN');
}
{
 const invalid=fixture();invalid.writeUInt16LE(5,56);
 assert.equal(inspectRootVector(invalid).status,'NOT_STRUCTURALLY_PROVEN');
}
{
 const invalid=fixture();invalid.writeUInt16LE(9,58);
 assert.equal(inspectRootVector(invalid).status,'NOT_STRUCTURALLY_PROVEN');
}
console.log('Synthetic FlatBuffers root/vector/table structure: 7 assertions PASS');
