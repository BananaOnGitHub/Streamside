var Wrapped=installEntry("native"),clients=[],states=[],stores=[],subscriptions=0,unsubscribed=0;
for(var i=0;i<5;i++){
 var cl=new Client(),state={_tmiClient:cl,lines:[]};clients.push(cl);states.push(state);
 var st={getState:(function(value){return function(){return value;};})(state),subscribe:function(){subscriptions++;return function(){unsubscribed++;};}};stores.push(st);
 advance(2000);render(Wrapped,{chatStore:st},"list"+i);
}
same(subscriptions,5,"stores admitted beyond first four");same(unsubscribed,1,"four-store eviction");
var before=packets.length;clients[0].emitLine({id:"evicted"},9);same(packets.length,before,"evicted client silent");
for(var j=0;j<3000;j++){
 advance(1000);var line={id:"secret-"+j,clientNonce:"nonce-"+j};states[4].lines=[{line:line}];
 same(clients[4].emitLine(line,55),55,"long-running original return");if(j%10===0)tick(2000);
}
check(packets.length>2048,"continues after former lifetime budget");
check(packets.some(function(v){return v[0]===2 && v[1]===5 && v[2]>256;}),"labels rotate instead of exhausting");
advance(2000);clients[4].emitLine({id:"late-target",isUnpublished:true},1);
check(packets.some(function(v){return v[0]===2 && v[1]===5 && v[2]===3001;}),"late own message");
advance(2000);before=packets.length;
for(var k=0;k<2000;k++)clients[4].emitLine({id:"burst"+k},1);
check(packets.slice(before).filter(function(v){return v[0]!==21;}).length<=32,"regular burst rate bound");
check(packets.slice(before).filter(function(v){return v[0]===21;}).length<=16,"target burst rate bound");
tick(600000);check(packets.some(function(v){return v[0]===16 && v[4]>0;}),"suppression explicit");
unmount("list4");advance(600000);render(Wrapped,{chatStore:stores[4]},"reopened");clients[4].emitLine({id:"after-reopen",isUnpublished:true},1);
check(packets.some(function(v){return v[0]===13 && v[1]===5 && v[8]===2 && v[4]===1;}),"late reopen cycle");
check(JSON.stringify(packets).indexOf("secret")===-1,"privacy under long run");
var foreign=function(){return 789;};Client.prototype.emitLine=foreign;tick(2000);same(clients[4].emitLine(),789,"foreign hook remains owned by its installer");
check(packets.some(function(v){return v[0]===12 && v[5]===1;}),"hook ownership refreshed");
states[4].lines=[];for(var full=0;full<2000;full++)states[4].lines.push({line:{id:"large"+full}});
before=packets.length;tick(2000);tick(2000);
check(packets.slice(before).some(function(v){return v[0]===16;}),"coverage lane survives full snapshot scans");
