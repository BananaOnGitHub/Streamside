/* Production snapshot projection: no additional app adapter or instrumentation. */
function exerciseViewport(render){
  var time=1000,timers=[],packets=[],seq=0,capturingNow=false,reads=0;
  globalThis.performance.now=function(){return time;};
  globalThis.setTimeout=function(fn,delay){timers.push([fn,delay]);return fn;};
  globalThis.clearTimeout=function(fn){timers=timers.filter(function(t){return t[0]!==fn;});};
  function flush(){var n=0;while(timers.length){check(++n<20,"bounded capture");var t=timers.shift();time+=t[1];t[0]();}}
  bridge.report=function(e,g,s,p){check(e===1 && p.length<=8192 && p.indexOf("PRIVATE")<0,"bounded private-free wire");packets.push(JSON.parse(p));return _observeNative(g,s,p,time,0);};
  function immutable(o){return new Proxy(o,{set:function(){throw new Error("source write");},defineProperty:function(){throw new Error("source define");},deleteProperty:function(){throw new Error("source delete");}});}
  function line(i){return immutable({id:"PRIVATE-id-"+i,clientNonce:"PRIVATE-nonce-"+i});}
  function setup(length,storeLength,first,last,option){
    option=option || {};var data=[],lines=[],sizes=new Map(),positions={},cache=immutable({}),state,notify=null,readIndices=[],storeIndices=[],trace=[],client={emitLine:function(){return 1;},translateChatMessage:function(e){return e;}};
    for(var i=0;i<length;i++){var value={line:line(i),key:"PRIVATE-key-"+i};data.push(immutable(value));sizes.set(value.key,40);positions[i]=i*40;}
    for(var i=0;i<storeLength;i++)lines.push(immutable({line:line(i+Math.max(0,length-storeLength))}));
    if(option.tailStore){lines=[];for(var i=0;i<storeLength;i++)lines.push(immutable({line:line(i-storeLength+length)}));}
    if(option.missingStore!==undefined)lines=lines.filter(function(v){return v.line.id!=="PRIVATE-id-"+option.missingStore;});
    if(option.measurements){sizes.delete("PRIVATE-key-"+first);sizes.set("PRIVATE-key-"+(first+1),0);sizes.set("PRIVATE-key-"+(first+2),34.125);sizes.set("PRIVATE-key-"+(first+3),NaN);sizes.set("PRIVATE-key-"+(first+4),-2);sizes.set("PRIVATE-key-"+(first+5),undefined);sizes.set("PRIVATE-key-"+(first+6),0.0001);}
    if(option.objectOnly){var object=immutable({});data[0]=immutable({line:object,key:"PRIVATE-key-0"});lines[0]=immutable({line:object});}
    data=new Proxy(data,{get:function(a,k){
      if(typeof k==="string" && String(+k)===k && +k>=0){if(capturingNow)check(packets.length>0,"frozen history transferred before row read");readIndices.push(+k);if(capturingNow)trace.push("row");if(option.slow && +k===first+2)time+=3;if(option.rowThrow && +k===first)throw new Error("row unavailable");}
      return a[k];
    },set:function(){throw new Error("data mutation");},defineProperty:function(){throw new Error("data define");},deleteProperty:function(){throw new Error("data delete");}});
    var source=immutable({data:data,start:first,end:last,scroll:first*40,scrollLength:300,contentLength:length*40,sizes:option.noSizes?null:sizes,positionAtIndex:function(i){check(i>=0 && i<length,"valid position index");return positions[i];},elementAtIndex:function(){throw new Error("elementAtIndex forbidden");},sizeAtIndex:function(){throw new Error("sizeAtIndex forbidden");},idCache:cache});
    lines=new Proxy(lines,{get:function(a,k){
      if(capturingNow && typeof k==="string" && String(+k)===k && +k>=0){storeIndices.push(+k);if(option.storeSlow)time+=0.3;if(option.storeThrow && +k===a.length-1)throw new Error("store row unavailable");}
      return a[k];
    },set:function(){throw new Error("store mutation");},defineProperty:function(){throw new Error("store define");},deleteProperty:function(){throw new Error("store delete");}});
    state=immutable({_tmiClient:client,lines:lines,paused:false});
    var store={getState:function(){reads++;if(capturingNow){check(packets.length>0,"history precedes store getter");trace.push("store");if(option.changed && notify)notify(state);if(option.storeDelay)time+=3;}return state;},subscribe:function(fn){notify=fn;return function(){notify=null;};}};
    var node={getState:function(){if(capturingNow){check(packets.length>0,"history precedes visible range getter");trace.push("list");}if(option.getterThrow)throw new Error("list unavailable");return source;}};
    var ref={current:null},wrapped=render.call(store,{}, {ref:ref}).props.ref;wrapped(node);
    return {store:store,client:client,data:data,lines:lines,sizes:sizes,cache:cache,indices:readIndices,storeIndices:storeIndices,trace:trace,unmount:function(){wrapped(null);},notify:function(){if(notify)notify(state);}};
  }
  var cmd=registered.StreamsideInvestigation().command,config=[];config.push(375,1,2,128,12,2000,10000,2000,8,4,4,256,64,256,65536,65536);
  function captureCase(cases){
    packets=[];time+=5000;var g=100+(++seq)*2,before=cases.map(function(c){return c.sizes.size;});
    cmd(1,g,1,config);cases[0].client.translateChatMessage({id:"PRIVATE-live"});cases[0].client.emitLine({id:"PRIVATE-live"});
    check(timers.length===0,"no armed polling");capturingNow=true;cmd(2,g,2,config);capturingNow=false;flush();
    check(cases.every(function(c){return c.trace[0]==="list";}),"visible range getter precedes store snapshot");
    check(packets[0][3][0][0]===0 && packets.every(function(p){return p[0]===4;}),"frozen history and version");
    var rows=[];packets.forEach(function(p){rows=rows.concat(p[3]);});
    check(rows.filter(function(r){return r[0]===8 || r[0]===9;}).length<=128,"shared entry cap");
    check(packets[packets.length-1][2]===1 && calls[calls.length-1][4]===true,"capture complete, case "+seq);
    cmd(3,g+1,3,config);cases.forEach(function(c,i){check(c.sizes.size===before[i] && Object.keys(c.cache).length===0,"measurement map and idCache immutable");c.unmount();});
    check(timers.length===0,"capture timer cleaned");return rows;
  }
  function kinds(rows,k){return rows.filter(function(r){return r[0]===k;});}
  function indices(rows){return kinds(rows,9).map(function(r){return r[6];});}
  // Both real device regressions: the previous projection read 0..63 or 22..85.
  var c=setup(127,127,119,126,{measurements:true}),rows=captureCase([c]),sample=indices(rows),members=kinds(rows,9),coverage=kinds(rows,10)[0];
  check(JSON.stringify(sample)===JSON.stringify([119,120,121,122,123,124,125,126,118,117]),"viewport then two-row margin at end");
  check((coverage[5]&7)===1 && coverage[6]===119 && coverage[7]===126 && coverage[8]===8,"complete requested viewport");
  check((members[0][5]&1) && members[0][7]===-1,"never measured");check((members[1][5]&2) && members[1][7]===0,"measured zero");
  check(!(members[2][5]&7) && members[2][7]===34125,"fractional measured height preserved");
  check([3,5].every(function(i){return (members[i][5]&4) && members[i][7]===-1;}) && (members[4][5]&4) && members[4][7]===-2000,"invalid measurements not unknown or zero");
  check(!(members[6][5]&2),"positive sub-resolution height is never marked measured zero");
  check(members.every(function(r){return (r[5]&8) && r[4]>0;}),"tail membership correlated by stable identity");
  c=setup(150,391,140,149,{tailStore:true});rows=captureCase([c]);check(indices(rows).slice(0,10).every(function(i,n){return i===140+n;}),"second device viewport regression");
  check(kinds(rows,9).every(function(r){return r[5]&8;}),"visible rows found in larger store tail");
  c=setup(150,151,142,149,{storeSlow:true});rows=captureCase([c]);var traversal=kinds(rows,11)[0];
  check(JSON.stringify(c.storeIndices)===JSON.stringify([150,149,148,147,146,145,144]),"device budget regression reads newest seven, not old indices 33..39");
  check((traversal[5]&11)===11 && (traversal[5]&512) && traversal[6]===7 && traversal[7]===144 && traversal[8]===150,"deadline traversal progress is explicit");
  check(kinds(rows,9).filter(function(r){return r[5]&128;}).length===8 && (kinds(rows,10)[0][5]&1),"viewport remains first and complete");
  check(kinds(rows,6)[0][6]>=2000 && kinds(rows,6)[0][6]<2400 && config[7]===2000,"same two millisecond deadline, no deferred scan");
  c=setup(20,20,12,19,{storeDelay:true});rows=captureCase([c]);traversal=kinds(rows,11)[0];check((traversal[5]&8) && !(traversal[5]&2) && traversal[6]===0 && traversal[7]===-1 && traversal[8]===-1,"budget before traversal explicitly did not reach newest entry");
  c=setup(10,10,4,9,{storeThrow:true});rows=captureCase([c]);traversal=kinds(rows,11)[0];check((traversal[5]&32) && !(traversal[5]&2) && traversal[6]===9 && traversal[8]===8,"failed newest read cannot claim tail reached");
  c=setup(1000,1000,500,508);rows=captureCase([c]);check(JSON.stringify(indices(rows))===JSON.stringify([500,501,502,503,504,505,506,507,508,499,509,498,510]),"middle viewport and both margins");
  check(kinds(rows,9).every(function(r){return (r[5]&32) && !(r[5]&16);}),"partial store tail cannot assert absence");
  traversal=kinds(rows,11)[0];check((traversal[5]&18)===18 && traversal[8]===999 && traversal[7]===885 && traversal[6]===115,"entry cap and newest-first bounds explicit");
  c=setup(5,7,0,4);rows=captureCase([c]);check(kinds(rows,8).filter(function(r){return r[6]>=5;}).every(function(r){return r[5]&16;}),"store-only rows absent after complete comparable list");
  traversal=kinds(rows,11)[0];check((traversal[5]&7)===7 && traversal[6]===7 && traversal[7]===0 && traversal[8]===6,"complete store traversal explicit");
  c=setup(10,10,2,4,{missingStore:3});rows=captureCase([c]);check(kinds(rows,9).some(function(r){return r[6]===3 && (r[5]&16);}),"list-only row absent after complete comparable store scan");
  c=setup(1,1,0,0,{objectOnly:true});rows=captureCase([c]);check(kinds(rows,9)[0][5]&512 && kinds(rows,9)[0][5]&8,"object-only direct association explicit");
  c=setup(300,300,50,249);rows=captureCase([c]);coverage=kinds(rows,10)[0];check((coverage[5]&2) && !(coverage[5]&1) && coverage[8]===128,"oversized viewport explicitly partial");check(!kinds(rows,9).some(function(r){return r[5]&256;}),"margin never displaces visible rows");
  c=setup(130,130,1,128);rows=captureCase([c]);coverage=kinds(rows,10)[0];check((coverage[5]&10)===10 && coverage[8]===128 && !(kinds(rows,6)[0][5]&4),"entry-bound margin shortage is partial without a false time-budget flag");
  c=setup(10,10,2,5,{changed:true});rows=captureCase([c]);check(kinds(rows,11)[0][5]&64,"changed traversal explicit");coverage=kinds(rows,10)[0];check((coverage[5]&66)===66 && !(coverage[5]&1),"changed snapshot range is explicitly partial");check(rows.filter(function(r){return r[0]===8 || r[0]===9;}).every(function(r){return (r[5]&32) && !(r[5]&24);}),"changed membership cannot claim present or absent");
  config[13]=8;c=setup(80,80,0,39);rows=captureCase([c]);config[13]=256;check(kinds(rows,11)[0][5]&256,"alias continuity limit explicit");var byIndex={};kinds(rows,8).forEach(function(r){byIndex[r[6]]=r[4];});check(kinds(rows,9).every(function(r){return (r[5]&8) && byIndex[r[6]]===r[4];}),"snapshot association survives bounded alias eviction without raw-identity copies");
  c=setup(20,20,3,8,{slow:true});rows=captureCase([c]);coverage=kinds(rows,10)[0];check((coverage[5]&2) && (coverage[5]&128) && coverage[8]<6,"time budget explicitly partial");
  c=setup(20,20,3,8,{rowThrow:true});rows=captureCase([c]);check(kinds(rows,10)[0][5]&2,"row read failure cannot claim complete");
  c=setup(10,10,2,5,{noSizes:true});rows=captureCase([c]);check(kinds(rows,9).every(function(r){return (r[5]&1024) && !(r[5]&3);}),"measurement access unavailable is not never measured or zero");
  var ranges=[[undefined,undefined],[-1,3],[5,3],[0,99],[0.5,4],[NaN,4]];
  ranges.forEach(function(range){var c=setup(10,10,range[0],range[1]),rows=captureCase([c]),coverage=kinds(rows,10)[0];check((coverage[5]&4) && !(coverage[5]&1) && (coverage[5]&16),"invalid range labels tail fallback unavailable");check(kinds(rows,9).every(function(r){return !(r[5]&384);}),"fallback rows never labelled visible or margin");});
  c=setup(10,10,2,5,{getterThrow:true});rows=captureCase([c]);check(kinds(rows,10)[0][5]&4,"unavailable list range explicit");
  c=setup(0,0,0,-1);rows=captureCase([c]);check((kinds(rows,10)[0][5]&33)===33 && indices(rows).length===0,"empty range complete and explicitly empty");
  traversal=kinds(rows,11)[0];check((traversal[5]&133)===133 && !(traversal[5]&2) && traversal[6]===0 && traversal[7]===-1 && traversal[8]===-1,"empty store is not a reached newest entry");
  var left=setup(200,200,100,109),right=setup(200,200,150,159);rows=captureCase([left,right]);var projected=kinds(rows,9);check(projected.slice(0,20).every(function(r){return r[5]&128;}) && projected.slice(20).every(function(r){return r[5]&256;}),"all list viewports precede any margins");
}
