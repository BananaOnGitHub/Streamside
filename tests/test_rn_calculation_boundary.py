"""Production owned instance wrapper; fake RN calculations, not device evidence."""
import ast
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class CalculationBoundaryTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node required')
    def test_deadline_active_dismissal_and_diagnostic_failure(self):
        tree = ast.parse((ROOT/'tests/test_rn_library.py').read_text())
        script = next(n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'script' for t in n.targets))
        script += r'''
let events=[],scheduled=new Map(),serial=0;
env.setTimeout=(fn,delay)=>{const id=++serial;scheduled.set(id,{fn,delay});return id;};
env.clearTimeout=id=>scheduled.delete(id);bridge.observe=(...args)=>{events.push(args);return args[0]===27?1:undefined;};
function cleanup(key){(slots.get(key)||[]).forEach(s=>{if(s&&s.cleanup)s.cleanup();});slots.delete(key);}
function columns(sid){p.channelID='42';p.emotePickerSID=sid;library();g=grid();const e=row();return render(e.type,e.props,sid+'-columns');}
const result={first:0,last:6},original=function(){return result;};
const list={_adjustCellsAroundViewport:original,_listMetrics:{getContentLength:()=>420},
 _scrollMetrics:{visibleLength:370,offset:0,zoomScale:1,velocity:0},_isNestedWithSameOrientation:()=>false};
let flat=columns('deadline');list.props={...flat.props,getItemCount:d=>d.length};flat.props.ref({_listRef:list});
assert.strictEqual(list._adjustCellsAroundViewport(list.props,result,0),result);
assert(events.some(x=>x[0]===29&&x[3]===3)); // Missing metrics getter never blocks original.
let deadline=Array.from(scheduled.values()).find(x=>x.delay===5000);assert(deadline);deadline.fn();
assert.strictEqual(list._adjustCellsAroundViewport,original);assert(events.some(x=>x[0]===29&&x[3]===5));
cleanup('deadline-columns');cleanup('42/deadline');assert.equal(scheduled.size,0);
flat=columns('active-close');list.props={...flat.props,getItemCount:d=>d.length};flat.props.ref({_listRef:list});
assert.notEqual(list._adjustCellsAroundViewport,original);assert.equal(scheduled.size,2);
// Dismissal restores the active instance, cancels both timers and stays idempotent.
flat.props.ref(null);assert.strictEqual(list._adjustCellsAroundViewport,original);assert.equal(scheduled.size,1);
cleanup('active-close-columns');cleanup('42/active-close');assert.equal(scheduled.size,0);
assert.equal(events.filter(x=>x[0]===29&&x[3]===2).length,2);
'''
        result = subprocess.run(['node', '-e', script, str(ROOT/'src/rn/ProviderEmoteStrip.js')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node required')
    def test_exact_forwarding_budgets_metrics_and_restoration(self):
        tree = ast.parse((ROOT/'tests/test_rn_library.py').read_text())
        script = next(n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'script' for t in n.targets))
        script = script.replace('deps.some((x,j)=>x!==old.deps[j])){if(old',
                                '(!deps||deps.some((x,j)=>x!==old.deps[j]))){if(old')
        script += r'''
let events=[],scheduled=new Map(),serial=0,clock=0;
env.performance={now:()=>clock};
env.setTimeout=(fn,delay)=>{const id=++serial;scheduled.set(id,{fn,delay});return id;};
env.clearTimeout=id=>scheduled.delete(id);
bridge.observe=(...args)=>{events.push(args);return args[0]===27?1:undefined;};
function cleanup(key){(slots.get(key)||[]).forEach(s=>{if(s&&s.cleanup)s.cleanup();});slots.delete(key);}
function makeColumns(sid){p.channelID='42';p.emotePickerSID=sid;library();g=grid();const e=row();return [e,render(e.type,e.props,sid+'-columns')];}
channel=Array.from({length:837},(_,i)=>({...a,id:1000+i,url:'asset-'+i}));
config={...config,revision:99};
let [element,flat]=makeColumns('calculation');
let wanted={first:0,last:167},originalCalls=0,metricCalls=0,error=new Error('original error');
const frame={index:167,length:60,offset:10020};
const metricPrototype={getCellMetricsApprox(index,props){metricCalls++;assert.strictEqual(this,metric);assert.strictEqual(props,virtual.props);return frame;}};
const metric=Object.assign(Object.create(metricPrototype),{getContentLength:()=>10080});
const prototype={_adjustCellsAroundViewport(props,previous,pending,extra){
 originalCalls++;assert.strictEqual(this,virtual);assert.strictEqual(props,virtual.props);assert.strictEqual(extra,'kept');
 if(pending===999)throw error;
 assert.strictEqual(this._listMetrics.getCellMetricsApprox(167,props),frame);
 assert.strictEqual(this._listMetrics.getCellMetricsApprox(83,props),frame);
 return wanted;
}};
const virtual=Object.assign(Object.create(prototype),{props:{...flat.props,getItemCount:data=>data.length},
 _scrollMetrics:{visibleLength:370,offset:0,zoomScale:1,velocity:0},_listMetrics:metric,_isNestedWithSameOrientation:()=>false});
const original=virtual._adjustCellsAroundViewport,get=metric.getCellMetricsApprox;
flat.props.ref({_listRef:virtual});assert.notEqual(virtual._adjustCellsAroundViewport,original);
assert.equal(scheduled.size,2);assert(events.some(x=>x[0]===29&&x[3]===1));
const previous={first:0,last:6};
assert.strictEqual(virtual._adjustCellsAroundViewport(virtual.props,previous,0,'kept'),wanted);
assert.equal(originalCalls,1);assert.equal(metricCalls,2);assert.equal(previous.last,6);
assert.strictEqual(metric.getCellMetricsApprox,get);assert(!Object.hasOwn(metric,'getCellMetricsApprox'));
let rows=events.filter(x=>x[0]===27);assert.equal(rows.length,1);
let numbers=JSON.parse(rows[0][2]);assert.equal(numbers.length,41);
assert.deepEqual(numbers.slice(0,4),[0,6,0,167]);assert.equal(numbers[4],370);assert.equal(numbers[11],168);
assert.equal(numbers[15],1);assert.equal(numbers[16],2);assert.equal(numbers[18],1);
assert.equal(numbers[21],167);assert.equal(numbers[26],83);
// Source props, callback identities, timers and the installed wrapper survive a rerender.
const installed=virtual._adjustCellsAroundViewport,bind=flat.props.ref;
flat=render(element.type,element.props,'calculation-columns');assert.strictEqual(flat.props.ref,bind);
assert.strictEqual(virtual._adjustCellsAroundViewport,installed);
// Non-finite zoom is encoded safely; missing dimensions / pending / disabled are distinct.
virtual._scrollMetrics.zoomScale=NaN;virtual._adjustCellsAroundViewport(virtual.props,previous,0,'kept');
numbers=JSON.parse(events.filter(x=>x[0]===27).at(-1)[2]);assert.equal(numbers[6],5);assert.equal(numbers[7],-1);
virtual._scrollMetrics.zoomScale=1;virtual._scrollMetrics.visibleLength=0;
virtual._adjustCellsAroundViewport(virtual.props,previous,0,'kept');
assert.equal(JSON.parse(events.filter(x=>x[0]===27).at(-1)[2])[15],2);
virtual._scrollMetrics.visibleLength=370;virtual._adjustCellsAroundViewport(virtual.props,previous,1,'kept');
assert.equal(JSON.parse(events.filter(x=>x[0]===27).at(-1)[2])[15],3);
virtual.props.disableVirtualization=true;virtual._adjustCellsAroundViewport(virtual.props,previous,0,'kept');
assert.equal(JSON.parse(events.filter(x=>x[0]===27).at(-1)[2])[15],4);delete virtual.props.disableVirtualization;
assert.throws(()=>virtual._adjustCellsAroundViewport(virtual.props,previous,999,'kept'),e=>e===error);
assert.strictEqual(metric.getCellMetricsApprox,get);
// Duplicate snapshots are suppressed but real queries and original calls still occur.
for(let i=0;i<150;i++)virtual._adjustCellsAroundViewport(virtual.props,previous,0,'kept');
assert.strictEqual(virtual._adjustCellsAroundViewport,original);assert(!Object.hasOwn(virtual,'_adjustCellsAroundViewport'));
assert(events.some(x=>x[0]===28&&x[3]===128));assert(events.some(x=>x[0]===29&&x[3]===4));
assert(events.filter(x=>x[0]===27).length<=16);
cleanup('calculation-columns');cleanup('42/calculation');assert.equal(scheduled.size,0);
// Second owned instance: transition cap and own-property restoration.
[element,flat]=makeColumns('calculation-reopen');
let next=0;const ownedOriginal=function(){return {first:0,last:next++};};
const second={_adjustCellsAroundViewport:ownedOriginal,props:{...flat.props,getItemCount:d=>d.length},
 _scrollMetrics:{visibleLength:370,offset:0,zoomScale:1,velocity:0},
 _listMetrics:{getContentLength:()=>10080,getCellMetricsApprox:()=>frame},_isNestedWithSameOrientation:()=>false};
flat.props.ref({_listRef:second});for(let i=0;i<20;i++)second._adjustCellsAroundViewport(second.props,previous,0);
assert.strictEqual(second._adjustCellsAroundViewport,ownedOriginal);assert(Object.hasOwn(second,'_adjustCellsAroundViewport'));
assert.equal(events.filter(x=>x[0]===27&&x[3]===2).length,16);assert(events.some(x=>x[0]===29&&x[3]===6));
cleanup('calculation-reopen-columns');cleanup('42/calculation-reopen');assert.equal(scheduled.size,0);
// Later lists are not instrumented; no history or timers grow with reopening.
[element,flat]=makeColumns('calculation-third');flat.props.ref({_listRef:second});
assert.strictEqual(second._adjustCellsAroundViewport,ownedOriginal);assert.equal(scheduled.size,1);
cleanup('calculation-third-columns');cleanup('42/calculation-third');assert.equal(scheduled.size,0);
'''
        result = subprocess.run(['node', '-e', script, str(ROOT/'src/rn/ProviderEmoteStrip.js')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
