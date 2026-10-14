/* Execute the real factory's guarded installer: original export survives. */
function check(value) { if (!value) throw new Error("factory fallback changed"); }
var original=null, styleCalls=0, React={memo:function(fn){original=fn;return fn;}};
var modules={1:function(x){return {default:x};},17:{},72:React,5:{StyleSheet:{create:function(x){styleCalls++;return x;}}},245:{jsx:function(){}},4782:{ChatLine:function(){}},3500:{LibraryTmiClient:function(){}}};
_runtimeGlobal.__r=function(id) {
  if(id===16) { if(_refusal) throw new TypeError("fixture-only");return {default:{buildLocalEcho:null}}; }
  return modules[id];
};
for(var mode=0;mode<2;mode++) {
  _runtimeGlobal._refusal=mode===1;var exports={};
  buildLocalEcho(_runtimeGlobal,__r,null,null,{},exports,[1,17,72,5,245,4782,519,2071,1846,3488,517,4897,4898,3487,4899,3458,2085,4900,4901,3864,4904,4905]);
  check(exports.ChatMessageList===original);check(exports.AUTOSCROLL_TRIGGER_ZONE===24 && exports.READER_WINDOW_SIZE===50);
}
check(styleCalls===4);
