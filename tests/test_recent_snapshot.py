"""Recent history is persisted immediately; its visible row loads on opening."""
import os
import shutil
import unittest
import test_composer


HARNESS = test_composer.RECENT_ACTIONS.split('int main(void) {')[0]
HARNESS = HARNESS.replace('BOOL hidden;', 'BOOL hidden; id window;')
HARNESS = HARNESS.replace('objects[96]', 'objects[4096]').replace('object_count<96', 'object_count<4096')
HARNESS = HARNESS.replace('static State *current;', '''static State *current;
static id saved_history,metadata_a,metadata_b;
static unsigned history_reads,history_writes;
id tas_emotes_named_copy(id room,id name) {
    (void)room;
    if(!strcmp(name->text,"First"))return metadata_a;
    if(!strcmp(name->text,"Second"))return metadata_b;
    return nil;
}
''')
HARNESS = HARNESS.replace('else if(!strcmp(sel,"count"))', '''else if(!strcmp(sel,"window"))result=o->window;
    else if(!strcmp(sel,"new"))result=fresh(o->cls);
    else if(!strcmp(sel,"standardUserDefaults"))result=o;
    else if(!strcmp(sel,"arrayForKey:")) {
        assert(!strcmp(va_arg(args,id)->text,RECENTS_KEY));history_reads++;result=saved_history;
    } else if(!strcmp(sel,"setObject:forKey:")) {
        saved_history=va_arg(args,id);assert(!strcmp(va_arg(args,id)->text,RECENTS_KEY));history_writes++;
    } else if(!strcmp(sel,"mutableCopy")) { result=fresh("NSMutableArray");*result=*o; }
    else if(!strcmp(sel,"removeObject:")) {
        id name=va_arg(args,id);for(U i=0;i<o->count;i++)if(o->children[i]==name) {
            memmove(o->children+i,o->children+i+1,(o->count-i-1)*sizeof(id));o->count--;break;
        }
    } else if(!strcmp(sel,"insertObject:atIndex:")) {
        id item=va_arg(args,id);U i=va_arg(args,U);assert(i<=o->count && o->count<4);
        memmove(o->children+i+1,o->children+i,(o->count-i)*sizeof(id));o->children[i]=item;o->count++;
    } else if(!strcmp(sel,"addObject:")) { assert(o->count<4);o->children[o->count++]=va_arg(args,id); }
    else if(!strcmp(sel,"isEqual:")) {
        id other=va_arg(args,id);BOOL same=other && o->count==other->count;
        for(U i=0;same && i<o->count;i++)same=o->children[i]==other->children[i];result=(id)(uintptr_t)same;
    } else if(!strcmp(sel,"count"))''')
HARNESS += r'''
int main(void) {
    struct Fake name_a={.cls="NSString",.text="First"},name_b={.cls="NSString",.text="Second"};
    struct Fake emote_a={.cls="NSDictionary",.tint=&name_a},emote_b={.cls="NSDictionary",.tint=&name_b};
    metadata_a=&emote_a;metadata_b=&emote_b;
    struct Fake history={.cls="NSArray",.count=2,.children={&name_a,&name_b}};
    saved_history=&history;
    struct Fake row={.cls="UIScrollView"},delegate={.cls="SSComposerDelegate"};
    struct Fake window={.cls="UIWindow"},container={.cls="UIView",.window=&window,.parent=&window};
    window.window=&window;
    State s={.recent_strip=&row};delegate.context=&s;current=&s;delegate_class=objc_getClass("SSComposerDelegate");
    original_collection_layout=(IMP)native_layout;
    /* Closed or hidden ancestors never load history. */
    container.hidden=YES;refresh_recents(&delegate,visible_in_window(&container));assert(!history_reads && !s.recent_menu_open);
    container.hidden=NO;window.hidden=YES;refresh_recents(&delegate,visible_in_window(&container));assert(!history_reads);
    window.hidden=NO;
    refresh_recents(&delegate,visible_in_window(&container));assert(history_reads==1 && s.recent_menu_open);
    assert(row.count==2 && row.children[0]->metadata==metadata_a && row.children[1]->metadata==metadata_b);
    id first=row.children[0],second=row.children[1],snapshot=s.recent_entries;
    row.offset.x=64;
    /* Real remember() persists a selection immediately. Subsequent edits,
     * sends, timer ticks, images and provider-tab changes keep this snapshot. */
    remember(&name_b);assert(history_writes==1 && saved_history->children[0]==&name_b);
    U reads=history_reads;
    for(U i=0;i<8;i++) { s.tab=i%2;refresh_recents(&delegate,visible_in_window(&container)); }
    assert(history_reads==reads && s.recent_entries==snapshot && row.offset.x==64);
    assert(row.children[0]==first && row.children[1]==second);
    /* Reopening the same UIKit container loads the new order exactly once. */
    container.window=nil;refresh_recents(&delegate,visible_in_window(&container));assert(!s.recent_menu_open && history_reads==reads);
    container.window=&window;refresh_recents(&delegate,visible_in_window(&container));assert(history_reads==reads+1);
    assert(row.children[0]->metadata==metadata_b && row.children[1]->metadata==metadata_a);
    assert(!first->parent && !second->parent && row.offset.x==0);
    /* No extra reads/layout churn on an unchanged snapshot after reopening. */
    first=row.children[0];row.offset.x=64;
    refresh_recents(&delegate,NO);refresh_recents(&delegate,YES);
    assert(history_reads==reads+2 && row.children[0]==first && row.offset.x==64);
    return 0;
}
'''


class RecentSnapshotTests(unittest.TestCase):
    def test_history_changes_wait_until_the_next_menu_open(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        source = (test_composer.ROOT / "src" / "SSComposer.c").read_text()
        # Thumbnail loading and strip construction are UIKit infrastructure;
        # production snapshot, history, visibility and button binding run here.
        for name, replacement in (
            ("set_thumbnail", 'static void set_thumbnail(id image,id metadata) { (void)metadata;(void)thumbnail_url_key;(void)thumbnail_record_key;v1(image,"setImage:",nil); }'),
            ("make_strip", 'static id make_strip(void) { (void)strip_class;(void)strip_cancel_touch;(void)configure_strip;assert(!"test supplies its UIKit strip");return nil; }'),
        ):
            start = source.index(f"static {'id' if name=='make_strip' else 'void'} {name}(")
            end = source.index('\n}', start) + 2
            source = source[:start] + replacement + source[end:]
        test_composer.ComposerTests().compile_run(HARNESS.replace('#include "SSComposer.c"', source), [zig, "cc", "-fblocks"], runtime=True)


if __name__ == "__main__":
    unittest.main()
