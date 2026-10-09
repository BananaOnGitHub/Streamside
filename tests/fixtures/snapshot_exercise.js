/* Runs after the production graft's installer in matching Hermes-98.
 * RN/React objects are fixtures. Snapshot generation is never reimplemented. */
function check(ok,message){if(!ok)throw new Error(message);}
var events=[],scheduled=new Map(),serial=0,rejectDelivery=false;
_runtimeGlobal.setTimeout=function(fn,delay){var id=++serial;scheduled.set(id,{fn:fn,delay:delay});return id;};
_runtimeGlobal.clearTimeout=function(id){scheduled.delete(id);};
bridge.observe=function(e,s,asset,x,y){
 events.push([e,s,asset,x,y]);
 if(e===27&&rejectDelivery)return 0;
 return _observeNative(e,s,asset===undefined?null:asset,x===undefined?0:x,y===undefined?0:y);
};
check(typeof buildLocalEcho('composer')==='function','installer result');
check(typeof trays.EmotePickerTray==='function','compiled installer library binding');
check(bridge.getSnapshot('42')!==null,'fixture snapshot');
channel=Array.from({length:837},function(_,i){return Object.assign({},a,{id:1000+i,url:'asset-'+i});});
config=Object.assign({},config,{revision:99});
var p={channelID:'42',emotePickerSID:'pipeline',sections:[{id:'channel'}],onSelectEmote:function(){}};
function cleanup(key){(slots.get(key)||[]).forEach(function(s){if(s&&s.cleanup)s.cleanup();});slots.delete(key);}
function columns(sid){
 p.emotePickerSID=sid;
 var wrapper=render(trays.EmotePickerTray,p),session=render(wrapper.type,wrapper.props,wrapper.props.key);
 check(session.type==='provider','fallback reads='+reads+' state='+JSON.stringify(config)+' props='+JSON.stringify(wrapper.props));
 context=session.props.value;check(!!context,'library context');
 var routed=jsx.jsx(RN.SectionList,{testID:'emote-grid-list',sections:[{key:'recents',data:[]},{key:'channel',data:[]}],renderItem:function(x){return x.item;},renderSectionHeader:function(x){return x.section;}},'grid');
 var adapted=render(routed.type,routed.props),grid=render(adapted.type,adapted.props);
 var row=grid.props.renderItem({section:grid.props.sections[1],item:grid.props.sections[1].data[0]});
 check(typeof row.type==='function','diagnostic columns adapter');
 return render(row.type,row.props,sid+'-columns');
}
var flat=columns('pipeline');check(flat.props.data.length===168,'real catalog to five-row column geometry');
var previous={first:0,last:6},result={first:0,last:167},originalCalls=0,frameCalls=0,thrown=new Error('PRIVATE-SENTINEL');
var frame={length:flat.props.getItemLayout(null,1).length,offset:flat.props.getItemLayout(null,1).offset};
var queried=true,shouldThrow=false;
function getter(index,props){frameCalls++;check(this===list._listMetrics,'metric receiver');check(props===list.props,'metric props');return frame;}
function metrics(){return {getContentLength:function(){return 10360;},getCellMetricsApprox:getter};}
var prototype={_adjustCellsAroundViewport:function(props,before,pending,extra){
 originalCalls++;check(this===list&&props===list.props&&before===previous&&extra==='kept','original receiver/arguments');
 if(shouldThrow)throw thrown;
 if(queried){check(this._listMetrics.getCellMetricsApprox(1,props)===frame,'frame identity');check(this._listMetrics.getCellMetricsApprox(2,props)===frame,'frame identity');}
 return result;
}};
var list=Object.assign(Object.create(prototype),{props:Object.assign({},flat.props,{getItemCount:function(data){return data.length;}}),
 _listMetrics:metrics(),_scrollMetrics:{visibleLength:370,offset:0,zoomScale:1,velocity:0},_isNestedWithSameOrientation:function(){return false;}});
