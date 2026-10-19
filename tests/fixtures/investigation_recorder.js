/* Runs against the production owned graft in pinned compiled Hermes. */
function exerciseRecorder(render){
  var time=1000,timers=[],packets=[],sent=0,listener=null,originals=[],nativeCalls=0,unsubscribed=0;
  global.performance.now=function(){return time;};
  global.setTimeout=function(fn,delay){var t={fn:fn,delay:delay,cancelled:false};timers.push(t);return t;};
  global.clearTimeout=function(t){t.cancelled=true;};
  function flush(){var count=0;while(timers.length){var t=timers.shift();if(!t.cancelled){check(++count<20,"bounded capture timers");time+=t.delay;t.fn();}}}
  bridge.report=function(e,g,s,payload){check(e===1 && payload.length<=8192,"bounded packet");check(payload.indexOf("PRIVATE")<0,"privacy sentinel absent");packets.push(JSON.parse(payload));sent++;return _observeNative(g,s,payload,time,0);};
  var failure={PRIVATE:1},client={};
  client.translateChatMessage=function(event){nativeCalls++;check(this===client,"translation this");if(event.failed)throw failure;return event.line;};
  client.emitLine=function(line){nativeCalls++;check(this===client,"emission this");if(line.failed)throw failure;return 73;};
  client.onChannelPointsRewardEvent=function(){nativeCalls++;return 74;};
  var state={_tmiClient:client,lines:[],paused:false,pushRewardRedemption:function(){nativeCalls++;return 75;}};
  var store={getState:function(){return state;},subscribe:function(fn){check(listener===null,"single subscription");listener=fn;return function(){unsubscribed++;listener=null;};}};
  var sizes=new Map(),data=[],list={getState:function(){return {data:data,start:0,end:data.length-1,scroll:1,scrollLength:200,contentLength:400,sizes:sizes,positionAtIndex:function(i){return i*40;},elementAtIndex:function(){throw new Error("mutating helper used");},sizeAtIndex:function(){throw new Error("mutating helper used");}};}};
  var ref={current:null};render.call(store,{}, {ref:ref}).props.ref(list);
  originals.push(client.translateChatMessage,client.emitLine,client.onChannelPointsRewardEvent,state.pushRewardRedemption);
  var cmd=registered.StreamsideInvestigation().command,config=[];config.push(1023,1,2,128,12,2000,10000,2000,8,4,4,256,64,256,65536,65536);
  check(listener===null && timers.length===0,"dormant no collection");cmd(1,2,1,config);check(listener!==null,"late arm with no render");check(timers.length===0,"no armed timer");
  var privateLine={id:"PRIVATE-id",clientNonce:"PRIVATE-nonce",body:"PRIVATE-body",userName:"PRIVATE-user",isUnpublished:true};
  check(client.translateChatMessage({line:privateLine,sentByCurrentUser:true})===privateLine,"translation exact return");check(client.emitLine(privateLine)===73,"emission return");
  try{client.emitLine({failed:true});throw new Error("did not throw");}catch(e){check(e===failure,"exception identity");}
  state.lines.push({line:privateLine});data.push({line:privateLine,key:"PRIVATE-key"});sizes.set("PRIVATE-key",42);listener(state);
  check(client.onChannelPointsRewardEvent()===74 && state.pushRewardRedemption(privateLine)===75,"reward original return");
  check(sent===0 && timers.length===0,"zero per-message bridge and timer traffic");
  // More than an hour armed and a saturated ordinary stream. Priority remains independent.
  for(var i=0;i<400;i++){time+=1000;client.translateChatMessage({line:{id:"PRIVATE-"+i,clientNonce:"PRIVATE-n"+i}});client.emitLine({id:"PRIVATE-"+i});client.onChannelPointsRewardEvent();}
  while(state.lines.length<128)state.lines.push({line:privateLine});while(data.length<128)data.push({line:privateLine,key:"PRIVATE-key"});
  time+=7200000;client.emitLine(privateLine);cmd(2,2,2,config);
  check(sent===1,"history transferred before snapshot");flush();
  var rows=[];packets.forEach(function(p){check(p[0]===1,"wire version");rows=rows.concat(p[3]);});
  check(packets.length===8 && !packets[7][3].some(function(r){return r[0]===6 && (r[5]&16);}),"full final batch is not falsely truncated");
  check(packets[packets.length-1][2]===1 && calls[calls.length-1][4]===true,"complete capture acknowledged");
  var normal=0,urgent=0,member=0,listed=0,firstLabel=0;
  rows.forEach(function(r){check(r.length===9 && r.every(function(n){return Number.isInteger(n) && n>=-1 && n<=10000000;}),"numeric-only fixed rows");if(r[0]===1)normal++;if(r[0]===2)urgent++;if(r[0]===8){member=r[4];}if(r[0]===9){listed=r[4];check(r[7]===42 && r[8]===r[6]*40,"known size and position");}if(r[0]===2 && r[2]===0 && r[5]===1)firstLabel=r[4];});
  check(normal<=256 && urgent<=64 && normal>200 && urgent>0,"bounded separate rings");check(member>0 && member===listed,"store/list identity association");
  check(listener!==null && timers.length===0,"capture returns armed without timer");
  // A failed read must leave already transferred frozen history intact.
  packets=[];list.getState=function(){throw failure;};cmd(2,2,3,config);flush();check(packets[0][3][0][0]===0,"frozen history retained on snapshot failure");
  // Stop cancels pending work, releases scope and preserves foreign wrappers.
  var foreign=function(){return 99;};client.emitLine=foreign;cmd(2,2,4,config);cmd(3,3,5,config);var oldSent=sent;flush();check(sent===oldSent,"late capture cancelled");
  check(listener===null && unsubscribed===1,"subscription released");check(client.translateChatMessage===originals[0] && client.emitLine===foreign && client.onChannelPointsRewardEvent===originals[2] && state.pushRewardRedemption===originals[3],"restore owned methods only");
  for(var cycle=0;cycle<100;cycle++){cmd(1,4+cycle,6+cycle*2,config);cmd(3,4+cycle,7+cycle*2,config);}check(listener===null && timers.length===0,"repeated teardown no timers");
}
