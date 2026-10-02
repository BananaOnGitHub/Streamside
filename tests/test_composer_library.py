"""Exercise the actual footer/browser functions, with a host UIKit boundary."""
import os
import shutil
import unittest
import test_composer as composer
ROOT = composer.ROOT


HARNESS = r'''
#include <assert.h>
#include <stdarg.h>
#include "SSComposer.c"
struct Fake {
    const char *cls,*text,*action;
    id parent,host,button,highlight,stack,highlights,container,views[6],children[16],front;
    State *context;
    Rect frame,bounds;
    U count,selected,targets,reloads;
    id tint,background;
    double constant;
    BOOL hidden,active;
};
static struct Fake objects[256],classes[32],empty={0},datasets[4][2];
static U allocated,class_count,queries,native_actions;
static int last_provider,last_scope;
static id expected_room;
static id create(const char *cls) { assert(allocated<256);id o=&objects[allocated++];o->cls=cls;return o; }
Class objc_getClass(const char *name) {
    for(U i=0;i<class_count;i++)if(!strcmp(classes[i].cls,name))return &classes[i];
    assert(class_count<32);classes[class_count].cls=name;return &classes[class_count++];
}
Class object_getClass(id o) { return o; }
SEL sel_registerName(const char *s) { return s; }
const char *sel_getName(SEL s) { return s; }
Ivar class_getInstanceVariable(Class c,const char *name) {
    (void)c;
    if(!strcmp(name,"_state"))return (Ivar)(uintptr_t)offsetof(struct Fake,context);
    if(!strcmp(name,"emoteButtonsStackView"))return (Ivar)(uintptr_t)offsetof(struct Fake,stack);
    if(!strcmp(name,"emoteHighlightsStackView"))return (Ivar)(uintptr_t)offsetof(struct Fake,highlights);
    if(!strcmp(name,"emoticonPaletteContainerView"))return (Ivar)(uintptr_t)offsetof(struct Fake,container);
    const char *names[]={"$__lazy_storage_$_recentEmotesButton","$__lazy_storage_$_channelEmotesButton",
        "$__lazy_storage_$_allEmotesButton","recentEmotesHighlight","channelEmotesHighlight","allEmotesHighlight"};
    for(U i=0;i<6;i++)if(!strcmp(name,names[i]))return (Ivar)(uintptr_t)(offsetof(struct Fake,views)+i*sizeof(id));
    return NULL;
}
ptrdiff_t ivar_getOffset(Ivar iv) { return (ptrdiff_t)(uintptr_t)iv; }
size_t class_getInstanceSize(Class c) { (void)c;return sizeof(struct Fake); }
id objc_retain(id o) { return o; }
void objc_release(id o) { (void)o; }
id objc_loadWeakRetained(id *p) { return *p; }
id objc_initWeak(id *p,id o) { *p=o;return o; }
void objc_destroyWeak(id *p) { *p=nil; }
id objc_getAssociatedObject(id o,const void *key) {
    if(!o)return nil;
    if(key==&state_key || key==&footer_key)return o->host;
    if(key==&button_key)return o->button;
    if(key==&library_highlight_key)return o->highlight;
    return nil;
}
void objc_setAssociatedObject(id o,const void *key,id value,uintptr_t policy) {
    assert(policy==1);
    if(key==&footer_key)o->host=value;
    else if(key==&button_key)o->button=value;
    else if(key==&library_highlight_key)o->highlight=value;
    else assert(!"unexpected association");
}
void *ss_test_field(id o,const char *name) {
    if(!strcmp(name,"frame"))return &o->frame;
    if(!strcmp(name,"bounds"))return &o->bounds;
    assert(!"unexpected geometry");return NULL;
}
void ss_test_frame(id o,Rect value) { o->frame=value;o->bounds.size=value.size; }
id ss_test_view(const char *cls,Rect value) { id o=create(cls);ss_test_frame(o,value);return o; }
id ss_test_collection(Rect value,id flow) { assert(flow);return ss_test_view("UICollectionView",value); }
Rect ss_test_convert(id footer) { return footer->frame; }
id ss_test_constraint(id anchor,double value) { anchor->constant=value;return anchor; }
void ss_test_size(id flow,Size value) { flow->bounds.size=value; }
void ss_test_offset_animated(id content,Point value,BOOL animated) { (void)content;(void)value;(void)animated;assert(!"no provider recents in this fixture"); }
static void remove_child(id parent,id child) {
    if(!parent)return;
    for(U i=0;i<parent->count;i++)if(parent->children[i]==child) {
        memmove(parent->children+i,parent->children+i+1,(parent->count-i-1)*sizeof(id));parent->count--;break;
    }
}
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"isKindOfClass:")) { Class c=va_arg(args,Class);result=(id)(uintptr_t)(!strcmp(o->cls,c->cls)); }
    else if(!strcmp(sel,"new") || !strcmp(sel,"alloc"))result=create(o->cls);
    else if(!strcmp(sel,"stringWithUTF8String:")) { result=create("NSString");result->text=va_arg(args,const char *); }
    else if(!strcmp(sel,"isEqual:")) { id other=va_arg(args,id);result=(id)(uintptr_t)(o==other || (o->text && other->text && !strcmp(o->text,other->text))); }
    else if(!strcmp(sel,"systemImageNamed:")) { assert(va_arg(args,id));result=create("UIImage"); }
    else if(!strcmp(sel,"setImage:forState:")) { assert(va_arg(args,id));assert(!va_arg(args,U)); }
    else if(!strcmp(sel,"setAccessibilityLabel:") || !strcmp(sel,"setAccessibilityIdentifier:") || !strcmp(sel,"setText:"))o->text=va_arg(args,id)->text;
    else if(!strcmp(sel,"widthAnchor") || !strcmp(sel,"heightAnchor"))result=o;
    else if(!strcmp(sel,"setActive:"))o->active=(BOOL)va_arg(args,int);
    else if(!strcmp(sel,"setTranslatesAutoresizingMaskIntoConstraints:") || !strcmp(sel,"setUserInteractionEnabled:") || !strcmp(sel,"setAlwaysBounceVertical:")) { (void)va_arg(args,int); }
    else if(!strcmp(sel,"setHidden:"))o->hidden=(BOOL)va_arg(args,int);
    else if(!strcmp(sel,"isHidden"))result=(id)(uintptr_t)o->hidden;
    else if(!strcmp(sel,"setSelected:"))o->selected=(U)va_arg(args,int);
    else if(!strcmp(sel,"setTintColor:"))o->tint=va_arg(args,id);
    else if(!strcmp(sel,"tintColor"))result=o->tint;
    else if(!strcmp(sel,"setBackgroundColor:"))o->background=va_arg(args,id);
    else if(!strcmp(sel,"backgroundColor"))result=o->background;
    else if(!strcmp(sel,"secondaryLabelColor") || !strcmp(sel,"systemPurpleColor") || !strcmp(sel,"secondarySystemBackgroundColor") || !strcmp(sel,"clearColor"))result=o;
    else if(!strcmp(sel,"superview"))result=o->parent;
    else if(!strcmp(sel,"window"))result=o;
    else if(!strcmp(sel,"subviews") || !strcmp(sel,"arrangedSubviews"))result=o;
    else if(!strcmp(sel,"count"))result=(id)(uintptr_t)o->count;
    else if(!strcmp(sel,"objectAtIndex:")) { U i=va_arg(args,U);assert(i<o->count);result=o->children[i]; }
    else if(!strcmp(sel,"addObject:")) { assert(o->count<16);o->children[o->count++]=va_arg(args,id); }
    else if(!strcmp(sel,"addSubview:")) { id child=va_arg(args,id);assert(o->count<16);o->children[o->count++]=child;child->parent=o; }
    else if(!strcmp(sel,"removeArrangedSubview:"))remove_child(o,va_arg(args,id));
    else if(!strcmp(sel,"removeFromSuperview")) { remove_child(o->parent,o);o->parent=nil; }
    else if(!strcmp(sel,"insertArrangedSubview:atIndex:")) {
        id child=va_arg(args,id);U i=va_arg(args,U);assert(i<=o->count && o->count<16);
        memmove(o->children+i+1,o->children+i,(o->count-i)*sizeof(id));o->children[i]=child;o->count++;child->parent=o;
    } else if(!strcmp(sel,"bringSubviewToFront:")) { o->front=va_arg(args,id);assert(o->front->parent==o); }
    else if(!strcmp(sel,"addTarget:action:forControlEvents:")) {
        assert(va_arg(args,id));o->action=va_arg(args,SEL);U event=va_arg(args,U);assert(event==1UL<<6 || event==1UL<<12);o->targets++;
    } else if(!strcmp(sel,"initWithItems:")) { id items=va_arg(args,id);o->count=items->count;memcpy(o->children,items->children,items->count*sizeof(id));result=o; }
    else if(!strcmp(sel,"setSelectedSegmentIndex:"))o->selected=(U)va_arg(args,I);
    else if(!strcmp(sel,"selectedSegmentIndex"))result=(id)(uintptr_t)o->selected;
    else if(!strcmp(sel,"setMinimumInteritemSpacing:") || !strcmp(sel,"setMinimumLineSpacing:")) { }
    else if(!strcmp(sel,"registerClass:forCellWithReuseIdentifier:")) { assert(va_arg(args,Class));assert(va_arg(args,id)); }
    else if(!strcmp(sel,"setDataSource:") || !strcmp(sel,"setDelegate:"))o->host=va_arg(args,id);
    else if(!strcmp(sel,"setTextAlignment:") || !strcmp(sel,"setNumberOfLines:")) { (void)va_arg(args,I); }
    else if(!strcmp(sel,"setTextColor:"))o->tint=va_arg(args,id);
    else if(!strcmp(sel,"reloadData"))o->reloads++;
    else if(!strcmp(sel,"visibleCells"))result=&empty;
    else assert(!"unexpected library selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
id tas_emotes_picker_copy(id room,int provider,int scope,id query,size_t limit) {
    assert(room==expected_room && !query && limit==6500);assert(provider>=0 && provider<4 && scope>=0 && scope<2);
    last_provider=provider;last_scope=scope;queries++;return &datasets[provider][scope];
}
static void native_action(id o,SEL sel) { (void)o;(void)sel;native_actions++; }
static void rebuilt_stack(id stack,id own,id a,id b,id c) {
    own->parent=nil;stack->count=0;
    id native[]={a,b,c};for(U i=0;i<3;i++)if(native[i]) { stack->children[stack->count++]=native[i];native[i]->parent=stack; }
}
static void native_footer_layout(id footer,SEL sel) {
    (void)sel;
    rebuilt_stack(footer->stack,footer->button,footer->views[0],footer->views[1],footer->views[2]);
    rebuilt_stack(footer->highlights,footer->highlight,footer->views[3],footer->views[4],footer->views[5]);
}
static void native_footer_apply(id footer,SEL sel,id theme) {
    native_footer_layout(footer,sel);
    footer->views[0]->tint=footer->views[2]->tint;
    footer->views[1]->tint=theme;
    footer->views[3]->background=nil;footer->views[4]->background=theme;
}
int main(void) {
    (void)attachment_metadata_key;(void)thumbnail_url_key;(void)thumbnail_record_key;
    (void)request_native_catalog;(void)unified_matches;(void)image_request;(void)visual_text;
    struct Fake normal={.cls="UIColor"},active={.cls="UIColor"},room={.cls="NSString"};expected_room=&room;
    State s={.room=&room};struct Fake delegate={.context=&s};delegate_class=&delegate;
    struct Fake owner={.cls=INPUT,.host=&delegate},container={.cls=CONTAINER,.parent=&owner,.bounds={{0,0},{390,300}}};owner.container=&container;
    struct Fake native={.cls="UICollectionView",.parent=&container},footer={.cls=FOOTER,.parent=&container,.frame={{0,252},{390,48}},.bounds={{0,0},{390,48}}};
    container.children[container.count++]=&native;container.children[container.count++]=&footer;
    struct Fake buttons={.cls="UIStackView"},highlights={.cls="UIStackView"},views[6]={0};footer.stack=&buttons;footer.highlights=&highlights;
    for(U i=0;i<6;i++) { views[i].cls=i<3 ? "UIButton":"UIView";views[i].tint=&normal;footer.views[i]=&views[i]; }
    views[0].tint=&active;views[3].background=&active;
    rebuilt_stack(&buttons,&empty,&views[0],&views[1],&views[2]);rebuilt_stack(&highlights,&empty,&views[3],&views[4],&views[5]);
    s.owner=&owner;s.footer=&footer;
    for(int p=0;p<4;p++)for(int sc=0;sc<2;sc++)datasets[p][sc].count=(U)(p*100+sc+1);
    install_footer(&footer,&owner);
    id button=footer.button,highlight=footer.highlight;
    assert(button && highlight && buttons.count==4 && buttons.children[1]==button && highlights.children[1]==highlight);
    assert(button->constant==40 && highlight->constant==3 && button->targets==1 && !strcmp(button->action,"ssThirdParty:"));
    U once_allocated=allocated;for(int i=0;i<10;i++)install_footer(&footer,&owner);
    assert(allocated==once_allocated && buttons.count==4 && highlights.count==4 && button->targets==1 && GET(library_tab_creations)==1);
    /* The native Swift worker removes all arranged views, then adds ONLY its
     * current native buttons. The same retained button must be reinserted. */
    original_footer_layout=(IMP)native_footer_layout;
    footer_layout(&footer,"layoutSubviews");
    assert(footer.button==button && buttons.children[1]==button && highlights.children[1]==highlight && GET(library_tab_repairs)==1);
    assert(button->targets==1);
    rebuilt_stack(&buttons,button,nil,&views[1],&views[2]);rebuilt_stack(&highlights,highlight,nil,&views[4],&views[5]);
    install_footer(&footer,&owner);assert(buttons.children[0]==button && highlights.children[0]==highlight);
    /* Restore Recent and open the actual complete panel, not an empty tab. */
    rebuilt_stack(&buttons,button,&views[0],&views[1],&views[2]);rebuilt_stack(&highlights,highlight,&views[3],&views[4],&views[5]);
    install_footer(&footer,&owner);third_party_tab(&delegate,"ssThirdParty:",button);
    assert(s.tab==1 && s.panel && s.panel->parent==&container && native.hidden && container.front==s.panel);
    assert(s.provider->count==4 && s.scope->count==2 && s.grid->host==&delegate);
    const char *providers[]={"All","7TV","BTTV","FFZ"};for(U i=0;i<4;i++)assert(!strcmp(s.provider->children[i]->text,providers[i]));
    assert(!strcmp(s.scope->children[0]->text,"Channel") && !strcmp(s.scope->children[1]->text,"Global"));
    assert(s.panel->frame.size.height==252 && s.grid->frame.origin.y==76 && s.grid->frame.size.height==176);
    assert(button->selected && highlight->background==&active && !views[3].background && views[0].tint==&normal);
    for(int p=0;p<4;p++) {
        s.scope->selected=1;scope_changed(&delegate,"ssScope:",s.scope);assert(last_scope==1);
        s.provider->selected=(U)p;provider_changed(&delegate,"ssProvider:",s.provider);
        assert(s.library==p && !s.library_scope && !s.scope->selected && last_provider==p && !last_scope);
        assert(item_count(&delegate,"collectionView:numberOfItemsInSection:",s.grid,0)==(I)datasets[p][0].count);
    }
    /* A rebuild while browsing must preserve the panel and selection. */
    rebuilt_stack(&buttons,button,&views[0],&views[1],&views[2]);rebuilt_stack(&highlights,highlight,&views[3],&views[4],&views[5]);
    install_footer(&footer,&owner);assert(buttons.children[1]==button && button->selected && s.tab==1 && s.panel->parent==&container);
    struct Fake themed={.cls="UIColor"};original_footer_apply=(IMP)native_footer_apply;
    footer_apply(&footer,"apply:",&themed);
    assert(button->selected && highlight->background==&themed && !views[4].background && s.library==3 && !s.library_scope);
    container.bounds.size.width=844;place_library_panel(&s,&container,&footer);assert(s.grid->frame.size.width==836);
    /* Backspace keeps the browser open; native library navigation exits it. */
    for(U i=0;i<5;i++)original_footer_actions[i]=(IMP)native_action;
    footer_action(&footer,"backspaceButtonPressed");assert(s.tab==1 && native.hidden);
    footer_action(&footer,"channelEmotesButtonPressed");assert(!s.tab && !native.hidden && !s.panel->parent && !button->selected && !highlight->background);
    assert(views[4].background==&themed && views[1].tint==&themed && native_actions==2 && queries==10);
    /* Native Recent's lazy views can be absent altogether, not just absent
     * from the stacks. The full library must still open and highlight. */
    footer.views[0]=nil;footer.views[3]=nil;footer_layout(&footer,"layoutSubviews");
    assert(buttons.children[0]==button && highlights.children[0]==highlight);
    third_party_tab(&delegate,"ssThirdParty:",button);
    assert(s.tab==1 && button->selected && highlight->background==&themed && native.hidden);
    footer_action(&footer,"allEmotesButtonPressed");assert(!s.tab && !native.hidden && !s.panel->parent);
    return 0;
}
'''


