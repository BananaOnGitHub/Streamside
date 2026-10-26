/* Production owned adapter; no added observation hooks. */
function exerciseHardening(render) {
  var time=1000,timers=[],packets=[],listener=null,originalCalls=0;
  globalThis.performance.now=function(){return time;};
  globalThis.setTimeout=function(fn,delay){var t={fn:fn,delay:delay,cancelled:false};timers.push(t);return t;};
  globalThis.clearTimeout=function(t){t.cancelled=true;};
  function flush(){while(timers.length){var t=timers.shift();if(!t.cancelled){time+=t.delay;t.fn();}}}
  bridge.report=function(e,g,s,p){packets.push(JSON.parse(p));return _observeNative(g,s,p,time,0);};
  var client={
    translateChatMessage:function(e){originalCalls++;return e.line;},
    emitLine:function(line){originalCalls++;return line;},
    onChannelPointsRewardEvent:function(){originalCalls++;return 73;}
  };
  var state={_tmiClient:client,lines:[],pushRewardRedemption:function(){originalCalls++;return 74;}};
  var store={getState:function(){return state;},subscribe:function(fn){check(!listener,"one subscription");listener=fn;return function(){listener=null;};}};
  var list={getState:function(){return {data:[],start:0,end:-1,sizes:new Map(),scroll:0,scrollLength:40,contentLength:0};}};
  render.call(store,{}, {ref:{current:null}}).props.ref(list);
  var cmd=registered.StreamsideInvestigation().command,config=[375,1,2,128,12,2000,10000,2000,8,4,4,2,2,256,65536,65536];
  cmd(1,2,1,config);
  for(var i=0;i<5;i++){time+=1000;client.translateChatMessage({line:{id:"PRIVATE-"+i}});client.emitLine({id:"PRIVATE-"+i});client.onChannelPointsRewardEvent();}
  cmd(2,2,2,config);flush();
  var rows=[];packets.forEach(function(p){rows=rows.concat(p[3]);});
  var loss=rows.filter(function(r){return r[0]===12;})[0];
  check(loss && loss[6]===8 && loss[7]===4 && loss[5]===0,"exact independent overwrite counts");
  check(packets[0][3][1][0]===12,"loss freezes in first transfer");
  cmd(3,3,3,config);
  // Copies retaining a previous owned wrapper must not reactivate it or grow
  // an observer chain on the next arm. Real action/client replacement semantics.
  var sequence=4,g=4;
  for(var cycle=0;cycle<100;cycle++){
    state=Object.assign({},state);
    client=Object.assign({},client);state._tmiClient=client;
    config[11]=256;config[12]=64;
    cmd(1,g,sequence++,config);
    var before=originalCalls;client.emitLine({id:"PRIVATE-owned-"+cycle});state.pushRewardRedemption();
    check(originalCalls===before+2,"each original called exactly once");
    packets=[];cmd(2,g,sequence++,config);flush();
    rows=[];packets.forEach(function(p){rows=rows.concat(p[3]);});
    check(rows.filter(function(r){return r[0]===1 && r[2]===1;}).length===1,"old copied wrappers stay inert");
    check(rows.filter(function(r){return r[0]===2 && r[2]===6;}).length===1,"one reward action observation");
    cmd(3,++g,sequence++,config);
    check(!listener && !timers.length,"cycle fully disarmed");
  }
  cmd(1,++g,sequence++,config);time+=10000001;packets=[];cmd(2,g,sequence++,config);flush();
  rows=[];packets.forEach(function(p){rows=rows.concat(p[3]);});
  check(rows[0][1]===10000000 && (rows[1][5]&32),"elapsed saturation explicit");
  cmd(3,++g,sequence++,config);
}
