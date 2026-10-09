/* Actual compiled owned LibraryGrid geometry through Twitch's donor algorithm.
 * React lifecycle is a host facade; no Fabric/native mount-count claim. */
function check(ok,message) { if (!ok) throw new Error(message); }
check(typeof buildLocalEcho('composer') === 'function', 'owned installer');
var alg = _runtimeGlobal._windowAlgorithms;
var demoProps = {data:Array.from({length:168},function (_,i) { return i; }),getItemCount:function (d) { return d.length; }};
var oldMetric = {getCellMetricsApprox:function (i) { return {index:i,offset:i*(370/6),length:370/6}; }};
var oldOverlap = alg.elementsThatOverlapOffsets([0,0,370,740],demoProps,oldMetric,1);
check(oldOverlap[3] === undefined, 'original fractional layout reproduces missing overscan endpoint');
var oldRange = {first:0,last:6};
for (var n=0;n<20;n++) {
  var next = alg.computeWindowedRenderLimits(demoProps,7,3,oldRange,oldMetric,{visibleLength:370,offset:0,velocity:0,zoomScale:1});
  check(next.last === Math.min(167,oldRange.last+7), 'original repeated batch expansion');
  oldRange = next;
}
check(oldRange.last > 120, 'old stationary window expands far beyond viewport');
var p = {channelID:'42',emotePickerSID:'window',sections:[{id:'channel'}],onSelectEmote:function () {}};
function cleanup(key) { (slots.get(key)||[]).forEach(function (s) { if (s&&s.cleanup) s.cleanup(); });slots.delete(key); }
function open() {
  var wrapper=render(trays.EmotePickerTray,p),session=render(wrapper.type,wrapper.props,wrapper.props.key);
  check(session.type==='provider','provider library');context=session.props.value;
}
function grid() {
  var native={testID:'emote-grid-list',sections:[{key:'recents',data:[]},{key:'channel',data:[]}],renderItem:function (x) { return x.item; },renderSectionHeader:function (x) { return x.section; }};
  var routed=jsx.jsx(RN.SectionList,native,'grid'),adapted=render(routed.type,routed.props);
  return render(adapted.type,adapted.props);
}
function flat(view) {
  var row=view.props.renderItem({section:view.props.sections[1],item:view.props.sections[1].data[0]});
  return typeof row.type === 'function' ? render(row.type,row.props,'window-columns') : row;
}
var widths=[320,360,370,375,390,393,402,414,430,768,834,1024],sizes=[1,24,124,838,1001,5000];
for (var w=0;w<widths.length;w++) for (var catalogCase=0;catalogCase<sizes.length;catalogCase++) {
  cleanup('42/'+p.emotePickerSID);p.emotePickerSID='window-'+w+'-'+catalogCase;
  channel=Array.from({length:sizes[catalogCase]},function (_,i) { return Object.assign({},a,{id:1000+i}); });
  config=Object.assign({},config,{revision:config.revision+1});open();
  var view=grid();view.props.onLayout({nativeEvent:{layout:{width:widths[w],height:625}}});view=grid();
  var row=flat(view),fp=row.props,props=Object.assign({},fp,{getItemCount:function (d) { return d.length; }});
  check(fp.horizontal && fp.windowSize===3 && fp.style.height===260,'five-row configuration preserved');
  var count=fp.data.length,stride=fp.getItemLayout(null,0).length;
  check(count===Math.ceil(sizes[catalogCase]/5),'five-row item mapping');
  for (var i=0;i<count;i++) {
    var item=fp.getItemLayout(null,i),end=fp.getItemLayout(null,i+1).offset;
    check(item.offset+item.length===end,'no holes at adjacent column boundaries');
    check(Math.abs(item.length-stride)<1e-8,'fractional visual width preserved');
  }
  var keys=fp.data.map(fp.keyExtractor),again=flat(grid());
  check(JSON.stringify(keys)===JSON.stringify(again.props.data.map(again.props.keyExtractor)),'logical column keys stable on rerender');
  var firstTiles=fp.renderItem({item:fp.data[0]}).children[0],againTiles=again.props.renderItem({item:again.props.data[0]}).children[0];
  check(JSON.stringify(firstTiles.map(function (t) { return t.props.key; }))===JSON.stringify(againTiles.map(function (t) { return t.props.key; })),'tile keys stable on rerender');
  var metric={getCellMetricsApprox:function (i,actual) { check(actual===props,'algorithm props identity');return fp.getItemLayout(actual.data,i); }};
  for (var flag=0;flag<2;flag++) {
    _runtimeGlobal._windowFeature=!!flag;
    var previous={first:0,last:Math.min(count-1,fp.initialNumToRender-1)};
    var extent=Math.max(0,count*stride-widths[w]);
    var offsets=[0,0,0,stride,widths[w]/2,widths[w],extent/3,extent,extent/2,0,0];
    for (var move=0;move<offsets.length;move++) {
      var offset=Math.min(extent,offsets[move]),velocity=move===7?10:move===8?-10:0;
      var range=alg.computeWindowedRenderLimits(props,fp.maxToRenderPerBatch,fp.windowSize,previous,metric,{visibleLength:widths[w],offset:offset,velocity:velocity,zoomScale:1});
      var visible=alg.elementsThatOverlapOffsets([offset,offset+widths[w]],props,metric,1);
      check(range.first>=0 && range.last<count,'range in bounds');
      check(range.last-range.first+1<=Math.ceil(3*widths[w]/stride)+2,'window bounded to viewport and overscan');
      check(visible[0]===undefined || range.first<=visible[0],'first visible column included');
      check(visible[1]===undefined || range.last>=visible[1],'last visible column included');
      for (var column=visible[0]===undefined?range.first:visible[0];column<=Math.min(range.last,visible[1]===undefined?range.last:visible[1]);column++) {
        var rendered=fp.renderItem({item:fp.data[column]}).children[0],logical=fp.data[column].emotes;
        check(rendered.length===logical.length,'every visible item gets an image element');
        for (var tileIndex=0;tileIndex<logical.length;tileIndex++) {
          var image=rendered[tileIndex].children[0],ip=image.props.data||image.props;
          check(rendered[tileIndex].props.key===logical[tileIndex].id && ip.source.uri===logical[tileIndex].url && ip.resizeMode==='contain','visible identity/source/proportions preserved');
        }
      }
      previous=range;
    }
  }
  // Closing/reopening uses the same layout and stable logical identities.
  cleanup('window-columns');cleanup('42/'+p.emotePickerSID);open();var reopened=flat(grid());
  // Grid layout state is retained by the host facade; new native layout events
  // on an actual reopened surface remain a device validation requirement.
  check(JSON.stringify(keys)===JSON.stringify(reopened.props.data.map(reopened.props.keyExtractor)),'reopen logical identities');
}
