"""Exact owned probe and geometry fixtures; no claim of Fabric virtualization."""
import ast
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class LibraryBoundaryTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node required')
    def test_stage_sampling_identity_geometry_and_bounded_cleanup(self):
        tree = ast.parse((ROOT/'tests/test_rn_library.py').read_text())
        script = next(n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'script' for t in n.targets))
        script = script.replace('deps.some((x,j)=>x!==old.deps[j])){if(old',
                                '(!deps||deps.some((x,j)=>x!==old.deps[j]))){if(old')
        script += r'''
let observations=[],scheduled=new Map(),serial=0;
env.performance={now:()=>0};
env.setTimeout=fn=>{const id=++serial;scheduled.set(id,fn);return id;};
env.clearTimeout=id=>scheduled.delete(id);
bridge.observe=(...args)=>observations.push(args);
function tick(){const pending=Array.from(scheduled);scheduled.clear();pending.forEach(([id,fn])=>fn());}
function cleanup(key){(slots.get(key)||[]).forEach(s=>{if(s&&s.cleanup)s.cleanup();});slots.delete(key);}
p.channelID='42';p.emotePickerSID='boundary';
channel=Array.from({length:950},(_,i)=>({...a,id:i+1000,name:'item'+i,url:'asset-'+i}));
config={...config,revision:4};library();g=grid();
let element=row(),columnType=element.type;
assert.equal(typeof columnType,'function');assert.equal(element.props.data.data.length,190);
let flat=render(columnType,element.props,'boundary-columns');
const virtual={state:{cellsAroundViewport:{first:0,last:6},renderMask:{enumerateRegions:()=>[{first:0,last:6,isSpacer:false},{first:7,last:189,isSpacer:true}]},pendingScrollUpdateCount:0},
 _scrollMetrics:{visibleLength:370,zoomScale:1,offset:0},_listMetrics:{getContentLength:()=>11716},
 _isNestedWithSameOrientation:()=>false,props:flat.props};
flat.props.ref({_listRef:virtual});
flat.props.onLayout({nativeEvent:{layout:{width:370,height:260}}});
assert(observations.some(x=>x[0]===16&&x[3]===0&&x[4]===6));
tick();tick();assert.equal(element.props.context.type,1);assert.equal(scheduled.size,0);
// A large internal window is observed rather than silently clamped or hidden.
virtual.state.cellsAroundViewport.last=189;virtual.state.renderMask.enumerateRegions=()=>[{first:0,last:189,isSpacer:false}];
virtual._scrollMetrics.zoomScale=0;
flat.props.onContentSizeChange(11716,260);
assert(observations.some(x=>x[0]===17&&x[3]===190));assert(observations.some(x=>x[0]===19&&x[3]===0));
const key=flat.props.keyExtractor(flat.props.data[0]);
const tileA=flat.props.renderItem({item:flat.props.data[0]}).children[0][0];
render(tileA.children[0].type,tileA.children[0].props,'stable-image');
const mounts=observations.filter(x=>x[0]===1&&x[1]===1).length;
// Rerendering the same logical cell preserves its type/key/source value.
library();g=grid();element=row();flat=render(columnType,element.props,'boundary-columns');
const tileB=flat.props.renderItem({item:flat.props.data[0]}).children[0][0];
assert.equal(tileA.props.key,tileB.props.key);assert.equal(tileA.type,tileB.type);
assert.equal(tileA.children[0].type,tileB.children[0].type);assert.equal(key,flat.props.keyExtractor(flat.props.data[0]));
render(tileB.children[0].type,tileB.children[0].props,'stable-image');
assert.equal(observations.filter(x=>x[0]===1&&x[1]===1).length,mounts);
for(const x of [60,120,180,2000,10000,9000,200]){
 flat.props.onScroll({nativeEvent:{contentOffset:{x}}});assert(scheduled.size<=1);
 assert.equal(element.props.context.type,x===9000||x===200?3:2);
}
tick();tick();tick();assert.equal(element.props.context.type,1);assert.equal(scheduled.size,0);
// Exact geometry does not depend on catalog length and keys survive layout changes.
for(const count of [1,35,950,5000])for(const width of [180,370,768]){
 channel=Array.from({length:count},(_,i)=>({...a,id:i+1000,name:'item'+i,url:'asset-'+i}));
 config={...config,revision:config.revision+1};timers.slice().forEach(fn=>fn());library();g=grid();
 g.props.onLayout({nativeEvent:{layout:{width,height:625}}});g=grid();element=row();
 const fp=element.props.data,cols=Math.max(3,Math.min(12,Math.floor(width/60))),cellWidth=width/cols;
 assert.equal(fp.data.length,Math.ceil(count/5));assert.equal(fp.initialNumToRender,cols+1);assert.equal(fp.windowSize,3);
 assert(fp.data.every(c=>c.emotes.length<=5));assert.equal(fp.getItemLayout(null,fp.data.length-1).offset,(fp.data.length-1)*cellWidth);
 const t=fp.renderItem({item:fp.data[0]}).children[0][0];assert.equal(t.props.key,1000);
 assert.equal(fp.getItemLayout(null,0).length,cellWidth);assert.equal(fp.style.height,260);
}
// Inaccessible refs fail closed and the sampler stops after twenty attempts.
flat.props.ref(null);flat.props.onScroll({nativeEvent:{contentOffset:{x:400}}});
for(let i=0;i<21;i++)tick();assert.equal(scheduled.size,0);assert(observations.some(x=>x[0]===26));
flat.props.onScroll({nativeEvent:{contentOffset:{x:500}}});assert.equal(scheduled.size,1);
cleanup('boundary-columns');assert.equal(scheduled.size,0);
cleanup('42/boundary');cleanup('stable-image');assert(observations.some(x=>x[0]===22&&x[3]===4));
assert(observations.some(x=>x[0]===2&&x[1]===1));
p.emotePickerSID='boundary-reopen';library();g=grid();assert(element.props.context.index<row().props.context.index);
// Probe is absent in production: original FlatList and its props remain.
delete bridge.observe;g=grid();assert.equal(row().type,'flat');
'''
        result = subprocess.run(['node', '-e', script, str(ROOT/'src/rn/ProviderEmoteStrip.js')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
