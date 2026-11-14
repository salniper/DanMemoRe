'use strict';
// Structural read-only FlatBuffers probe. No string values or original bytes exported.
// Valid nested tables are evidence of consistent encoding, NOT gameplay semantics.
const MAX_ROWS = 200000;
const MAX_PLAIN_BYTES = 64 * 1024 * 1024;
function inspectRootVector(plain) {
  if (!Buffer.isBuffer(plain) || plain.length < 12 ||
      plain.length > MAX_PLAIN_BYTES)
    return {status:'NOT_STRUCTURALLY_PROVEN'};
  const ok = (off, n) => Number.isSafeInteger(off) && off >= 0 && n >= 0 &&
    off + n <= plain.length;
  const vectorTable = (table) => {
    if (!ok(table,4)) return false;
    const rel=plain.readInt32LE(table);
    const vt=table-rel;
    if (!ok(vt,4)) return false;
    const vtBytes=plain.readUInt16LE(vt);
    const objBytes=plain.readUInt16LE(vt+2);
    if (!Number.isSafeInteger(vtBytes) || vtBytes < 4 ||
        vtBytes > 2048 || vtBytes%2 || !ok(vt,vtBytes) ||
        objBytes < 4 || objBytes > 65535 || !ok(table,objBytes))
      return false;
    for(let i=vt+4;i<vt+vtBytes;i+=2){
      const field=plain.readUInt16LE(i);
      if (field!==0 && (field<4 || field>=objBytes)) return false;
    }
    return {vt,objBytes,vtBytes};
  };
  const root=plain.readUInt32LE(0);
  if (!ok(root,4) || root<4) return {status:'NOT_STRUCTURALLY_PROVEN'};
  const structure=vectorTable(root);
  if (!structure || structure.vtBytes<6) return {status:'NOT_STRUCTURALLY_PROVEN'};
  const fieldOff=plain.readUInt16LE(structure.vt+4);
  if (!fieldOff || !ok(root+fieldOff,4)) return {status:'NOT_STRUCTURALLY_PROVEN'};
  const fieldAt=root+fieldOff;
  const vector=fieldAt+plain.readUInt32LE(fieldAt);
  if (!ok(vector,4)) return {status:'NOT_STRUCTURALLY_PROVEN'};
  const count=plain.readUInt32LE(vector);
  if(count>MAX_ROWS || !ok(vector+4,count*4))
    return {status:'NOT_STRUCTURALLY_PROVEN'};
  for(let i=0;i<count;i++){
    const ptrAt=vector+4+i*4;
    const table=ptrAt+plain.readUInt32LE(ptrAt);
    if(!vectorTable(table)) return {status:'NOT_STRUCTURALLY_PROVEN'};
  }
  return {status:'FLATBUFFERS_ROOT_VECTOR_NESTED_TABLES_CONSISTENT',
          row_count:count, checked_nested_tables:count,
          disclaimer:'Structural compatibility only. No original story schema or runtime validation.'};
}
module.exports={inspectRootVector};
