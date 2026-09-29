import assert from 'node:assert/strict';
import {Buffer} from 'node:buffer';
import {pathToFileURL} from 'node:url';
import {webcrypto} from 'node:crypto';
import {existsSync} from 'node:fs';
const path = new URL('../ui/browser_identity.mjs', import.meta.url);
assert.ok(existsSync(path), 'Browser identity must survive reload independently of display names');
const {default: render} = await import(path);
globalThis.crypto = webcrypto;
let stored = null;
globalThis.localStorage = {getItem:()=>stored, setItem:(_key,value)=>{stored=value;}};
let first;
render({data:{},setStateValue:(_key,value)=>{first=value;}});
assert.equal(first.persisted, true);
assert.match(first.token, /^[A-Za-z0-9_-]{43}$/);
assert.equal(Buffer.from(first.token, 'base64url').length, 32);
assert.equal(Buffer.from(first.token, 'base64url').toString('base64url'), first.token);
let second;
render({data:{},setStateValue:(_key,value)=>{second=value;}});
assert.equal(second.token, first.token, 'Reload must recover the same owner');
let sent = false;
render({data:{identity:first},setStateValue:()=>{sent=true;}});
assert.equal(sent,false,'Rerenders must not loop');

const invalidCanonicalToken = `${'A'.repeat(42)}B`;
let repairedStorage = invalidCanonicalToken;
globalThis.localStorage = {
  getItem:()=>repairedStorage,
  setItem:(_key,value)=>{repairedStorage=value;},
};
let repaired;
render({data:{},setStateValue:(_key,value)=>{repaired=value;}});
assert.notEqual(repaired.token, invalidCanonicalToken,
  'Stored tokens with nonzero unused base64 bits must be replaced');
assert.equal(Buffer.from(repaired.token, 'base64url').length, 32);
assert.equal(Buffer.from(repaired.token, 'base64url').toString('base64url'), repaired.token,
  'A 32-byte base64url token must have canonical final bits');
assert.equal(repairedStorage, repaired.token);

const competingToken = `${'B'.repeat(42)}A`;
let racedStorage = null;
globalThis.localStorage = {
  getItem:()=>racedStorage,
  setItem:(_key)=>{racedStorage=competingToken;},
};
let raced;
render({data:{},setStateValue:(_key,value)=>{raced=value;}});
assert.equal(raced.token, competingToken,
  'The component must adopt the canonical value found on storage readback');
assert.equal(raced.persisted, true);

globalThis.localStorage = {getItem:()=>null, setItem:()=>{}};
let unpersisted;
render({data:{},setStateValue:(_key,value)=>{unpersisted=value;}});
assert.equal(unpersisted.persisted, false,
  'A successful setItem call without a stored readback is not persistence');

globalThis.localStorage = {getItem:()=>{throw Error('blocked');}};
let temporary;
render({data:{},setStateValue:(_key,value)=>{temporary=value;}});
assert.equal(temporary.persisted,false);
assert.notEqual(temporary.token,first.token);
console.log('Browser identity canonical-token, storage readback, reload and blocked-storage tests: PASS');

// New tabs must initialize inside the same cross-tab lock, not before it.
const navigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
const grants = [];
Object.defineProperty(globalThis, 'navigator', {configurable:true, value:{locks:{
  request:(_name, callback)=>new Promise(resolve=>grants.push(()=>resolve(callback()))),
}}});
let sharedStorage = null;
globalThis.localStorage = {getItem:()=>sharedStorage,setItem:(_key,value)=>{sharedStorage=value;}};
let tabA, tabB;
render({data:{},setStateValue:(_key,value)=>{tabA=value;}});
render({data:{},setStateValue:(_key,value)=>{tabB=value;}});
assert.ok(tabA === undefined, 'A new owner must not be published before its cross-tab lock is granted');
assert.equal(tabB, undefined);
for (const grant of grants) grant();
await Promise.resolve();
assert.equal(tabA.token, tabB.token, 'Serialized initial tabs must choose the same stored owner');
if (navigatorDescriptor) Object.defineProperty(globalThis,'navigator',navigatorDescriptor);
else delete globalThis.navigator;
console.log('Cross-tab locked initialization: PASS');
