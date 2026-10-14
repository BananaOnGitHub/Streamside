var Wrapped=installEntry("native"), clients=[], states=[], subscriptions=0, unsubscribed=0;
for(var i=0;i<3;i++){
 var cl=new Client(),state={_tmiClient:cl,lines:[]};clients.push(cl);states.push(state);
 render(Wrapped,{chatStore:{getState:(function(st){return function(){return st;};})(state),subscribe:function(){subscriptions++;return function(){unsubscribed++;};}}});
}
same(subscriptions,2,"session cap");
for(var j=0;j<2000;j++)clients[0].emitLine({id:"secret-"+j,clientNonce:"nonce-"+j},0);
check(packets.length<=1502,"packet cap");check(packets.every(function(v){return v[2]<=256;}),"label cap");
check(packets.some(function(v){return v[0]===11 && v[4]===2;}),"budget stop");same(unsubscribed,2,"budget teardown");
same(Client.prototype.emitLine,nativeEmit,"budget restores hook");check(JSON.stringify(packets).indexOf("secret")===-1,"privacy under load");
