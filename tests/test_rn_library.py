"""Library session, navigation and insertion behavior in an owned RN mock."""
import ast
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class RNLibraryTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node required for RN host facade')
    def test_fractional_columns_and_identity_on_first_open_and_fresh_reopen(self):
        tree=ast.parse(Path(__file__).read_text())
        existing=next(n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
        prefix=existing.split('vm.createContext(env);')[0]
        baseline=json.loads((ROOT/'tests/fixtures/window_baseline.json').read_text())
        exercise=prefix+"vm.createContext(env);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),env);env.install('composer');\n"
        exercise+='const baseline='+json.dumps(baseline)+';\n'+(ROOT/'tests/fixtures/window_geometry.js').read_text()
        result=subprocess.run(['node','-e',exercise,str(ROOT/'src/rn/ProviderEmoteStrip.js')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node required for RN mocks')
    def test_open_snapshot_filters_geometry_navigation_and_fallback(self):
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let context=null,slots=new Map(),active=[],cursor=0,effects=[],timers=[];
const React={createElement:(type,props,...children)=>({type,props:props||{},children}),
 createContext:()=>({Provider:'provider'}),useContext:()=>context,
 cloneElement:(child,p)=>({...child,props:{...child.props,...p}}),Children:{toArray:x=>x||[]},
 useRef:value=>{const i=cursor++;return active[i]||(active[i]={current:value});},
 useState:value=>{const i=cursor++;if(!(i in active))active[i]=typeof value==='function'?value():value;
   const scope=active;return [active[i],x=>scope[i]=typeof x==='function'?x(scope[i]):x];},
 useMemo:(fn,deps)=>{const i=cursor++,old=active[i];if(!old||deps.some((x,j)=>x!==old.deps[j]))active[i]={deps,value:fn()};return active[i].value;},
 useEffect:(fn,deps)=>{const i=cursor++,old=active[i];if(!old||deps.some((x,j)=>x!==old.deps[j])){if(old&&old.cleanup)old.cleanup();const scope=active;scope[i]={deps};effects.push(()=>scope[i].cleanup=fn());}}};
function render(fn,p,key=fn){active=slots.get(key)||[];slots.set(key,active);cursor=0;effects=[];const out=fn(p);effects.forEach(e=>e());return out;}
const RN={View:'view',Text:'text',Image:'image',Pressable:'button',ScrollView:'scroll',SectionList:'grid',FlatList:'flat'};
const theme={colors:{backgroundBase:'black',backgroundAlt:'#222',backgroundAlt2:'#555',textBase:'white',textAlt:'#ccc',textLink:'purple'}};
const a={id:101,name:'First',url:'a.gif',aspect:1,provider:0},b={id:102,name:'Wide',url:'b.gif',aspect:3,provider:1},c={id:103,name:'FF',url:'c.gif',aspect:1,provider:2};
let saved=[a],channel=[a,b,c],global=[b],config={enabled:1,mode:0,revision:1},reads=0,insertions=[],nativeJumps=0,viewEvents=[];
const bridge={getState:()=>config,search:()=>[],getSnapshot:room=>{reads++;if(room!=='42')return null;return {sections:[channel,global],recents:saved.slice(),title:'Third-party emotes',label:'Recent third-party emotes',labels:['All','7TV','BTTV','FFZ','Channel','Global'],icon:'✦',message:'No emotes in this section'};},
 remember:(room,name,id)=>{if(room!=='42'||!config.enabled)return null;const value=channel.concat(global).find(x=>x.name===name);if(!value||value.id!==id)return null;saved=[value,...saved.filter(x=>x.name!==name)].slice(0,40);return value;},getMetadata:()=>null};
const nativeJSX=(type,props,key)=>({type,props,key});const jsx={jsx:nativeJSX,jsxs:nativeJSX};
const trays={EmotePickerTray:'native-library'},buttons={IconButton:'native-button'},inputs={EmoteTextInput:'native-input'},suggestions={ChatAutocompleteTray:'native-suggestions'};
const autocomplete={useAutocomplete:()=>({}),caretFromEdit:()=>0,EMOTE_URL_TEMPLATE:'animated',EMOTE_URL_TEMPLATE_STATIC:'static'};
const env={__r:id=>({72:React,5:RN,2118:{useTheme:()=>theme},245:jsx,16:{default:{buildLocalEcho:bridge}},4174:trays,3759:inputs,4619:autocomplete,4713:suggestions})[id],setInterval:fn=>{timers.push(fn);return fn;},clearInterval:fn=>timers=timers.filter(x=>x!==fn),WeakMap};
vm.createContext(env);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),env);env.install('composer');
const p={channelID:'42',emotePickerSID:'open1',sections:[{id:'channel'}],onSelectEmote:(...x)=>insertions.push(x)};
let session;
function library(){const wrapper=render(trays.EmotePickerTray,p);session=wrapper.type;const out=render(session,wrapper.props,wrapper.props.key);context=out.type==='provider'?out.props.value:null;return out;}
let out=library();assert(context);assert.equal(out.children[0].type,'native-library');assert.equal(reads,1);
const recents={key:'recents',data:[{key:'r'}]},sub={key:'channel',data:[{key:'s'}]},ref={current:null};
const native={testID:'emote-grid-list',sections:[recents,sub],ref,renderItem:x=>x.item,renderSectionHeader:x=>x.section,onViewableItemsChanged:e=>viewEvents.push(e)};
let gridFn;
function grid(){const routed=jsx.jsx(RN.SectionList,native,'gridKey');assert.equal(routed.props.key,'gridKey');const adapted=render(routed.type,routed.props);gridFn=adapted.type;return render(adapted.type,adapted.props);}
let g=grid();assert.deepEqual(Array.from(g.props.sections,s=>s.key),['recents','provider','channel']);assert.strictEqual(g.props.sections[0],recents);assert.strictEqual(g.props.sections[2],sub);
assert.equal(g.props.ListHeaderComponent.children[1].props.horizontal,true);
assert.equal(g.props.ListHeaderComponent.children[1].children[0][0].props.accessibilityLabel,'First');
for(const [i,offset,length] of [[0,84,28],[1,112,52],[2,164,0],[3,164,88],[4,252,260],[5,512,0],[6,512,28]])assert.deepEqual(JSON.parse(JSON.stringify(g.props.getItemLayout(null,i))),{index:i,offset,length});
const row=()=>g.props.renderItem({section:g.props.sections[1],item:g.props.sections[1].data[0]});
const cells=()=>row().props.data.flatMap(item=>row().props.renderItem({item}).children[0]);
let tiles=cells();assert.equal(tiles.length,3);assert(tiles[1].children[0].props.style.width>tiles[1].children[0].props.style.height);
assert.equal(row().type,'flat');assert.equal(row().props.horizontal,true);assert.equal(row().props.style.height,260);
assert.equal(row().props.keyboardShouldPersistTaps,'always');assert.equal(row().props.windowSize,3);
let header=g.props.renderSectionHeader({section:g.props.sections[1]});
assert.equal(header.children[1].children[0][0].props.style.backgroundColor,theme.colors.textBase);
assert.equal(header.children[1].children[0][0].children[0].props.style.color,theme.colors.backgroundBase);
assert.equal(header.children[1].children[0][1].props.style.backgroundColor,undefined);
tiles[1].props.onPress();assert.deepEqual(Array.from(insertions[0]),['Wide','']);assert.equal(saved[0].name,'Wide');
library();g=grid();assert.equal(reads,1);assert.equal(context.recents[0].name,'First');
config={...config,revision:2};timers.slice().forEach(fn=>fn());library();g=grid();assert.equal(reads,2);assert.equal(context.recents[0].name,'First');
header=g.props.renderSectionHeader({section:g.props.sections[1]});header.children[1].children[0][2].props.onPress();library();g=grid();assert.equal(cells().length,1);assert.equal(cells()[0].props.accessibilityLabel,'Wide');
header=g.props.renderSectionHeader({section:g.props.sections[1]});
assert.equal(header.children[1].children[0][2].props.accessibilityState.selected,true);
assert.equal(header.children[1].children[0][2].props.style.backgroundColor,theme.colors.textBase);
assert.equal(header.children[1].children[0][0].props.style.backgroundColor,undefined);
const channelKey=row().props.key;
header.children[2].children[0][1].props.onPress();library();g=grid();assert.equal(context.scope,1);assert.equal(cells()[0].props.accessibilityLabel,'Wide');
assert.notEqual(row().props.key,channelKey); // Remount horizontal scroll at the beginning after a filter change.
header=g.props.renderSectionHeader({section:g.props.sections[1]});assert.equal(header.children[2].children[0][1].props.style.backgroundColor,theme.colors.textBase);
const jumps=[];g.props.ref({scrollToLocation:x=>jumps.push(x),getScrollResponder:()=>({scrollTo:()=>{}})});
ref.current.scrollToLocation({sectionIndex:1,itemIndex:0});assert.equal(jumps.at(-1).sectionIndex,2);
const nativeTabs=[{type:'tab',props:{category:{key:'recents'},active:true,onPress:()=>nativeJumps++}},{type:'tab',props:{category:{key:'channel'},active:false,onPress:()=>nativeJumps++}}];
function nav(){const routed=jsx.jsxs(RN.ScrollView,{testID:'emote-nav-tablist',children:nativeTabs,horizontal:true});return render(routed.type,routed.props);}
let n=nav();assert.equal(n.props.children.length,3);n.props.children[1].props.onPress();assert.equal(jumps.at(-1).sectionIndex,1);library();n=nav();assert.equal(n.props.children[1].props.accessibilityState.selected,true);assert.equal(n.props.children[0].props.active,false);
n.props.children[2].props.onPress();library();assert.equal(nativeJumps,1);assert.equal(context.active,false);
g=grid();const callback=g.props.onViewableItemsChanged;const event={viewableItems:[{isViewable:true,section:g.props.sections[1]}]};callback(event);library();g=grid();assert.strictEqual(g.props.onViewableItemsChanged,callback);assert.strictEqual(viewEvents.at(-1),event);assert.equal(context.active,true);
// Stale provider identity cannot insert. Library still works with inline Off.
const stale=cells()[0];global=[];channel=[a,c];stale.props.onPress();assert.equal(insertions.length,1);
config={...config,mode:2};timers.slice().forEach(fn=>fn());assert.equal(library().type,'provider');
p.emotePickerSID='open2';library();assert.equal(context.recents[0].name,'Wide');assert.equal(context.recents.length,2);
config={...config,enabled:0};timers.slice().forEach(fn=>fn());assert.equal(library().type,'native-library');assert.equal(context,null);
const routed=jsx.jsx(RN.SectionList,native);assert.strictEqual(render(routed.type,routed.props).props,native);
assert.strictEqual(jsx.jsx(RN.View,{testID:'other'}).type,RN.View);assert.equal(buttons.IconButton,'native-button');
// A valid room with no native catalog gets a surface; unknown rooms do not.
config={...config,enabled:1};p.sections=[];p.emotePickerSID='empty';out=library();assert.equal(out.children[0].props.sections[0].id,'provider');
channel=Array.from({length:1001},(_,i)=>({...a,id:i+1000,name:'item'+i}));config={...config,revision:3};timers.slice().forEach(fn=>fn());library();g=grid();
assert.equal(g.props.sections[1].data.length,1);assert.equal(row().props.data.length,201);
assert(row().props.data.every(x=>x.emotes.length<=5));assert.equal(row().props.renderItem({item:row().props.data[0]}).children[0].length,5);
assert.equal(row().props.getItemLayout(null,200).offset,12000);
assert.equal(g.props.getItemLayout(null,4).length,260); // Catalog size never grows the outer vertical section.
p.channelID='unknown';out=library();assert.equal(out.type,'native-library');
'''
        ran = subprocess.run(['node', '-e', script, str(ROOT / 'src/rn/ProviderEmoteStrip.js')], capture_output=True, text=True)
        self.assertEqual(ran.returncode, 0, ran.stderr)
