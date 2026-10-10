"""Actual legacy palette probes preserve forwarding, geometry and privacy."""
import unittest
import test_composer_library as library


class LegacyPaletteProbeTests(unittest.TestCase):
    def test_passive_forwarding_snapshots_bounds_and_privacy(self):
        harness = '#define TAS_IMAGE_DEMAND_DIAGNOSTIC 1\n' + library.HARNESS
        harness = harness.replace('id flow,collection,', 'id visible; id flow,collection,')
        harness = harness.replace('else assert(!"unexpected library selector");', 'else { fprintf(stderr,"unexpected: %s\\n",sel);assert(!"unexpected library selector"); }')
        harness = harness.replace('else if(!strcmp(sel,"visibleCells"))result=&empty;',
            'else if(!strcmp(sel,"visibleCells"))result=o->visible ? o->visible : &empty;\n'
            '    else if(!strcmp(sel,"indexPathForCell:"))result=va_arg(args,id)->path;')
        harness = harness.replace('result=o->children[i]; }',
            'result=o->cls && !strcmp(o->cls,"LargeArray") ? o->children[0] : o->children[i]; }')
        harness = harness.replace('int main(void) {', r'''
static id probe_expected_self,probe_expected_content,probe_expected_path,probe_result;
static unsigned probe_forwarded;
static id probe_native_cell(id self,SEL sel,id content,id path) {
    assert(self==probe_expected_self && content==probe_expected_content && path==probe_expected_path);
    assert(!strcmp(sel,"collectionView:cellForItemAtIndexPath:"));probe_forwarded++;return probe_result;
}
int main(void) {''')
        case = r'''
    /* The diagnostic build also runs every baseline geometry assertion above. */
    __atomic_store_n(&palette_probe_count,0,__ATOMIC_RELEASE);
    palette_probe_refused=palette_probe_queries=palette_probe_scans_limited=0;
    palette_probe_created_zero=palette_probe_created_other=palette_probe_created_nil=0;
    s.recent_menu_open=YES;s.recent_content=&native;native.host=&delegate;palette_probe_open(&s);
    native.text="PRIVATE-SENTINEL";native.sections=2;native.item_counts[0]=3;
    native.adjusted.top=48;native.bounds=(Rect){{0,-48},{390,250}};
    struct Fake zero_path={.cls="NSIndexPath",.section=0},other_path={.cls="NSIndexPath",.section=1};
    struct Fake zero_cell={.cls="UICollectionViewCell",.text="PRIVATE-SENTINEL",.path=&zero_path,.frame={{0,52},{56,56}}};
    struct Fake other_cell={.cls="UICollectionViewCell",.path=&other_path,.frame={{0,900},{56,56}},.hidden=YES};
    struct Fake visible={.cls="NSArray",.count=2,.children={&zero_cell,&other_cell}};native.visible=&visible;
    struct Fake zero_attr={.cls="UICollectionViewLayoutAttributes",.path=&zero_path};
    struct Fake other_attr={.cls="UICollectionViewLayoutAttributes",.path=&other_path};
    struct Fake native_attrs={.cls="NSArray",.count=2,.children={&zero_attr,&other_attr}};
    struct Fake returned_attrs={.cls="NSArray",.count=1,.children={&other_attr}};
    Rect requested={{0,-48},{390,250}},query={{0,-48},{390,100}};
    palette_probe_query(&s,requested,query,&native_attrs,&returned_attrs);
    assert(native_attrs.count==2 && returned_attrs.count==1 && zero_attr.path==&zero_path);
    original_palette_probe_cell=(IMP)probe_native_cell;probe_expected_self=&native;
    probe_expected_content=&native;probe_expected_path=&zero_path;probe_result=&zero_cell;
    assert(palette_probe_cell(&native,"collectionView:cellForItemAtIndexPath:",&native,&zero_path)==&zero_cell);
    probe_result=nil;
    assert(!palette_probe_cell(&native,"collectionView:cellForItemAtIndexPath:",&native,&zero_path));
    probe_expected_path=&other_path;probe_result=&other_cell;
    assert(palette_probe_cell(&native,"collectionView:cellForItemAtIndexPath:",&native,&other_path)==&other_cell);
    native.host=nil;probe_expected_path=&zero_path;probe_result=&zero_cell;
    assert(palette_probe_cell(&native,"collectionView:cellForItemAtIndexPath:",&native,&zero_path)==&zero_cell);
    native.host=&delegate;assert(probe_forwarded==4 && palette_probe_created_zero==2 && palette_probe_created_other==1 && palette_probe_created_nil==1);
    U reloads=native.reloads,invalidations=metric_invalidations,reads=queries;
    Point offset=native.offset;
    palette_probe_snapshot(&s,&native,2);palette_probe_snapshot(&s,&native,2);
    assert(palette_probe_count==1);
    PaletteProbeSnapshot v=palette_probe_records[0];
    assert(v.visible==2 && v.visible_zero==1 && v.visible_hidden==1 && v.intersecting==1 && v.zero_items==3);
    assert(v.palette && v.delegate_self && v.source_self);
    assert(v.original==2 && v.original_zero==1 && v.returned==1 && !v.returned_zero);
    assert(v.created_zero==2 && v.created_other==1 && v.created_nil==1);
    char report[4096];ss_legacy_palette_status(report,sizeof(report));
    assert(strstr(report,"palette stage=2") && strstr(report,"attrs(total/section0)=2/1=>1/0"));
    assert(!strstr(report,"PRIVATE-SENTINEL"));
    native.visible=&empty;native.item_counts[0]=0;
    assert(palette_probe_records[0].zero_items==3 && palette_probe_records[0].visible==2); /* immutable published observations */
    assert(native.reloads==reloads && metric_invalidations==invalidations && queries==reads && !memcmp(&offset,&native.offset,sizeof(offset)));
    /* Large collections bound getter work; later records cannot overwrite the prefix. */
    visible.cls="LargeArray";visible.count=129;visible.children[0]=&zero_cell;native.visible=&visible;
    palette_probe_open(&s);palette_probe_snapshot(&s,&native,0);
    assert(palette_probe_records[1].visible==129 && palette_probe_records[1].visible_zero==128 && palette_probe_scans_limited==1);
    for(unsigned i=0;i<16;i++) { palette_probe_open(&s);palette_probe_snapshot(&s,&native,0); }
    assert(palette_probe_count==16 && palette_probe_refused==2 && palette_probe_records[0].visible==2);
    char tiny[3]={'x','x','z'};ss_legacy_palette_status(tiny,2);assert(tiny[1]==0 && tiny[2]=='z');
    ss_legacy_palette_status(NULL,0);
'''
        harness = harness.replace('    return 0;\n}', case+'    return 0;\n}')
        library.LibraryTests().run_library(harness)
