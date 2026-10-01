"""Exercise unified results and selector ownership in the production C code."""
import os
import shutil
import unittest
import test_composer

HARNESS = r'''
#include <stdarg.h>
#include <assert.h>
#include "SSComposer.c"
struct Fake {
    const char *cls,*text;
    id name,url,native,identifier;
    id children[160]; U count;
    State *context;
};
static struct Fake objects[20000],classes[8];static U used,class_count;
static id fresh(const char *cls) { assert(used<20000);id o=&objects[used++];o->cls=cls;return o; }
static id text_value(const char *text) { id o=fresh("NSString");o->text=text;return o; }
Class objc_getClass(const char *name) {
    for(U i=0;i<class_count;i++)if(!strcmp(name,classes[i].cls))return &classes[i];
    assert(class_count<8);classes[class_count].cls=name;return &classes[class_count++];
}
Class object_getClass(id o) { return o ? objc_getClass(o->cls) : nil; }
SEL sel_registerName(const char *name) { return name; }
id objc_retain(id o) { return o; }
void objc_release(id o) { (void)o; }
id objc_getAssociatedObject(id o,const void *key) { return o && key==&selector_key ? o : nil; }
static ptrdiff_t context_offset=offsetof(struct Fake,context);
Ivar class_getInstanceVariable(Class c,const char *name) { (void)c;return !strcmp(name,"_state") ? &context_offset : NULL; }
ptrdiff_t ivar_getOffset(Ivar iv) { return *(ptrdiff_t *)iv; }
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"new"))result=fresh(o->cls);
    else if(!strcmp(sel,"stringWithUTF8String:"))result=text_value(va_arg(args,const char *));
    else if(!strcmp(sel,"standardUserDefaults"))result=o;
    else if(!strcmp(sel,"integerForKey:"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"count"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"UTF8String"))result=(id)o->text;
    else if(!strcmp(sel,"objectAtIndex:")) { U i=va_arg(args,U);assert(i<o->count);result=o->children[i]; }
    else if(!strcmp(sel,"addObject:")) { assert(o->count<160);o->children[o->count++]=va_arg(args,id); }
    else if(!strcmp(sel,"objectForKey:")) {
        id k=va_arg(args,id);
        if(!strcmp(o->cls,"Catalog")) { for(U i=0;i<o->count;i++)if(!strcmp(o->children[i]->name->text,k->text))result=o->children[i]; }
        else if(!strcmp(k->text,"name"))result=o->name;
        else if(!strcmp(k->text,"native"))result=o->native;
        else if(!strcmp(k->text,"id"))result=o->identifier;
        else assert(!"unexpected key");
    } else if(!strcmp(sel,"sortUsingComparator:")) {
        struct Block { void *isa;int flags,reserved; I (*invoke)(void *,id,id); };
        struct Block *block=(struct Block *)va_arg(args,id);
        for(U i=0;i<o->count;i++)for(U j=i+1;j<o->count;j++)if(block->invoke(block,o->children[i],o->children[j])>0) {
            id tmp=o->children[i];o->children[i]=o->children[j];o->children[j]=tmp;
        }
    } else if(!strcmp(sel,"caseInsensitiveCompare:")) {
        const char *other=va_arg(args,id)->text;I n=0;
        const unsigned char *a=(const unsigned char *)o->text,*b=(const unsigned char *)other;
        while(*a || *b) { unsigned x=*a,y=*b;if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;n=(I)x-(I)y;if(n)break;a++;b++; }
        result=(id)(intptr_t)n;
    } else assert(!"unexpected selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
static id providers;
id tas_emotes_picker_copy(id room,int provider,int scope,id query,size_t limit) {
    (void)room;assert(provider==0 && scope==-1 && limit==6500);
    id result=fresh("NSMutableArray");
    for(U i=0;i<providers->count;i++)if(ss_ascii_prefix(providers->children[i]->name->text,query->text))result->children[result->count++]=providers->children[i];
    return result;
}
static id item(const char *name,BOOL native) {
    id o=fresh("NSDictionary");o->name=text_value(name);o->native=native ? o->name : nil;
    o->identifier=text_value(native ? "25" : "tas-synthetic");return o;
}
static I native_rows(id self,SEL sel,id table,I section) { (void)self;(void)sel;(void)table;assert(section==0);return 9; }
int main(void) {
    id kappa=item("Kappa",YES),keeper=item("Keeper",YES),provider=item("KEKW",NO),overlap=item("Kappa",NO);
    id catalog=fresh("Catalog");catalog->count=2;catalog->children[0]=keeper;catalog->children[1]=kappa;
    id native=fresh("NSMutableArray");native->count=2;native->children[0]=keeper;native->children[1]=kappa;
    providers=fresh("NSMutableArray");providers->count=2;providers->children[0]=provider;providers->children[1]=overlap;
    State s={.native_entries=native,.native_by_code=catalog,.native_ready=YES};
    id result=unified_matches(&s,text_value("k"));assert(result->count==3);
    assert(result->children[0]==kappa && result->children[1]==provider && result->children[2]==keeper);
    assert(!strcmp(key(result->children[0],"id")->text,"25"));
    result=unified_matches(&s,text_value("KAP"));assert(result->count==1 && result->children[0]==kappa);
    result=unified_matches(&s,text_value("kek"));assert(result->count==1 && result->children[0]==provider);
    result=unified_matches(&s,text_value("nothing"));assert(!result->count);
    result=unified_matches(&s,text_value(""));assert(result->count==3); /* bare colon */
    /* Empty/unknown native catalogs continue to expose provider results. */
    s.native_entries=nil;s.native_by_code=nil;result=unified_matches(&s,text_value("k"));assert(result->count==2);
    /* A large shared prefix cannot starve either catalog or overflow the strip. */
    native->count=0;providers->count=0;catalog->count=0;
    for(U i=0;i<70;i++) { native->children[native->count++]=kappa;providers->children[providers->count++]=provider; }
    s.native_entries=native;s.native_by_code=catalog;
    result=unified_matches(&s,text_value("k"));assert(result->count==64);
    for(U i=0;i<64;i++)assert(result->children[i]==(i%2 ? provider : kappa));
    /* Suppression belongs only to the connected composer's colon completion.
     * Mentions, commands, disabled mode, unknown catalogs and other selectors
     * retain Twitch's original result count. Both supported modes suppress. */
    delegate_class=objc_getClass("SSComposerDelegate");id selector=fresh("Selector");selector->context=&s;
    original_selector_rows=(IMP)native_rows;
    s.colon_selector=YES;
    assert(!selector_rows(selector,"rows",nil,0));
    objc_getClass("NSUserDefaults")->count=1;assert(!selector_rows(selector,"rows",nil,0));
    objc_getClass("NSUserDefaults")->count=2;assert(selector_rows(selector,"rows",nil,0)==9);
    objc_getClass("NSUserDefaults")->count=0;s.colon_selector=NO;assert(selector_rows(selector,"rows",nil,0)==9);
    s.colon_selector=YES;s.native_ready=NO;assert(selector_rows(selector,"rows",nil,0)==9);
    assert(selector_rows(nil,"rows",nil,0)==9);
    return 0;
}
'''


class NativePickerTests(unittest.TestCase):
    def test_mixed_results_native_ids_and_scoped_selector_replacement(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        test_composer.ComposerTests().compile_run(HARNESS, [zig, "cc", "-fblocks"], runtime=True)


if __name__ == "__main__":
    unittest.main()
