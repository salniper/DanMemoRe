#!/usr/bin/env node
'use strict';
// Read-only, fail-closed diagnostic. Never authorizes legacy import or writes game data.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { nativeMasterConfig, decodeFile } = require('./decode_master_data.cjs');
const { inspectRootVector } = require('./inspect_story_flatbuffer_shape.cjs');

const IDS = ['751040548','751040550','751040806','751040815','751041273','751041275'];
const PREFIX = '1/master/divide_novel_command_enc/';
const MAX_STORY_BYTES = 16 * 1024 * 1024; // hard bound for forensic input, not a game format assertion
const sha256 = b => crypto.createHash('sha256').update(b).digest('hex');
const md5 = b => crypto.createHash('md5').update(b).digest('hex');
const hex = (v, n) => typeof v === 'string' && new RegExp('^[a-f0-9]{'+n+'}$').test(v);
function checkPath(root, relative) {
  const base = fs.realpathSync(root);
  let at = base;
  for (const item of relative.split('/')) {
    if (item === '' || item === '.' || item === '..') throw Error('unsafe path');
    at = path.join(at, item);
    if (fs.lstatSync(at).isSymbolicLink()) throw Error('symlink refused: ' + relative);
  }
  const target = fs.realpathSync(at);
  if (!target.startsWith(base + path.sep)) throw Error('path escapes contents');
  if (!fs.statSync(target).isFile()) throw Error('not a file: ' + relative);
  return target;
}
function inspect(audit, contents, image) {
  if (!audit || !Array.isArray(audit.issues)) throw Error('invalid audit');
  const entries = audit.issues.filter(x => x.status === 'unverified_bytes' && x.path.startsWith(PREFIX));
  if (entries.length !== IDS.length) throw Error('expected exactly six story command mismatches');
  const seen = new Set();
  const config = image ? nativeMasterConfig(image) : null; // SHA-256-pinned original 15.1.0 binary only
  const results = entries.map(entry => {
    const name = entry.path.slice(PREFIX.length);
    if (!IDS.some(id => name === 'novelCommand' + id + '.enc') || seen.has(name))
      throw Error('unexpected or duplicate story command: ' + name);
    seen.add(name);
    const keys = ['actual_md5','reference_md5','historical_md5'];
    if (keys.some(k => !hex(entry[k],32)) ||
        entry.reference_md5 !== entry.historical_md5 ||
        entry.actual_md5 === entry.reference_md5 ||
        !Number.isSafeInteger(entry.actual_size) || entry.actual_size <= 0 ||
        entry.actual_size > MAX_STORY_BYTES ||
        entry.reference_size !== entry.actual_size || entry.historical_size !== entry.actual_size)
      throw Error('invalid audit fingerprints: ' + name);
    const source = checkPath(contents, entry.path);
    if (fs.statSync(source).size > MAX_STORY_BYTES) throw Error('story file exceeds diagnostic limit: ' + name);
    const data = fs.readFileSync(source);
    const stable = data.length === entry.actual_size && md5(data) === entry.actual_md5;
    const row = { path: entry.path, sha256: sha256(data),
      audit_recheck: stable ? 'MATCH' : 'CHANGED_SINCE_AUDIT',
      reference_md5_match: md5(data) === entry.reference_md5,
      aes_block_aligned: data.length > 0 && data.length % 16 === 0,
      decode_probe: 'NOT_RUN', verdict: 'UNVERIFIED_DO_NOT_IMPORT' };
    if (config && stable && row.aes_block_aligned) {
      try {
        const plain = decodeFile(data, config.key, config.iv);
        row.decode_probe = 'AES_CBC_ZLIB_INFLATE_SUCCEEDED';
        row.plaintext_length = plain.length;
        row.plaintext_sha256 = sha256(plain); // no plaintext exported or logged
        row.structure_probe = inspectRootVector(plain);
      } catch (_) {
        row.decode_probe = 'AES_CBC_ZLIB_INFLATE_FAILED';
      }
    } else if (config) row.decode_probe = 'SKIPPED_UNSTABLE_OR_UNALIGNED';
    return row;
  });
  if (seen.size !== IDS.length) throw Error('incomplete story command set');
  return { verdict: 'DO_NOT_IMPORT_UNVERIFIED_BYTES', file_count: results.length,
    decoder_scope: 'Master AES-CBC/zlib and generic FlatBuffers root vector only; success is NOT original novel schema or runtime proof',
    results };
}
function main(args) {
  if ((args.length !== 4 && args.length !== 6) ||
      args[0] !== '--audit' || args[2] !== '--contents' ||
      (args.length === 6 && args[4] !== '--native-binary'))
    throw Error('Usage: node inspect_story_command_compat.cjs --audit AUDIT.json --contents CONTENTS [--native-binary ORIGINAL_15_1_0_ARM64_SO]');
  const report = inspect(JSON.parse(fs.readFileSync(args[1], 'utf8')), args[3],
                         args.length === 6 ? args[5] : null);
  process.stdout.write(JSON.stringify(report, null, 2) + '\n');
}
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (err) { process.stderr.write('Diagnostic failed: ' + err.message + '\n'); process.exitCode = 1; }
}
module.exports = { inspect, IDS };