def replace_body(source, name, body):
    start = source.index(name + " {")
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[:opening] + "{" + body + "}" + source[end:]


class LibraryTests(unittest.TestCase):
    def test_footer_rebuild_restores_complete_browser_and_provider_scope_reset(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        source = composer.recent_geometry_source()
        source = replace_body(source, "static id delegate_for(id owner)", "return objc_getAssociatedObject(owner,&state_key);")
        source = replace_body(source, "static void refresh(id delegate)", "State *s=state(delegate);refresh_library(s);place_library_panel(s,container_for(s,s->owner),s->footer);")
        for signature, body in (("static void render(id delegate)", "(void)delegate;"),
                                ("static void expand(id delegate)", "(void)delegate;"),
                                ("static void start_tick(id delegate)", "(void)delegate;"),
                                ("static void set_thumbnail(id image_view,id metadata)", "(void)image_view;(void)metadata;")):
            source = replace_body(source, signature, body)
        source = source.replace('static id view(const char *c,Rect r) { return ((id (*)(id,SEL,Rect))objc_msgSend)(m0((id)objc_getClass(c),"alloc"),sel_registerName("initWithFrame:"),r); }',
            'extern id ss_test_view(const char *,Rect);\nextern id ss_test_collection(Rect,id);\nextern Rect ss_test_convert(id);\nextern id ss_test_constraint(id,double);\nextern void ss_test_size(id,Size);\nstatic id view(const char *c,Rect r) { return ss_test_view(c,r); }')
        source = source.replace('((id (*)(id,SEL,Rect,id))objc_msgSend)(m0((id)objc_getClass("UICollectionView"),"alloc"),sel_registerName("initWithFrame:collectionViewLayout:"),(Rect){{0,76},{320,124}},flow)',
            'ss_test_collection((Rect){{0,76},{320,124}},flow)')
        source = source.replace('((void (*)(id,SEL,Size))objc_msgSend)(flow,sel_registerName("setItemSize:"),(Size){56,56})', 'ss_test_size(flow,(Size){56,56})')
        source = source.replace('((Rect (*)(id,SEL,Rect,id))objc_msgSend)(footer,sel_registerName("convertRect:toView:"),rect(footer,"bounds"),container)', 'ss_test_convert(footer)')
        source = source.replace('((id (*)(id,SEL,double))objc_msgSend)(m0(item,"widthAnchor"),sel_registerName("constraintEqualToConstant:"),width)', 'ss_test_constraint(m0(item,"widthAnchor"),width)')
        source = source.replace('((id (*)(id,SEL,double))objc_msgSend)(m0(highlight,"heightAnchor"),sel_registerName("constraintEqualToConstant:"),3.0)', 'ss_test_constraint(m0(highlight,"heightAnchor"),3.0)')
        composer.ComposerTests().compile_run(HARNESS.replace('#include "SSComposer.c"', source), [zig, "cc", "-fblocks"], runtime=True)
