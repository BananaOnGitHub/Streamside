/* Diagnostic-only, bounded scalar observations of the bound legacy palette.
 * No history/model/image values, object addresses or extra layout queries. */
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
#define PALETTE_PROBE_LIMIT 16
#define PALETTE_PROBE_SCAN_LIMIT 128
typedef struct {
    unsigned stage;
    BOOL window,hidden,menu,heading;
    Rect bounds,requested,query;
    double inset,recent,header,gap_start,gap_height;
    I gap_section;
    U sections,zero_items,visible,visible_zero,visible_hidden,intersecting;
    U original,original_zero,returned,returned_zero;
    uint64_t created_zero,created_other,created_nil;
} PaletteProbeSnapshot;
static PaletteProbeSnapshot palette_probe_records[PALETTE_PROBE_LIMIT];
static unsigned palette_probe_count;
static uint64_t palette_probe_refused,palette_probe_queries,palette_probe_scans_limited;
static uint64_t palette_probe_created_zero,palette_probe_created_other,palette_probe_created_nil;
static IMP original_palette_probe_cell;

static void palette_probe_open(State *s) { s->palette_probe_stages=0; }
static void palette_probe_snapshot(State *s,id content,unsigned stage) {
    if (!s || !content || stage>5 || (s->palette_probe_stages&(1U<<stage))) return;
    s->palette_probe_stages|=1U<<stage;
    unsigned index=__atomic_load_n(&palette_probe_count,__ATOMIC_RELAXED);
    if (index>=PALETTE_PROBE_LIMIT) { INC(palette_probe_refused);return; }
    PaletteProbeSnapshot value={0};value.stage=stage;
    value.window=m0(content,"window")!=nil;value.hidden=yes(content,"isHidden");
    value.menu=s->recent_menu_open;value.heading=s->recent_heading_observed;
    value.bounds=rect(content,"bounds");
    Insets inset=((Insets (*)(id,SEL))objc_msgSend)(content,sel_registerName("adjustedContentInset"));
    value.inset=inset.top;value.recent=s->recent_height;value.header=s->recent_header_height;
    value.gap_start=s->library_start;value.gap_height=s->library_height;value.gap_section=s->library_section;
    value.sections=number(content,"numberOfSections");
    if (value.sections) value.zero_items=(U)((I (*)(id,SEL,I))objc_msgSend)(content,sel_registerName("numberOfItemsInSection:"),0);
    id cells=m0(content,"visibleCells");value.visible=number(cells,"count");
    U count=value.visible<PALETTE_PROBE_SCAN_LIMIT ? value.visible : PALETTE_PROBE_SCAN_LIMIT;
    if (count<value.visible) INC(palette_probe_scans_limited);
    for (U i=0;i<count;i++) {
        id cell=at(cells,i),path=m1(content,"indexPathForCell:",cell);
        if (path && !number(path,"section")) value.visible_zero++;
        if (yes(cell,"isHidden")) value.visible_hidden++;
        if (intersects(rect(cell,"frame"),value.bounds)) value.intersecting++;
    }
    value.requested=s->palette_probe_bounds;value.query=s->palette_probe_query;
    value.original=s->palette_probe_original;value.original_zero=s->palette_probe_original_zero;
    value.returned=s->palette_probe_returned;value.returned_zero=s->palette_probe_returned_zero;
    value.created_zero=GET(palette_probe_created_zero);value.created_other=GET(palette_probe_created_other);
    value.created_nil=GET(palette_probe_created_nil);
    /* UIKit callbacks are main-thread writers. Published records are never
     * changed, so a background report can read the acquired prefix safely. */
    palette_probe_records[index]=value;
    __atomic_store_n(&palette_probe_count,index+1,__ATOMIC_RELEASE);
}
static U palette_probe_zero_attributes(id array) {
    U total=number(array,"count"),count=total<PALETTE_PROBE_SCAN_LIMIT ? total : PALETTE_PROBE_SCAN_LIMIT,zero=0;
    if (count<total) INC(palette_probe_scans_limited);
    for (U i=0;i<count;i++) {
        id attributes=at(array,i),path=m0(attributes,"indexPath");
        if (path && !number(path,"section") && !m0(attributes,"representedElementKind")) zero++;
    }
    return zero;
}
static void palette_probe_query(State *s,Rect bounds,Rect query,id original,id returned) {
    if (!s) return;
    INC(palette_probe_queries);
    s->palette_probe_bounds=bounds;s->palette_probe_query=query;
    s->palette_probe_original=number(original,"count");s->palette_probe_returned=number(returned,"count");
    s->palette_probe_original_zero=palette_probe_zero_attributes(original);
    s->palette_probe_returned_zero=palette_probe_zero_attributes(returned);
}
static void palette_probe_scroll(State *s,id content,BOOL after) {
    if (!s || !content || !s->recent_menu_open || s->placing_recents || s->placing_library || s->palette_layout_settling) return;
    Insets inset=((Insets (*)(id,SEL))objc_msgSend)(content,sel_registerName("adjustedContentInset"));
    if (rect(content,"bounds").origin.y>-inset.top+1) palette_probe_snapshot(s,content,after ? 4 : 3);
    else if (s->palette_probe_stages&(1U<<3)) palette_probe_snapshot(s,content,5);
}
static id palette_probe_cell(id self,SEL sel,id content,id path) {
    id result=((id (*)(id,SEL,id,id))original_palette_probe_cell)(self,sel,content,path);
    if (objc_getAssociatedObject(content,&recent_host_key)) {
        if (path && !number(path,"section")) INC(palette_probe_created_zero);else INC(palette_probe_created_other);
        if (!result) INC(palette_probe_created_nil);
    }
    return result;
}
void ss_legacy_palette_status(char *buffer,size_t capacity) {
    if (!buffer || !capacity) return;
    unsigned count=__atomic_load_n(&palette_probe_count,__ATOMIC_ACQUIRE);
    if (count>PALETTE_PROBE_LIMIT) count=PALETTE_PROBE_LIMIT;
    snprintf(buffer,capacity,"\nLegacy palette trace (passive; this launch)\n"
        "Cell callback hook: %s; created section0/other/nil: %llu/%llu/%llu\n"
        "Queries/snapshots/refused/scan limits: %llu/%u/%llu/%llu (limits 16 snapshots, 128 cells/attributes per observation)\n"
        "Stages: 0=bind 1=first layout 2=settled 3=before first scroll 4=after first scroll 5=returned to top. Section0 is an index, not proof of Recent.\n",
        original_palette_probe_cell ? "installed":"missing",(unsigned long long)GET(palette_probe_created_zero),
        (unsigned long long)GET(palette_probe_created_other),(unsigned long long)GET(palette_probe_created_nil),
        (unsigned long long)GET(palette_probe_queries),count,(unsigned long long)GET(palette_probe_refused),(unsigned long long)GET(palette_probe_scans_limited));
    for (unsigned i=0;i<count;i++) {
        PaletteProbeSnapshot v=palette_probe_records[i];size_t used=strlen(buffer);
        if (used>=capacity-1) break;
        snprintf(buffer+used,capacity-used,
            "palette stage=%u window/hidden/menu/heading=%d/%d/%d/%d bounds(y/w/h)=%.1f/%.1f/%.1f inset/recent/header=%.1f/%.1f/%.1f gap(section/y/h)=%ld/%.1f/%.1f sections/items0=%lu/%lu visible/section0/hidden/intersect=%lu/%lu/%lu/%lu created0/other/nil=%llu/%llu/%llu attrs(total/section0)=%lu/%lu=>%lu/%lu rect(y/h)=%.1f/%.1f=>%.1f/%.1f\n",
            v.stage,v.window,v.hidden,v.menu,v.heading,v.bounds.origin.y,v.bounds.size.width,v.bounds.size.height,
            v.inset,v.recent,v.header,v.gap_section,v.gap_start,v.gap_height,v.sections,v.zero_items,
            v.visible,v.visible_zero,v.visible_hidden,v.intersecting,(unsigned long long)v.created_zero,
            (unsigned long long)v.created_other,(unsigned long long)v.created_nil,v.original,v.original_zero,v.returned,v.returned_zero,
            v.requested.origin.y,v.requested.size.height,v.query.origin.y,v.query.size.height);
    }
}
#else
static void palette_probe_open(State *s) { (void)s; }
static void palette_probe_snapshot(State *s,id content,unsigned stage) { (void)s;(void)content;(void)stage; }
static void palette_probe_query(State *s,Rect bounds,Rect query,id original,id returned) { (void)s;(void)bounds;(void)query;(void)original;(void)returned; }
static void palette_probe_scroll(State *s,id content,BOOL after) { (void)s;(void)content;(void)after; }
void ss_legacy_palette_status(char *buffer,size_t capacity) { if (buffer && capacity) buffer[0]=0; }
#endif
