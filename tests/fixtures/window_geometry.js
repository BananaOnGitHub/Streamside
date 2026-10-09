// Ordinary CI: production JS geometry and logical identity through the host
// React facade. The donor Hermes test separately verifies RN's window algorithm.
const p={channelID:'42',emotePickerSID:'geometry',sections:[{id:'channel'}],onSelectEmote:()=>{}};
let gridInstance=null;
function cleanup(key){(slots.get(key)||[]).forEach(s=>{if(s&&s.cleanup)s.cleanup();});slots.delete(key);}
function close(){if(gridInstance)cleanup(gridInstance);cleanup('42/'+p.emotePickerSID);}
function openGrid(width){
 const wrapper=render(trays.EmotePickerTray,p),session=render(wrapper.type,wrapper.props,wrapper.props.key);
 assert.equal(session.type,'provider');context=session.props.value;
 const native={testID:'emote-grid-list',sections:[{key:'recents',data:[]},{key:'channel',data:[]}],renderItem:x=>x.item,renderSectionHeader:x=>x.section};
 const routed=jsx.jsx(RN.SectionList,native,'grid'),adapted=render(routed.type,routed.props);gridInstance=adapted.type;
 let view=render(gridInstance,adapted.props);view.props.onLayout({nativeEvent:{layout:{width,height:625}}});view=render(gridInstance,adapted.props);
 const row=view.props.renderItem({section:view.props.sections[1],item:view.props.sections[1].data[0]});
 assert.equal(row.type,'flat');return row.props;
}
for(const width of baseline.viewport_widths)for(const count of baseline.catalog_sizes){
 close();p.emotePickerSID='geometry/'+width+'/'+count;
 channel=Array.from({length:count},(_,i)=>({...a,id:1000+i}));config={...config,revision:config.revision+1};
 let keys=null;
 for(const reopening of [false,true]){
  if(reopening)close();const fp=openGrid(width);
  assert(fp.horizontal);assert.equal(fp.windowSize,3);assert.equal(fp.style.height,260);
  assert.equal(fp.data.length,Math.ceil(count/5));
  const stride=fp.getItemLayout(null,0).length;
  for(let i=0;i<fp.data.length;i++){
   const cell=fp.getItemLayout(null,i),next=fp.getItemLayout(null,i+1);
   assert.equal(cell.index,i);assert.equal(cell.offset+cell.length,next.offset,'fractional column endpoints must be contiguous');
   assert(Math.abs(cell.length-stride)<1e-8,'fractional visual width preserved');
   assert.deepEqual(fp.data[i].emotes.map(x=>x.id),channel.slice(i*5,i*5+5).map(x=>x.id));
  }
  const observed=fp.data.map(fp.keyExtractor);if(keys)assert.deepEqual(observed,keys);keys=observed;
  const rerender=openGrid(width);assert.deepEqual(rerender.data.map(rerender.keyExtractor),keys);
  const tiles=fp.renderItem({item:fp.data[0]}).children[0],again=rerender.renderItem({item:rerender.data[0]}).children[0];
  assert.deepEqual(tiles.map(t=>t.props.key),again.map(t=>t.props.key));
 }
}
close();
