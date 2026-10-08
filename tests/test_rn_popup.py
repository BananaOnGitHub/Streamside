"""Behavior checks for owned RN UI, without executing Twitch JS."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

class RNPopupTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node required for RN mocks')
    def test_provider_routing_and_sheet_handoff(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const calls=[],hooks=[];
const React={createElement:(type,props,...children)=>({type,props,children}),
 useRef:value=>{hooks.push('ref');return {current:value};}};
const RN={View:'view',Text:'text',Image:'image',Pressable:'button'};
const native={getMetadata:id=>id==='provider'?{id:900000000000001,name:'wide',url:'https://cdn.7tv.app/test.gif',
 subtitle:'7TV channel emote',aspect:3,title:'Copy name',label:'Copy image URL',openURL:'Open in browser',closeLabel:'Close'}:null,
 sendAction:(...args)=>calls.push(['action',...args])};
const sheets={BottomSheet:'sheet',useSheetHandoff:options=>{
 hooks.push('sheet');return {visible:true,onClose:()=>calls.push(['close']),
 onClosed:()=>{calls.push(['closed']);options.onPlainClose();}};}};
const theme={useTheme:()=>{hooks.push('theme');return {colors:{backgroundBase:'black',textBase:'white',textAlt:'gray'}};}};
sheets.useTheme=theme.useTheme;
const modules={72:React,5:RN,2118:sheets,16:{default:{buildLocalEcho:native}}};
const context={__r:id=>modules[id],Math};vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
const original=()=>{};const wrapper=context.install(original);
assert.notStrictEqual(wrapper,original);
modules[72]={default:React};assert.notStrictEqual(context.install(original),original);modules[72]=React;
let nativeProps={emoteID:'123',onClose:()=>calls.push(['host-close'])};
let card=wrapper(nativeProps);assert.strictEqual(card.type,original);assert.strictEqual(card.props,nativeProps);assert.strictEqual(hooks.length,0);
const lookup=native.getMetadata;native.getMetadata=()=>{throw Error('interop unavailable');};
assert.strictEqual(wrapper(nativeProps).type,original);native.getMetadata=lookup;
for(let action=0;action<3;action++){
 calls.length=0;hooks.length=0;
 card=wrapper({emoteID:'provider',onClose:nativeProps.onClose});assert.strictEqual(hooks.length,0);
 const sheet=card.type(card.props);assert.strictEqual(sheet.type,'sheet');
 assert.strictEqual(hooks.join(','),'theme,sheet,ref');
 const content=sheet.children[0];const image=content.children[0];
 assert.strictEqual(image.type,'image');assert.strictEqual(image.props.source.uri,'https://cdn.7tv.app/test.gif');
 assert.strictEqual(image.props.style.width,280);assert.strictEqual(image.props.style.height,112);assert.strictEqual(image.props.resizeMode,'contain');
 content.children[3+action].props.onPress();assert.strictEqual(calls[0][0],'close');assert.strictEqual(calls.length,1);
 sheet.props.onClosed();assert.deepStrictEqual(calls,[['close'],['closed'],['host-close'],['action',900000000000001,action]]);
 sheet.props.onClosed();assert.strictEqual(calls.filter(x=>x[0]==='action').length,1);
}
calls.length=0;card=wrapper({emoteID:'provider',onClose:nativeProps.onClose});
let sheet=card.type(card.props);sheet.props.onClose();sheet.props.onClosed();assert(!calls.some(x=>x[0]==='action'));
native.getMetadata=null;assert.strictEqual(context.install(original),original);
'''
        subprocess.run(['node','-e',script,str(ROOT/'src/rn/ProviderEmoteInfo.js')],check=True,capture_output=True,text=True)

if __name__=='__main__':unittest.main()
