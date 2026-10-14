/* Shared Node/source and Hermes/shipped-graft fixture. Host React, not Fabric. */
var packets=[], timer=null, context=null, slots=new Map(), activeSlots=null, cursor=0;
function check(value,reason) { if (!value) throw new Error(reason); }
function same(a,b,reason) { check(a===b,reason); }
function element(type,props,key) { return {type:type,props:props,key:key}; }
var React={
  memo:function (fn) { return fn; },
  createContext:function () { return {Provider:"context"}; },
  createElement:function (type,props,child) { var copy=Object.assign({},props); if (arguments.length>2) copy.children=child; return element(type,copy); },
  useContext:function () { return context; },
  useRef:function (value) { var i=cursor++; return activeSlots[i] || (activeSlots[i]={current:value}); },
  useMemo:function (fn,deps) { var i=cursor++, old=activeSlots[i];
    if (!old || old.deps.length!==deps.length || deps.some(function (v,j) { return v!==old.deps[j]; })) activeSlots[i]={deps:deps.slice(),value:fn()};
    return activeSlots[i].value;
  }
};
function render(fn,p) { activeSlots=slots.get(fn)||[]; slots.set(fn,activeSlots); cursor=0; return fn(p); }
var calls=[], failure=null;
function Client() {}
Client.prototype.translateChatMessage=function (event,second) { calls.push([this,event,second]); if (failure) throw failure; return event.line; };
Client.prototype.emitLine=function (line,second) { calls.push([this,line,second]); if (failure) throw failure; return second; };
var nativeTranslate=Client.prototype.translateChatMessage,nativeEmit=Client.prototype.emitLine;
var bridge={trace:function (packet) {
  var values=JSON.parse(packet); check(values.length===8 && values.every(function(v){return typeof v==="number" && Number.isFinite(v);}),"numeric-only wire");
  packets.push(values); return typeof _observeNative==="function"?_observeNative(60,0,packet,0,0):1;
}};
var jsx={jsx:element,jsxs:element}, lines={ChatLine:"native-line"};
var RN={StyleSheet:{create:function (x) { return x; }}};
var modules={1:function (x) { return {default:x}; },17:{},72:React,5:RN,245:jsx,16:{default:{buildLocalEcho:bridge}},4782:lines,3500:{LibraryTmiClient:Client}};
_runtimeGlobal.__r=function (id) { return modules[id]; };
_runtimeGlobal.setTimeout=function (fn,ms) { same(ms,120000,"bounded timer"); timer=fn; return 1; };
_runtimeGlobal.clearTimeout=function () { timer=null; };
var installEntry=typeof install==="function"?install:buildLocalEcho;
if (typeof _chatFactory!=="undefined") {
  var exports={};
  buildLocalEcho(_runtimeGlobal,__r,null,null,{},exports,[1,17,72,5,245,4782,519,2071,1846,3488,517,4897,4898,3487,4899,3458,2085,4900,4901,3864,4904,4905]);
  installEntry=function () { return exports.ChatMessageList; };
}
var original="original", Wrapped=installEntry(original);
check(Wrapped!==original,"installer/factory installed");
function store(client) {
  var state={_tmiClient:client,lines:[],connected:true}, listener=null, unsub=0;
  return {state:state,getState:function(){return state;},subscribe:function(fn){listener=fn;return function(){unsub++;listener=null;};},notify:function(){if(listener)listener();},unsub:function(){return unsub;}};
}
var a=new Client(), b=new Client(), sa=store(a), sb=store(b), unknown=new Client();
var p={chatStore:sa}, out=render(Wrapped,p); same(out.props.children.props.chatStore,sa,"original list props"); context=out.props.value;
var line={id:"private-id",clientNonce:"private-nonce",isUnpublished:true,emotes:[{id:"900000000000001"}],body:"private-body",username:"private-user"};
var event={line:line,sentByCurrentUser:true}, translated=a.translateChatMessage(event,42);
same(translated,line,"translation identity"); same(calls[0][0],a,"translation this"); same(calls[0][2],42,"translation args");
same(a.emitLine(line,123),123,"emit return"); same(calls[1][1],line,"emit args");
sa.state.lines=[{key:"private-key",line:line}]; sa.notify();
var nativeProps={testID:"chat-message-list",data:sa.state.lines,recycleItems:false,estimatedItemSize:36,renderItem:function(item,second){same(this,sa,"render this");same(second,22,"render args");return item;}};
var listElement=jsx.jsx("native-list",nativeProps,"key"), list=render(listElement.type,listElement.props);
same(list.type,"native-list","no native wrapper"); same(list.props.recycleItems,false,"recycling unchanged"); same(list.props.estimatedItemSize,36,"estimate unchanged");
var item={item:sa.state.lines[0]}; same(list.props.renderItem.call(sa,item,22),item,"render return");
var scroll={getNativeScrollRef:function(){return {measureInWindow:function(cb){cb(0,0,400,800);}};}};
list.props.ref(scroll);
var rowContext=render(lines.ChatLine,{chatStore:sa,line:line}); context=rowContext.props.value;
var layoutCalls=0, refNode=null, cleanupCalls=0, onLayout=function(e){layoutCalls++;same(this,sa,"layout this");return 9;};
var ref=function(node){refNode=node;return function(){cleanupCalls++;return 88;};};
var rowProps={testID:"chat-message-row",ref:ref,onLayout:onLayout,style:{width:77}};
var rowElement=jsx.jsx("native-row",rowProps,"row-key"), row=render(rowElement.type,rowElement.props);
same(row.type,"native-row","no row host wrapper");same(row.props.style,rowProps.style,"row style identity");
var node={measureInWindow:function(cb){cb(0,150,100,44);}}, cleanup=row.props.ref(node);same(refNode,node,"forward ref");
var e={nativeEvent:{layout:{height:44,width:100,x:0,y:150}}};same(row.props.onLayout.call(sa,e),9,"layout return");same(layoutCalls,1,"layout once");
var rowAgain=render(rowElement.type,rowElement.props);same(rowAgain.props.ref,row.props.ref,"stable ref");same(cleanup(),88,"cleanup return");same(cleanupCalls,1,"cleanup once");
var delayed=null, node2={measureInWindow:function(cb){delayed=cb;}};
row.props.ref(node2);row.props.onLayout.call(sa,e);row.props.ref(null);
var before=packets.length;delayed(0,1,1,1);same(packets.length,before,"stale geometry rejected");
context=out.props.value;
var reported=null, report=function(error){reported=error;return 7;}, error=new TypeError("private-error");
var boundaryElement=jsx.jsx("native-boundary",{name:"ChatLine",reportError:report,children:{props:{line:line}},fallback:undefined}), boundary=render(boundaryElement.type,boundaryElement.props);
same(boundary.props.reportError(error),7,"report return");same(reported,error,"report identity");same(boundary.props.fallback,undefined,"fallback unchanged");
render(Wrapped,{chatStore:sb});context=render(Wrapped,{chatStore:sb}).props.value;
var line2={id:"private-id",emotes:[]};sb.state.lines=[{line:line2}];b.translateChatMessage({line:line2});b.emitLine(line2,1);
context=out.props.value; boundary.props.reportError(error);
check(packets.some(function(v){return v[0]===9 && v[1]===1 && v[2]===1;}),"error remains original session");
check(packets.some(function(v){return v[0]===2 && v[1]===2 && v[2]===1;}),"separate session labels");
var echo={id:"replacement-id",clientNonce:"private-nonce"};a.translateChatMessage({line:echo});a.emitLine(echo,1);
check(packets.filter(function(v){return v[0]===2 && v[1]===1;}).every(function(v){return v[2]===1;}),"nonce reconciliation");
before=packets.length;unknown.emitLine(line,3);same(packets.length,before,"unscoped client");
a.translateChatMessage({line:null,sentByCurrentUser:true});
check(packets.some(function(v){return v[0]===1 && v[2]===0 && v[4]===0 && v[3]===1;}),"null own translation");
failure=error;try{a.emitLine(line,1);throw "not thrown";}catch(caught){same(caught,error,"original exception identity");} failure=null;
check(packets.some(function(v){return v[0]===3 && v[4]===0 && v[5]===1;}),"emit failure");
check(packets.some(function(v){return v[0]===5 && v[4]===1;}) && packets.some(function(v){return v[0]===5 && v[4]===2;}),"data versus rendered");
check(packets.some(function(v){return v[0]===7;}) && packets.some(function(v){return v[0]===8;}),"window geometry");
check(JSON.stringify(packets).indexOf("private")===-1,"privacy");
if (typeof _diagnosticReport==="function") { var reportText=_diagnosticReport();check(reportText.indexOf("s1 m1")>=0 && reportText.indexOf("error=1")>=0 && reportText.indexOf("private")===-1 && reportText.indexOf("Null translations/all-own: 1/1")>=0,"native report"); }
var foreign=function(){};Client.prototype.emitLine=foreign;var stop=timer;stop();
same(Client.prototype.emitLine,foreign,"foreign replacement preserved");same(Client.prototype.translateChatMessage,nativeTranslate,"owned hook restored");same(sa.unsub(),1,"unsubscribe");same(sb.unsub(),1,"unsubscribe2");
before=packets.length;sa.notify();row.props.onLayout.call(sa,e);same(packets.length,before,"stopped trace silent");
bridge.trace=null; same(installEntry(original),typeof _chatFactory!=="undefined"?Wrapped:original,"missing bridge no-op");
