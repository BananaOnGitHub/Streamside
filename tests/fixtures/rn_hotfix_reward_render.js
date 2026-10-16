/* Owned host adapters exercising the supplied donor reward renderer.
 * No React Native/Fabric layout or live PubSub delivery is simulated.
 */
function check(value, reason) { if (!value) throw new Error(reason); }
function element(type, props, key) { return {type:type, props:props, key:key}; }
var compiledCache=null;
var theme={colors:{textBase:"base",textAlt2:"alt"}},intl={formatMessage:function(){return "notice";}},attachmentShift={};
var modules={
  1:function(value){return {default:value};},
  72:{},
  5:{StyleSheet:{create:function(value){return value;}},View:"View"},
  245:{jsx:element,jsxs:element},
  519:{c:function(size){return compiledCache || (compiledCache=new Array(size));}},
  2071:{useTheme:function(){return theme;},CoreText:"CoreText"},
  1846:{useIntl:function(){return intl;}},
  3478:{useInlineAttachmentCenterShift:function(){return attachmentShift;}},
  4791:{AnimationType:{None:0},getAnimationType:function(){return 1;}},
  3477:{ChatMessageRow:"ChatMessageRow"},
  3480:{EmotePart:"EmotePart"},
  4068:{formatWholeNumber:function(intl, value){return String(value);}},
  2085:{IconBits:"IconBits"},4075:{PointsIcon:"PointsIcon"}
};
var _mapped={};
for(var _i=0;_i<_baselineDependencies.length;_i++) {
 var _old=_baselineDependencies[_i],_new=_rewardDependencies[_i];
 if(_old in modules)_mapped[_new]=modules[_old];
}
modules=_mapped;
_runtimeGlobal.__r=function(id){check(id in modules,"unexpected dependency "+id);return modules[id];};
var exports={};
/* The investigation runner supplies dependencies from the donor registration. */
buildLocalEcho(_runtimeGlobal,__r,null,null,{},exports,_rewardDependencies);
check(typeof exports.ChannelPointsRewardLine==="function","reward export");
function render(body, rewards, deleted) {
  return exports.ChannelPointsRewardLine({
    event:{type:"channelpointsreward",id:"fixture",rewardId:"reward",body:body,
      displayName:"fixture",badges:{},emotes:[],deleted:!!deleted},
    rewardsById:rewards,badgeRegistry:{},pointsName:"points"
  });
}
var known={reward:{name:"fixture reward",cost:100,pricingType:"POINTS"}};
check(render("",undefined)===null,"empty notice without catalog returns null");
check(render("",{})===null,"empty notice with missing reward returns null");
check(render("  ",{})===null,"whitespace notice with missing reward returns null");
var notice=render("",known);
check(notice && notice.type==="View" && notice.props.testID==="chat-channelpointsreward-line","known empty reward renders notice");
var text=render("fixture text",{});
check(text && text.type==="ChatMessageRow" && text.props.message.body==="fixture text","missing reward keeps text message");
var both=render("fixture text",known);
check(both && both.props.testID==="chat-channelpointsreward-line" && both.props.children[1].props.children.type==="ChatMessageRow","known text reward renders notice and message");
check(render("",known,true)===null,"deleted empty reward returns null");
check(render("fixture text",known,true).type==="ChatMessageRow","deleted text reward keeps message renderer");
var stableProps={event:{type:"channelpointsreward",rewardId:"reward",body:"",displayName:"fixture"},badgeRegistry:{},pointsName:"points",rewardsById:{}};
check(exports.ChannelPointsRewardLine(stableProps)===null,"stable notice starts without reward");
stableProps.rewardsById=known;
var restored=exports.ChannelPointsRewardLine(stableProps);
check(restored && restored.props.testID==="chat-channelpointsreward-line","catalog arrival restores stable notice");
check(exports.ChannelPointsRewardLine(stableProps)===restored,"unchanged notice reuses compiled memo output");
stableProps.rewardsById={};
check(exports.ChannelPointsRewardLine(stableProps)===null,"catalog loss hides stable notice again");
