"""Library deletion reuses Twitch's pure helper and functional draft setter."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class RNBackspaceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node required for RN mocks')
    def test_scoped_codes_native_aliases_unicode_and_queued_edits(self):
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let config={enabled:1,mode:0},queue=[],draft='',lookups=[],hookCalls=0,helperCalls=0;
const React={createContext:()=>({}),useContext:()=>null,createElement:()=>null};
const RN={ScrollView:1,Pressable:2},ui={useTheme:()=>null};
const native={setDraft:fn=>queue.push(fn),backspaceDraft:()=>{throw Error('Unexpected native callback');},cheermoteTokenImages:Object.freeze({Cheer100:1})};
const hooks={useChatComposer:p=>{hookCalls++;return native;}},original=hooks.useChatComposer;
// Same observed smartBackspace contract: text, caret, recognition predicate.
// The imported donor helper itself is preserved byte-for-byte by the verifier.
function smart(text,caret,predicate){
 helperCalls++;assert.equal(caret,text.length);
 let end=caret,start=end;while(start>0&&!/\s/.test(text[start-1]))start--;
 if(text[end-1]===' '){end--;start=end;while(start>0&&!/\s/.test(text[start-1]))start--;}
 if(start!==end&&predicate(text.slice(start,end)))return {value:text.slice(0,start),caret:start};
 return {value:Array.from(text).slice(0,-1).join(''),caret:caret-1};
}
const bridge={getState:()=>config,search:()=>[],lookup:(room,code)=>{lookups.push([room,code]);return config.enabled&&room==='42'&&['Wide','om'].includes(code)?{name:code}:null;}};
const modules={72:React,5:RN,2118:ui,16:{default:{buildLocalEcho:bridge}},3759:{EmoteTextInput:1},
 4619:{useAutocomplete:()=>null,caretFromEdit:()=>0,EMOTE_URL_TEMPLATE:'a',EMOTE_URL_TEMPLATE_STATIC:'b'},
 4713:{ChatAutocompleteTray:1},4174:{},245:{},4687:hooks,3758:{smartBackspace:smart},3382:{emoteTokenAliases:token=>[token,':'+token+':']}};
const env={__r:id=>modules[id],WeakMap};vm.createContext(env);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),env);env.install('composer');
assert.notStrictEqual(hooks.useChatComposer,original);
const p=Object.freeze({channelID:'42',emoteTokenMap:Object.freeze({Kappa:1}),emoteSuggestions:Object.freeze([{token:'Smile'}])});
const result=hooks.useChatComposer(p);assert.equal(hookCalls,1);assert.strictEqual(result.setDraft,native.setDraft);
function flush(){while(queue.length)draft=queue.shift()(draft);}
for(const text of ['Wide','Wide ','hello Wide','hello Wide ']){draft=text;result.backspaceDraft();assert.equal(typeof queue[0],'function');flush();assert.equal(draft,text.startsWith('hello')?'hello ':'');}
for(const text of ['Kappa ','Cheer100 ',':Smile: ']){draft=text;result.backspaceDraft();flush();assert.equal(draft,'');}
// Batched taps operate on the latest draft, not the render's captured string.
draft='Wide om ';result.backspaceDraft();result.backspaceDraft();flush();assert.equal(draft,'');
draft='wide';result.backspaceDraft();flush();assert.equal(draft,'wid'); // Case-sensitive exact match.
draft='hello';result.backspaceDraft();flush();assert.equal(draft,'hell');
draft='hi😀';result.backspaceDraft();flush();assert.equal(draft,'hi');
config={enabled:1,mode:2};draft='om ';hooks.useChatComposer(p).backspaceDraft();flush();assert.equal(draft,'');
const unknown=hooks.useChatComposer({...p,channelID:'unknown'});draft='Wide';unknown.backspaceDraft();flush();assert.equal(draft,'Wid');
// Settings/catalog changes are checked when an updater executes.
draft='Wide';result.backspaceDraft();config={enabled:0,mode:2};flush();assert.equal(draft,'Wid');
assert.strictEqual(hooks.useChatComposer(p),native);
assert(helperCalls>10);assert(lookups.every(([room])=>room==='42'||room==='unknown'));
assert.deepEqual(Object.keys(p.emoteTokenMap),['Kappa']);assert.deepEqual(Object.keys(native.cheermoteTokenImages),['Cheer100']);
'''
        ran = subprocess.run(['node', '-e', script, str(ROOT / 'src/rn/ProviderEmoteStrip.js')], capture_output=True, text=True)
        self.assertEqual(ran.returncode, 0, ran.stderr)
