"""Owned provider strip behavior; no Twitch JS or device execution implied."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

class RNStripTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node required for RN mocks')
    def test_modes_scope_selection_live_settings_and_plain_text_insertion(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let active=[],cursor=0,effects=[],context=null,timer=null,config={mode:0,revision:1,enabled:1},queries=[],edits=[];
const slots=new Map(),inputCalls=[];
const React={createElement:(type,props,...children)=>({type,props,children}),createContext:()=>({Provider:'provider'}),
 useContext:()=>context,useRef:value=>{let i=cursor++;return active[i]||(active[i]={current:value});},
 useState:value=>{let i=cursor++;if(!(i in active))active[i]=typeof value==='function'?value():value;
  const scope=active;return [active[i],next=>{scope[i]=typeof next==='function'?next(scope[i]):next;}];},
 useMemo:fn=>{cursor++;return fn();},useEffect:(fn,deps)=>{let i=cursor++,old=active[i];
  if(!old||deps.some((x,j)=>x!==old.deps[j])){if(old&&old.cleanup)old.cleanup();active[i]={deps};effects.push(()=>{active[i].cleanup=fn();});}}};
const item={id:900000000000001,name:'WideEmote',url:'https://cdn.7tv.app/fixture.gif',aspect:3};
let catalog=[item];
const bridge={getState:()=>config,search:(room,query)=>{queries.push([room,query]);return room==='42'?catalog:[];}};
const inputs={EmoteTextInput:'native-input'};
const buttons={IconButton:'native-button'},trays={EmotePickerTray:'native-tray'},suggestions={ChatAutocompleteTray:'native-suggestions'},hookCalls=[];
let nativeResult={matches:null}, confirmed=0;
const RN={View:'view',Text:'text',Image:'image',Pressable:'button',ScrollView:'scroll'};
const ui={useTheme:()=>({colors:{backgroundBase:'black',textAlt:'white'}})};
const autocomplete={EMOTE_URL_TEMPLATE:'https://fixture/{id}/default',EMOTE_URL_TEMPLATE_STATIC:'https://fixture/{id}/static',caretFromEdit:(before,after)=>{let suffix=0;while(suffix<Math.min(before.length,after.length)&&before[before.length-suffix-1]===after[after.length-suffix-1])suffix++;return after.length-suffix;}};
autocomplete.useAutocomplete=(...args)=>{hookCalls.push(args);return nativeResult;};
const env={__r:id=>({72:React,5:RN,2118:ui,16:{default:{buildLocalEcho:bridge}},3759:inputs,4619:autocomplete,3337:buttons,4174:trays,4713:suggestions})[id],encodeURIComponent,WeakMap,
 setInterval:fn=>{timer=fn;return 1;},clearInterval:()=>{timer=null;}};
vm.createContext(env);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),env);
const Original='composer',Composer=env.install(Original),Input=inputs.EmoteTextInput;
let p={channelID:'42',draft:'Wi',inputFocused:true,canSend:true,remaining:498,onDraftChange:text=>{edits.push(text);p={...p,draft:text};}};
function render(fn,props){active=slots.get(fn)||[];slots.set(fn,active);cursor=0;effects=[];
 const out=fn(props);for(const e of effects)e();return out;}
function composer(){let out=render(Composer,p);context=out.props.value;assert.strictEqual(out.children[0].children[1].type,Original);return out.children[0].children[0];}
function input(value=p.draft){return render(Input,{value,ref:'preserved',onSelectionChange:e=>inputCalls.push(e),onChangeText:t=>inputCalls.push(t)});}
function select(start,end=start){let event={nativeEvent:{selection:{start,end}}};input().props.onSelectionChange(event);assert.strictEqual(inputCalls.at(-1),event);return composer();}
function button(strip){return strip&&strip.children[0][0];}
assert.strictEqual(composer(),null);let strip=select(2);assert.strictEqual(strip.type,'scroll');
assert.strictEqual(strip.props.horizontal,true);assert.strictEqual(strip.props.style.height,60);
assert.strictEqual(strip.props.keyboardShouldPersistTaps,'always');
assert.strictEqual(button(strip).children[0].props.style.width,96);assert.strictEqual(button(strip).children[0].props.source.uri,item.url);
assert.strictEqual(input().props.ref,'preserved');button(strip).props.onPress();assert.strictEqual(edits.at(-1),'WideEmote ');
composer();assert.strictEqual(input().props.selection.start,10);select(10);assert.strictEqual(input().props.selection,undefined);
// Automatic threshold, explicit colon, off, settings refresh without a keystroke.
p={...p,draft:'W'};assert.strictEqual(select(1),null);p={...p,draft:':'};assert(select(1));
config={...config,mode:1};timer();composer();p={...p,draft:'Wi'};assert.strictEqual(select(2),null);
p={...p,draft:':Wi'};strip=select(3);assert(strip);const stale=button(strip);
config={...config,mode:2};stale.props.onPress();assert.strictEqual(edits.length,1);timer();assert.strictEqual(composer(),null);
config={...config,mode:0};timer();composer();p={...p,draft:'😀 Wi end'};strip=select(5);button(strip).props.onPress();
assert.strictEqual(edits.at(-1),'😀 WideEmote end');composer();assert.strictEqual(input().props.selection.start,12);
// No insertion for noncollapsed/inside-word/URL/mention, unknown room, disabled/restricted input.
for(const text of ['http://Wi','@Wi','Wi:bad','/Wi']){p={...p,draft:text};assert.strictEqual(select(text.length),null);}
p={...p,draft:'Wi'};assert.strictEqual(select(1),null);assert.strictEqual(select(0,2),null);
p={...p,channelID:'other'};assert.strictEqual(composer(),null);assert.strictEqual(select(2),null);
p={...p,channelID:'42',canSend:false};assert.strictEqual(select(2),null);p={...p,canSend:true};
config={...config,enabled:0};timer();assert.strictEqual(select(2),null);config={...config,enabled:1};timer();composer();
// Native overlap, stale catalog/selection, remaining character budget, blur, unscoped input fallback.
p={...p,emoteMap:{WideEmote:'native'}};strip=select(2);assert.strictEqual(strip.children[0].length,1);
assert.strictEqual(button(strip).children[0].props.source.uri,'https://fixture/native/default');p={...p,emoteMap:{},remaining:0};
strip=select(2);let count=edits.length;button(strip).props.onPress();assert.strictEqual(edits.length,count);
p={...p,remaining:500};strip=select(2);catalog=[];button(strip).props.onPress();assert.strictEqual(edits.length,count);catalog=[item];
strip=select(2);input().props.onChangeText('Wis');p={...p,draft:'Wis'};composer();button(strip).props.onPress();assert.strictEqual(edits.length,count);
// First typing renders suggestions even if selection arrived first, or no
// post-change selection has arrived yet. New text precedes parent prop updates.
p={...p,draft:'W'};select(1);input().props.onChangeText('Wi');p={...p,draft:'Wi'};assert(composer());
input().props.onChangeText('Wid');select(3);p={...p,draft:'Wid'};assert(composer());
// Native subscriber entries share insertion, current catalog identity, and
// static/animated URL policy. Provider/native code overlap favors native.
p={...p,draft:':Su',emoteMap:{SubEmote:'emotesv2_123',Bad:null},emoteAnimationsEnabled:false};
strip=select(3);let sub=strip.children[0].find(b=>b.props.accessibilityLabel==='SubEmote');assert(sub);
assert.strictEqual(sub.children[0].props.source.uri,'https://fixture/emotesv2_123/static');
sub.props.onPress();assert.strictEqual(edits.at(-1),'SubEmote ');composer();
p={...p,draft:'Su'};strip=select(2);sub=strip.children[0].find(b=>b.props.accessibilityLabel==='SubEmote');
p={...p,emoteMap:{SubEmote:'changed'}};composer();count=edits.length;sub.props.onPress();assert.strictEqual(edits.length,count);
// The emote button/library exports are untouched in every mode.
assert.strictEqual(buttons.IconButton,'native-button');assert.strictEqual(trays.EmotePickerTray,'native-tray');
input().props.onBlur();assert.strictEqual(composer(),null);assert.strictEqual(timer,null);
context=null;const props={value:'test',ref:'x'};assert.strictEqual(render(Input,props).props,props);
assert(queries.every(q=>q[0]==='42'||q[0]==='other'));
// Takeover filters the native emote provider BEFORE native send callbacks are
// constructed. Command/mention provider identities and original props survive.
const emote={autocompleteType:'emote'},command={autocompleteType:'command'},mention={autocompleteType:'mention'};
const providers=[emote,command,mention],setter=()=>{},complete=()=>{};
const beforeCursor=cursor;
assert.strictEqual(autocomplete.useAutocomplete(':Su',setter,providers,complete),nativeResult);
assert.strictEqual(cursor,beforeCursor,'adapter must not add hooks to an already mounted parent');
assert.deepStrictEqual(Array.from(hookCalls.at(-1)[2]),[command,mention]);
assert.strictEqual(hookCalls.at(-1)[1],setter);assert.strictEqual(hookCalls.at(-1)[3],complete);
const filtered=hookCalls.at(-1)[2];autocomplete.useAutocomplete(':Su',setter,providers,complete);
assert.strictEqual(hookCalls.at(-1)[2],filtered,'stable provider identity across renders');
nativeResult={matches:[{type:'emote'}],confirmHighlightedMatch:()=>{confirmed++;return nativeResult.matches[0];},onChange:()=>{}};
const masked=autocomplete.useAutocomplete(':Su',setter,providers,complete);
assert.strictEqual(masked.matches,null);assert.strictEqual(masked.confirmHighlightedMatch(),null);assert.strictEqual(confirmed,0);
assert.strictEqual(masked.onChange,nativeResult.onChange);
// This mirrors the donor composer's send branch: null matches send ordinary text.
let sends=0;if(masked.matches===null)sends++;else masked.confirmHighlightedMatch();assert.strictEqual(sends,1);
const matchProps={matches:nativeResult.matches};assert.strictEqual(render(suggestions.ChatAutocompleteTray,matchProps),null);
nativeResult={matches:[{type:'mention'}]};assert.strictEqual(autocomplete.useAutocomplete('@test',setter,providers,complete),nativeResult);
assert.strictEqual(render(suggestions.ChatAutocompleteTray,{matches:nativeResult.matches}).type,'native-suggestions');
config={...config,mode:2};timer();
// Run each component's own refresh callback to model a live settings change.
slots.delete(suggestions.ChatAutocompleteTray);assert.strictEqual(render(suggestions.ChatAutocompleteTray,matchProps).props,matchProps);
assert.strictEqual(autocomplete.useAutocomplete(':Su',setter,providers,complete),nativeResult);assert.strictEqual(hookCalls.at(-1)[2],providers);
config={...config,mode:0,enabled:0};slots.delete(suggestions.ChatAutocompleteTray);
assert.strictEqual(autocomplete.useAutocomplete(':Su',setter,providers,complete),nativeResult);assert.strictEqual(hookCalls.at(-1)[2],providers);
assert.strictEqual(trays.EmotePickerTray,'native-tray');assert.strictEqual(render(suggestions.ChatAutocompleteTray,matchProps).props,matchProps);
composer();assert.strictEqual(buttons.IconButton,'native-button');
'''
        ran=subprocess.run(['node','-e',script,str(ROOT/'src/rn/ProviderEmoteStrip.js')],capture_output=True,text=True)
        self.assertEqual(ran.returncode,0,ran.stderr)
