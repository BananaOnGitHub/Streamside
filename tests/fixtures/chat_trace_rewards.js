/* Host lifecycle adapters; optionally executes the unchanged donor reward leaf.
 * Native cells, stores and delivery are mocks, not live Fabric/PubSub evidence. */
React.isValidElement=function(value){return !!(value && value.type && value.props);};
function store(client){var listener=null,value={state:{_tmiClient:client,lines:[],connected:true}};
  value.getState=function(){return value.state;};value.subscribe=function(fn){listener=fn;return function(){listener=null;};};value.notify=function(){if(listener)listener();};return value;
}
var rendererFailure=null,rewardModule={ChannelPointsRewardLine:function(p){
  if(rendererFailure)throw rendererFailure;
  if(!p.rewardsById || !p.rewardsById[p.event.rewardId])return p.event.body.trim()?element("ChatMessageRow",{message:p.event}):null;
  return element("View",{testID:"chat-channelpointsreward-line"});
}};
if(typeof _rewardFactory!=="undefined"){
  var compiledCache=null,theme={colors:{textBase:"base",textAlt2:"alt"}},intl={formatMessage:function(){return "notice";}},attachmentShift={};
  Object.assign(modules,{519:{c:function(size){return compiledCache || (compiledCache=new Array(size));}},
    2071:{useTheme:function(){return theme;},CoreText:"CoreText"},1846:{useIntl:function(){return intl;}},
    3478:{useInlineAttachmentCenterShift:function(){return attachmentShift;}},4791:{AnimationType:{None:0},getAnimationType:function(){return 1;}},
    3477:{ChatMessageRow:"ChatMessageRow"},3480:{EmotePart:"EmotePart"},4068:{formatWholeNumber:function(i,v){return String(v);}},2085:{IconBits:"IconBits"},4075:{PointsIcon:"PointsIcon"}});
  RN.View="View";_rewardFactory(_runtimeGlobal,__r,null,null,{},rewardModule,[1,72,5,245,3480,4068,519,2071,1846,3478,4791,3477,3487,2085,4075]);
}
modules[4790]=rewardModule;
var accepted=true,emitFailure=null;
Client.prototype.emitLine=function(line,extra){if(emitFailure)throw emitFailure;if(accepted)this.store.state.lines.push({key:line.id,line:line});return extra;};
Client.prototype.onChannelPointsRewardEvent=function(event,extra){var line=this.translateChatMessage(event,false);return this.emitLine(Object.assign({},line,{type:"channelpointsreward"}),extra);};
var client=new Client(),sa=store(client);client.store=sa;
var pushFailure=null,pushCalls=[],nativePush=function(line,extra){pushCalls.push([this,line,extra]);if(pushFailure)throw pushFailure;if(accepted)sa.state.lines.push({key:line.id,line:line});return extra;};
Object.defineProperty(sa.state,"pushRewardRedemption",{value:nativePush,writable:true,enumerable:false,configurable:false});
if(typeof _chatFactory!=="undefined"){
  var exports={};buildLocalEcho(_runtimeGlobal,__r,null,null,{},exports,[1,17,72,5,245,4782,519,2071,1846,3488,517,4897,4898,3487,4899,3458,2085,4900,4901,3864,4904,4905]);
  installEntry=function(){return exports.ChatMessageList;};
}
var Wrapped=installEntry("original"),out=render(Wrapped,{chatStore:sa});context=out.props.value;
var descriptor=Object.getOwnPropertyDescriptor(sa.state,"pushRewardRedemption");check(!descriptor.enumerable && !descriptor.configurable && descriptor.writable,"store descriptor preserved");
var irc={id:"secret-irc",rewardId:"secret-reward",body:"",type:"channelpointsreward",emotes:[],displayName:"secret-name"};
advance(2000);same(client.onChannelPointsRewardEvent({line:irc},42),42,"IRC return");
var ircLabel=packets.filter(function(v){return v[0]===17 && v[4]===1 && v[5]===1;})[0][2];
check(ircLabel>0 && packets.some(function(v){return v[0]===17 && v[2]===ircLabel && v[4]===1 && v[5]===2;}),"IRC correlated route");
var pub={id:"secret-pub",rewardId:"secret-reward",body:"",type:"channelpointsreward",emotes:[],displayName:"secret-name"};
advance(2000);same(sa.state.pushRewardRedemption(pub,77),77,"PubSub return");same(pushCalls[0][0],sa.state,"store this");same(pushCalls[0][1],pub,"store argument identity");same(pushCalls[0][2],77,"store extra argument");
var pubLabel=packets.filter(function(v){return v[0]===17 && v[4]===2 && v[5]===1;})[0][2];check(pubLabel>0 && pubLabel!==ircLabel,"separate anonymous routes");
check(packets.some(function(v){return v[0]===21 && v[2]===pubLabel && v[4]===2;}),"store present");
context=render(lines.ChatLine,{chatStore:sa,line:pub}).props.value;
var rewardProps={event:pub,rewardsById:{},badgeRegistry:{},pointsName:"points"};
same(render(rewardModule.ChannelPointsRewardLine,rewardProps,"reward"),null,"missing catalog null unchanged");
check(packets.some(function(v){return v[0]===18 && v[2]===pubLabel && v[4]===1 && v[5]===1 && v[6]===1;}),"missing catalog null observed");
advance(2000);rewardProps.rewardsById={"secret-reward":{name:"secret-reward-name",cost:100,pricingType:"POINTS"}};
check(render(rewardModule.ChannelPointsRewardLine,rewardProps,"reward")!==null,"catalog arrival renders");
check(packets.some(function(v){return v[0]===18 && v[2]===pubLabel && v[4]===2 && v[5]===2;}),"catalog available element observed");
advance(2000);rewardProps.rewardsById={};same(render(rewardModule.ChannelPointsRewardLine,rewardProps,"reward"),null,"catalog loss returns null again");
context=out.props.value;
var nativeProps={testID:"chat-message-list",data:sa.state.lines,recycleItems:false,estimatedItemSize:36,renderItem:function(item){return item;}};
var listElement=jsx.jsx("native-list",nativeProps),list=render(listElement.type,listElement.props,"list");
same(list.type,"native-list","no extra native view");same(list.props.recycleItems,false,"recycling preserved");same(list.props.estimatedItemSize,36,"estimate preserved");
var deferred=null,defer=false,cells=[{measureInWindow:function(cb){cb(0,100,400,40);}},{measureInWindow:function(cb){if(defer)deferred=cb;else cb(0,140,400,60);}}];
var knownSizes=new Map([[irc.id,40],[pub.id,60]]),state={data:sa.state.lines,sizes:knownSizes,positionAtIndex:function(i){return i?40:0;},elementAtIndex:function(i){return cells[i];}};
var ref={getState:function(){return state;},getNativeScrollRef:function(){return {measureInWindow:function(cb){cb(0,100,400,200);}};}};list.props.ref(ref);tick(2000);
check(packets.some(function(v){return v[0]===22 && v[4]===1 && v[5]===1 && v[6]===1 && v[7]===1;}),"four target hooks admitted");
check(packets.some(function(v){return v[0]===19 && v[2]===pubLabel && v[4]===60 && v[5]===40 && v[6]===1;}),"null reward known list space");
check(packets.some(function(v){return v[0]===20 && v[2]===pubLabel && v[5]===140 && v[7]===60;}),"null reward native cell measured");
defer=true;tick(2000);check(typeof deferred==="function","deferred cell measurement");cells[1]={measureInWindow:function(cb){cb(0,140,400,0);}};
var before=packets.length;deferred(0,140,400,60);same(packets.length,before,"recycled cell rejected");
knownSizes.delete(pub.id);tick(2000);
check(packets.some(function(v){return v[0]===19 && v[2]===pubLabel && v[4]===-1 && v[6]===0;}),"unknown size not estimate");
check(packets.some(function(v){return v[0]===20 && v[2]===pubLabel && v[7]===0;}),"zero native cell is measured");
accepted=false;advance(2000);var blocked={id:"secret-blocked",type:"channelpointsreward",body:"",rewardId:"secret-reward"};sa.state.pushRewardRedemption(blocked,8);
var blockedLabel=packets.filter(function(v){return v[0]===17 && v[4]===2 && v[5]===1;}).slice(-1)[0][2];
check(packets.some(function(v){return v[0]===21 && v[2]===blockedLabel && v[4]===1;}),"full live-alias absence observed");
advance(2000);sa.state.lines.push({key:blocked.id,line:blocked});sa.notify();
check(packets.some(function(v){return v[0]===21 && v[2]===blockedLabel && v[4]===2;}),"later store arrival same label");
accepted=true;advance(2000);var own={id:"secret-own",clientNonce:"secret-nonce",isUnpublished:true,body:"secret-body"};client.translateChatMessage({line:own,sentByCurrentUser:true});client.emitLine(own,1);
var ownLabel=packets.filter(function(v){return v[0]===1 && (v[3]&1);}).slice(-1)[0][2];
check([1,2,3,21].every(function(e){return packets.some(function(v){return v[0]===e && v[2]===ownLabel && (v[3]&1);});}),"own lifecycle preserved independently");
advance(2000);var ack={id:"secret-ack",clientNonce:"secret-nonce",body:"secret-body"};client.translateChatMessage({line:ack});client.emitLine(ack,1);
check(packets.filter(function(v){return v[0]===2;}).slice(-1)[0][2]===ownLabel,"own nonce reconciliation preserved");
advance(2000);pushFailure=new RangeError("secret-error");try{sa.state.pushRewardRedemption(pub);throw "not thrown";}catch(e){same(e,pushFailure,"PubSub error identity");}pushFailure=null;
check(packets.some(function(v){return v[0]===17 && v[4]===2 && v[5]===3 && v[7]===2;}),"PubSub failure");
advance(2000);emitFailure=new TypeError("secret-error");try{client.onChannelPointsRewardEvent({line:irc});throw "not thrown";}catch(e){same(e,emitFailure,"IRC error identity");}emitFailure=null;
check(packets.some(function(v){return v[0]===17 && v[4]===1 && v[5]===3 && v[7]===1;}),"IRC failure");
if(typeof _rewardFactory==="undefined"){advance(2000);context=render(lines.ChatLine,{chatStore:sa,line:pub}).props.value;rendererFailure=new TypeError("secret-error");try{render(rewardModule.ChannelPointsRewardLine,rewardProps,"reward");throw "not thrown";}catch(e){same(e,rendererFailure,"renderer error identity");}rendererFailure=null;check(packets.some(function(v){return v[0]===18 && v[5]===3 && v[7]===1;}),"renderer exception not null");}
if(typeof _diagnosticReport==="function"){var report=_diagnosticReport();check(report.indexOf("route=2")>=0 && report.indexOf("catalog=1 render=1")>=0 && report.indexOf("cell=measured")>=0,"native target report");check(report.indexOf("secret")===-1,"report privacy");}
/* Evict every alias/object entry while retaining the original target record.
 * A missing association is unknown, never asserted as a missing message. */
for(var churn=0;churn<600;churn++)render(lines.ChatLine,{chatStore:sa,line:{id:"secret-churn"+churn}},"churn");
tick(2000);check(packets.some(function(v){return v[0]===21 && v[2]===pubLabel && v[4]===3;}),"expired target identity is unknown");
check(JSON.stringify(packets).indexOf("secret")===-1,"numeric packet privacy");
unmount(Wrapped);same(sa.state.pushRewardRedemption,nativePush,"store method restored");
render(Wrapped,{chatStore:sa});var foreign=function(){return 99;};sa.state.pushRewardRedemption=foreign;tick(2000);unmount(Wrapped);same(sa.state.pushRewardRedemption,foreign,"foreign replacement retained");
