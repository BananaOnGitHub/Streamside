var global=_runtimeGlobal;
function check(x,m){if(!x)throw new Error(m);}
function trap(o){return new Proxy(o,{set:function(){throw new Error("write");},defineProperty:function(){throw new Error("define");},deleteProperty:function(){throw new Error("delete");}});}
for(var mode=0;mode<8;mode++){
 var raw=new Map();raw.set("totalSize",120);raw.set("stylePaddingTop",1);raw.set("headerSize",2);raw.set("footerSize",3);raw.set("anchoredEndSpaceSize",20);
 var values=trap({get:function(key){return raw.get(key);}}),data=trap([trap({key:"private"})]),positions=trap({0:34}),sizes=new Map();sizes.set("private",30);
 var props=trap({data:data,horizontal:!!(mode&1),rtl:!!(mode&2),contentInset:trap({bottom:5,left:6,right:7}),contentInsetEndAdjustment:2,anchoredEndSpace:!!(mode&4),stylePaddingLeft:3});
 var history=trap([trap({time:Date.now()-30,scroll:1}),trap({time:Date.now()-20,scroll:3}),trap({time:Date.now()-10,scroll:6})]);
 var state=trap({props:props,positions:positions,sizesKnown:sizes,idCache:trap({}),scrollHistory:history,scroll:5,scrollLength:50,totalSize:120,scrollAxisGap:2,contentInsetOverride:mode&4?trap({bottom:12,left:13,right:14}):null});
 var container=trap({state:state,values:values,scrollAxisGap:2});
 var getState=buildLocalEcho(container,state,{I18nManager:{isRTL:false}}),before=JSON.stringify(state),sizeBefore=sizes.size,value=getState();
 check(value.data===data && value.sizes===sizes,"original references");check(value.positionAtIndex(0)===34,"read-only position");check(typeof value.contentLength==="number" && typeof value.scrollVelocity==="number","helpers executed");check(JSON.stringify(state)===before && sizes.size===sizeBefore,"state unmodified");
}
