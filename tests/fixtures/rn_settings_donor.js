/* Dependencies for unchanged donor factory 4884 / component 22114.
 * Run this after loading the settings factory, before the owned installer.
 * The donor constructs the sheet, page children, test IDs and scroll props. */
React.__esModule=true;React.default=React;
RN.StyleSheet={create:function(x){return x;}};
var donorMemo={c:function(n){return React.useRef(Array(n).fill(Symbol.for('react.memo_cache_sentinel'))).current;}};
var donorIntl={defineMessages:function(x){return x;},useIntl:function(){return {formatMessage:function(x){return x.defaultMessage||x.id||'label';}};}};
function settingsRequire(id){
 if(id===1)return function(x){return x&&x.__esModule?x:{default:x};};
 if(id===17)return function(x){return x;};
 if(id===4881)return {USERNAME_COLOR_OPTIONS:[]};
 if(id===519)return donorMemo;
 if(id===517)return {usePlatformOrNull:function(){return null;}};
 if(id===1838)return donorIntl;
 if(id===2118)return {BottomSheet:'native-bottom-sheet',useTheme:function(){return theme;}};
 return env.__r(id)||{};
}
buildLocalEcho(_runtimeGlobal,settingsRequire,null,null,{exports:settings},settings,[1,17,72,5,245,2118,1838,519,517,4881,4630,4882,4902,2132,4901]);
_runtimeGlobal.exerciseDonorSettings=function(){
 function check(ok,msg){if(!ok)throw new Error(msg);}
 buildLocalEcho('composer');
 [undefined,null,[]].forEach(function(sections,index){
  var closed=0,props={visible:true,channelID:'42',channelLogin:'fixture',settings:{},identity:{},onClose:function(){closed++;}};
  if(index)props.containerSections=sections;
  var wrapped=render(settings.ChatSettingsSheet,props);context=wrapped.props.value;
  var native=wrapped.children[0],key='donor-settings-'+index;
  var sheet=render(native.type,native.props,key),scroll=sheet.props.children;
  var menu=render(scroll.type,scroll.props),children=menu.props.children;
  check(sheet.type==='native-bottom-sheet'&&sheet.props.visible===true,'native sheet retained');
  check(menu.type===RN.ScrollView&&menu.props.testID==='chat-settings-scroll','real donor scroll routed');
  check(children.length===8&&children[0].props.accessibilityRole==='button','reload first on real donor main page');
  check(children[0].children[0].children[0]==='Reload Emotes','real donor reload label');
  check(children[1].props.containerSections===sections&&typeof children[1].props.onRequestClose==='function','optional donor page props preserved');
  check(menu.props.keyboardShouldPersistTaps==='handled','donor scroll behavior retained');
  var count=reloaded.length;children[0].props.onPress();
  check(reloaded.length===count+1&&reloaded[count]==='42'&&closed===1,'real donor reload scope and close');
  // The donor's own state selects the identity subpage; no replica page tree.
  slots.get(key)[1]='identity';sheet=render(native.type,native.props,key);scroll=sheet.props.children;
  menu=render(scroll.type,scroll.props);
  check(menu.props.children.length===7&&!menu.props.children.some(function(child){return child&&child.props&&child.props.testID==='reload';}),'real donor subpage unchanged');
 });
 context=null;
};