var original=list._adjustCellsAroundViewport;
flat.props.ref({_listRef:list});
function call(){var count=originalCalls;check(list._adjustCellsAroundViewport(list.props,previous,0,'kept')===result,'result identity');check(originalCalls===count+1,'one original call');}
call();
var packets=events.filter(function(x){return x[0]===27;});check(packets.length===1,'compiled production snapshot emitted');
var values=JSON.parse(packets[0][2]);check(values.length===41&&values[4]===370&&values[5]===10360&&values[11]===168&&values[15]===1,'snapshot numeric shape');
check(values[16]===2&&values[21]===1&&values[26]===2,'only actual frame queries sampled');
check(_diagnosticReport().indexOf('calc list=1 transition=1')>=0,'production native acceptance');
check(list._listMetrics.getCellMetricsApprox===getter,'restore after success');
var snapshotCount=packets.length;call();check(events.filter(function(x){return x[0]===27;}).length===snapshotCount,'identical snapshot suppressed');
function failure(step,setup,restore){var start=events.length;setup();call();restore();check(events.slice(start).some(function(x){return x[0]===30&&x[3]===step&&x[4]===2;}),'explicit failure stage '+step);}
var count=list.props.getItemCount;
failure(1,function(){list.props.getItemCount=function(){throw thrown;};queried=false;},function(){list.props.getItemCount=count;queried=true;});
failure(2,function(){list._listMetrics.getContentLength=function(){throw thrown;};},function(){list._listMetrics=metrics();});
var finite=Number.isFinite;
failure(3,function(){Number.isFinite=undefined;},function(){Number.isFinite=finite;});
var nested=list._isNestedWithSameOrientation;
failure(4,function(){list._isNestedWithSameOrientation=function(){throw thrown;};},function(){list._isNestedWithSameOrientation=nested;});
failure(5,function(){list._listMetrics.getCellMetricsApprox=null;queried=false;},function(){list._listMetrics=metrics();queried=true;});
failure(6,function(){Object.defineProperty(list._listMetrics,'getCellMetricsApprox',{value:getter,writable:false,configurable:true});},function(){list._listMetrics=metrics();});
failure(8,function(){
 var value=getter;list._listMetrics=new Proxy(metrics(),{get:function(o,k){return k==='getCellMetricsApprox'?value:o[k];},set:function(o,k,v){if(k==='getCellMetricsApprox'){if(v===getter)throw thrown;value=v;return true;}o[k]=v;return true;}});
},function(){list._listMetrics=metrics();});
var layout=list.props.getItemLayout;
failure(7,function(){list.props.getItemLayout=function(){throw thrown;};list._scrollMetrics.offset=1;},function(){list.props.getItemLayout=layout;});
failure(9,function(){result={last:167};Object.defineProperty(result,'first',{get:function(){throw thrown;}});},function(){result={first:0,last:167};});
var concat=Array.prototype.concat;
failure(10,function(){Array.prototype.concat=function(){throw thrown;};},function(){Array.prototype.concat=concat;});
var stringify=JSON.stringify;
failure(11,function(){JSON.stringify=function(){throw thrown;};},function(){JSON.stringify=stringify;});
failure(12,function(){rejectDelivery=true;list._scrollMetrics.offset=2;},function(){rejectDelivery=false;});
var beforeDelivery=events.filter(function(x){return x[0]===27;}).length;
call();check(events.filter(function(x){return x[0]===27;}).length===beforeDelivery+1,'failed delivery retries on next real calculation');
// Original error survives instrumentation and metrics restoration.
shouldThrow=true;try{call();throw new Error('missing original throw');}catch(e){check(e===thrown,'original error identity');}shouldThrow=false;
check(list._listMetrics.getCellMetricsApprox===getter,'restore after original throw');
// Native interface rejects malformed packets; content never appears in report.
check(_observeNative(27,0,'[PRIVATE-SENTINEL]',1,0)===0,'native malformed packet acknowledgement');
check(_observeNative(27,0,packets[0][2],3,0)===0,'native slot restriction');
// Populate first slot to its real 16 transition limit, using actual real calls.
for(var i=0;i<30&&list._adjustCellsAroundViewport!==original;i++){result={first:0,last:i};call();}
check(list._adjustCellsAroundViewport===original,'snapshot cap restores original');
check(_diagnosticReport().indexOf('calc list=1 transition=16')>=0,'native first slot cap');
flat.props.ref(null);cleanup('pipeline-columns');cleanup('42/pipeline');
// Second list: own method, bounded lifetime and dismissal; no history growth.
flat=columns('reopening');list.props=Object.assign({},flat.props,{getItemCount:function(data){return data.length;}});list._listMetrics=metrics();
list._adjustCellsAroundViewport=original;flat.props.ref({_listRef:list});
for(var j=0;j<16;j++){result={first:j,last:j+6};call();}
check(list._adjustCellsAroundViewport===original,'second slot restoration');
check(_diagnosticReport().indexOf('calc list=2 transition=16')>=0,'second slot native records');
flat.props.ref(null);cleanup('reopening-columns');cleanup('42/reopening');
check(scheduled.size===0,'all startup timers released');
check(_diagnosticReport().indexOf('PRIVATE-SENTINEL')<0,'private exception strings not retained');

["props/catalog","content/scroll metrics","numeric classification","base values","metric getter","metric observer install","frame sampling","metric observer restore","result values","frame packing","serialization","native delivery"].forEach(function(name){var line=_diagnosticReport().split("\n").filter(function(x){return x.indexOf("Snapshot step "+name+" attempted/passed/failed:")===0;})[0];check(!!line&&Number(line.split("/").pop())>=1,"native failure counter "+name);});
