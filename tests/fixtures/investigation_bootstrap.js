var global=_runtimeGlobal, calls=[], registered={}, jsxCalls=0, reads=0, refCalls=0, cleanupCalls=0;
function check(x,why){if(!x)throw new Error(why);}
var nativeJSX=function(type,props){jsxCalls++;return {type:type,props:props};};
global.performance={now:function(){return 1000;}};
var bridge={startup:function(mask){check(mask===255,"startup API availability");},report:function(){return 1;},ready:function(abi,caps){check(abi===1,"ABI");calls.push([abi,caps]);return 1;},ack:function(epoch,generation,sequence,operation,success){calls.push([epoch,generation,sequence,operation,success]);}};
var map={};map.StreamsideInvestigation=bridge;
var modules={16:{default:map},245:{jsx:nativeJSX},1:function(x){return {default:x};},17:{},72:{memo:function(fn){return fn;}},5:{StyleSheet:{create:function(x){return x;}}}};
global.__r=function(id){return modules[id];};
global.RN$registerCallableModule=function(name,get){check(!registered[name],"single callable registration");registered[name]=get;};
global.setInterval=function(){throw new Error("diagnostic interval forbidden");};
global.setTimeout=function(){throw new Error("dormant timeout forbidden");};
var nativeStore={getState:function(){reads++;throw new Error("dormant store scan forbidden");}};
var sourceRef=function(node){refCalls++;check(this===nativeStore,"ref this");return function(){cleanupCalls++;check(this===nativeStore,"cleanup this");return 73;};};
function exerciseBootstrap(render){
  var props={ref:sourceRef,data:[],estimatedItemSize:36,style:{height:1}},type={native:true};
  var first=render.call(nativeStore,type,props),second=render.call(nativeStore,type,props);
  check(first.type===type&&second.type===type,"original component identity");
  check(first.props.data===props.data&&first.props.style===props.style&&first.props.estimatedItemSize===36,"functional props unchanged");
  check(first.props.ref===second.props.ref,"stable ref callback");
  check(modules[245].jsx===nativeJSX,"global JSX unchanged");
  var node={},cleanup=first.props.ref.call(nativeStore,node),count=jsxCalls;
  check(refCalls===1&&reads===0,"original ref once; no dormant scan");
  registered.StreamsideInvestigation().command(0,0,0,null);
  check(jsxCalls===count&&refCalls===1&&reads===0,"late command without render or ref remount");
  check(calls[calls.length-1][4]===true,"startup command acknowledged");
  check(cleanup.call(nativeStore)===73&&cleanupCalls===1,"cleanup result/this preserved");
  var failure={private:'not exported'},failing=function(){throw failure;};
  var item=render.call(nativeStore,type,{ref:failing});
  try{item.props.ref.call(nativeStore,node);throw new Error("missing ref exception");}catch(error){check(error===failure,"original exception identity");}
  for(var i=0;i<100;i++){var r={current:null},e=render.call(nativeStore,type,{ref:r});e.props.ref(node);check(r.current===node,"object ref forwarded");e.props.ref(null);check(r.current===null,"object ref cleared");}
  check(reads===0,"no speculative reads");
  var reused=render.call(nativeStore,type,{ref:sourceRef}).props.ref;
  var oldCleanup=reused.call(nativeStore,{}),newCleanup=reused.call(nativeStore,{});
  oldCleanup.call(nativeStore);newCleanup.call(nativeStore);

}
