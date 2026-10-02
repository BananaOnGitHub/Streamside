"""Picker display order must not change the exact-code lookup registry."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_emote_ui import RUNTIME

ROOT = Path(__file__).resolve().parent.parent
HARNESS = r'''
#include <assert.h>
#include <stdarg.h>
#include <strings.h>
#include "TASEmotes.c"
struct Fake {
    const char *cls;
    char value[256];
    uint64_t number;
    id children[32],keys[8],values[8];
    size_t count;
};
static struct Fake objects[8192],classes[8];
static size_t used,class_count;
static id fresh(const char *cls) { assert(used<8192);id o=&objects[used++];o->cls=cls;return o; }
static id string(const char *value) { id o=fresh("NSString");snprintf(o->value,sizeof(o->value),"%s",value);return o; }
Class objc_getClass(const char *name) {
    for(size_t i=0;i<class_count;i++)if(!strcmp(classes[i].cls,name))return &classes[i];
    assert(class_count<8);classes[class_count].cls=name;return &classes[class_count++];
}
SEL sel_registerName(const char *name) { return name; }
id objc_retain(id o) { return o; }
void objc_release(id o) { (void)o; }
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"new"))result=fresh(o->cls);
    else if(!strcmp(sel,"isKindOfClass:")) {
        Class c=va_arg(args,Class);
        result=(id)(uintptr_t)(!strcmp(o->cls,c->cls) ||
            (!strcmp(c->cls,"NSDictionary") && !strcmp(o->cls,"NSMutableDictionary")));
    } else if(!strcmp(sel,"stringWithUTF8String:"))result=string(va_arg(args,const char *));
    else if(!strcmp(sel,"UTF8String"))result=(id)o->value;
    else if(!strcmp(sel,"numberWithUnsignedLongLong:")) { result=fresh("NSNumber");result->number=va_arg(args,uint64_t); }
    else if(!strcmp(sel,"numberWithInt:")) { result=fresh("NSNumber");result->number=(uint64_t)va_arg(args,int); }
    else if(!strcmp(sel,"numberWithDouble:")) { (void)va_arg(args,double);result=fresh("NSNumber"); }
    else if(!strcmp(sel,"setObject:forKey:")) {
        id value=va_arg(args,id),key=va_arg(args,id);assert(o->count<8);
        o->keys[o->count]=key;o->values[o->count++]=value;
    } else if(!strcmp(sel,"objectForKey:")) {
        id key=va_arg(args,id);
        for(size_t i=0;i<o->count;i++)if(!strcmp(o->keys[i]->value,key->value))result=o->values[i];
    } else if(!strcmp(sel,"copy")) { result=fresh("NSDictionary");*result=*o;result->cls="NSDictionary"; }
    else if(!strcmp(sel,"addObject:")) { assert(o->count<32);o->children[o->count++]=va_arg(args,id); }
    else if(!strcmp(sel,"count"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"objectAtIndex:")) { size_t i=va_arg(args,size_t);assert(i<o->count);result=o->children[i]; }
    else if(!strcmp(sel,"removeLastObject")) { assert(o->count);o->count--; }
    else if(!strcmp(sel,"sortUsingComparator:")) {
        struct Block { void *isa;int flags,reserved;NSInteger (*invoke)(void *,id,id); };
        struct Block *block=va_arg(args,void *);
        for(size_t i=1;i<o->count;i++) {
            id item=o->children[i];size_t j=i;
            while(j && block->invoke(block,o->children[j-1],item)>0) { o->children[j]=o->children[j-1];j--; }
            o->children[j]=item;
        }
    } else if(!strcmp(sel,"caseInsensitiveCompare:") || !strcmp(sel,"compare:")) {
        id other=va_arg(args,id);
        int order=!strcmp(sel,"compare:") ? strcmp(o->value,other->value) : strcasecmp(o->value,other->value);
        result=(id)(intptr_t)(order<0 ? -1 : order>0 ? 1 : 0);
    } else assert(!"unexpected picker selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
void *_NSConcreteGlobalBlock[32];
static void add(Room *room,const char *name,unsigned char provider,bool global) {
    const char *prefixes[]={"https://cdn.7tv.app/emote/","https://cdn.betterttv.net/emote/","https://cdn.frankerfacez.com/emote/"};
    char url[256];snprintf(url,sizeof(url),"%s%s/2x",prefixes[provider],name);
    add_emote_locked(room,global ? MAX_GLOBAL : MAX_ROOM,name,url,provider,global,NULL,1);
}
static void expect(id items,const char *names) {
    char actual[512]={0};
    for(size_t i=0;i<count(items);i++) {
        if(i)strcat(actual," ");strcat(actual,text(dict(at(items,i),"name")));
    }
    assert(!strcmp(actual,names));objc_release(items);
}
int main(void) {
    g_enabled=true;Room *room=room_locked("123",time(NULL));id channel=string("123");
    add(room,"ZAMN",0,false);add(room,"aaaa",0,false);add(room,"Alpha",1,false);
    add(room,"alpha",0,false);add(room,"Beta",2,false);add(room,"YouKnow",0,false);add(room,"beta",2,false);
    add(&g_global,"aardvark",1,true);add(&g_global,"ZGlobal",0,true);
    add(&g_global,"zglobal",2,true);add(&g_global,"aaaa",2,true);
    /* Uppercase and lowercase stay distinct in the exact-code registry. */
    assert(find_word(room,"Alpha") && find_word(room,"alpha") && !find_word(room,"ALPHA"));
    assert(find_word(room,"Alpha")->fake_id!=find_word(room,"alpha")->fake_id);
    for(size_t i=1;i<room->size;i++)assert(strcmp(room->items[i-1].name,room->items[i].name)<0);
    expect(tas_emotes_picker_copy(channel,0,0,nil,6500),"aaaa Alpha alpha Beta beta YouKnow ZAMN");
    expect(tas_emotes_picker_copy(channel,1,0,nil,6500),"aaaa alpha YouKnow ZAMN");
    expect(tas_emotes_picker_copy(channel,2,0,nil,6500),"Alpha");
    expect(tas_emotes_picker_copy(channel,3,0,nil,6500),"Beta beta");
    expect(tas_emotes_picker_copy(channel,0,1,nil,6500),"aaaa aardvark ZGlobal zglobal");
    expect(tas_emotes_picker_copy(channel,1,1,nil,6500),"ZGlobal");
    expect(tas_emotes_picker_copy(channel,2,1,nil,6500),"aardvark");
    expect(tas_emotes_picker_copy(channel,3,1,nil,6500),"aaaa zglobal");
    expect(tas_emotes_picker_copy(channel,0,-1,nil,6500),"aaaa aardvark Alpha alpha Beta beta YouKnow ZAMN ZGlobal zglobal");
    expect(tas_emotes_picker_copy(channel,0,-1,string("A"),6500),"aaaa aardvark Alpha alpha");
    expect(tas_emotes_picker_copy(channel,0,-1,nil,2),"aaaa aardvark");
    expect(tas_emotes_picker_copy(channel,0,0,nil,0),"");
    expect(tas_emotes_picker_copy(nil,0,1,nil,6500),"aaaa aardvark ZGlobal zglobal");
    id both=tas_emotes_picker_copy(channel,0,-1,nil,6500);
    assert(dict(at(both,0),"id")->number==find_word(room,"aaaa")->fake_id); /* channel wins exact overlap */
    objc_release(both);
    id exact=tas_emotes_named_copy(channel,string("Alpha"));assert(dict(exact,"id")->number==find_word(room,"Alpha")->fake_id);
    exact=tas_emotes_named_copy(channel,string("alpha"));assert(dict(exact,"id")->number==find_word(room,"alpha")->fake_id);
    assert(!tas_emotes_named_copy(channel,string("ALPHA")));
    for(size_t i=1;i<room->size;i++)assert(strcmp(room->items[i-1].name,room->items[i].name)<0);
    reset_room_locked(room,false,time(NULL));reset_room_locked(&g_global,false,time(NULL));
    return 0;
}
'''


class EmotePickerTests(unittest.TestCase):
    def test_display_order_combines_cases_providers_and_scopes_without_changing_lookup(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig, "Zig is required for the production picker harness")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "objc").mkdir()
            runtime = RUNTIME + '\nMethod *class_copyMethodList(Class,unsigned *);\nSEL method_getName(Method);\n'
            for name in ("runtime.h", "objc.h", "message.h"):
                (root / "objc" / name).write_text(runtime)
            harness, binary = root / "picker.c", root / "picker"
            harness.write_text(HARNESS)
            built = subprocess.run([zig, "cc", "-fblocks", "-Wall", "-Wextra", "-Werror",
                "-Wno-cast-function-type-mismatch", "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
                "-I", str(root), "-I", str(ROOT / "src"), str(harness), "-pthread", "-o", str(binary)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([binary], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stderr)
