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
    id parent,host,button,highlight,stack,highlights,container,palette,views[6],children[16],front;
    id flow,collection,heading,deferred_heading,title,native_header,first,last,path,element_kind,marker;
    const char *encoding;
    State *context;
    Rect frame,bounds,applied_first;
    Insets inset,adjusted;
    Insets cached_sections[4];
    Point offset;
    Size content_size;
    Size applied_size;
    I item_counts[4];
    double header_heights[4];
    I section;
    U sections;
    U count,selected,targets,reloads;
    id tint,background;
    double constant,line_spacing,interitem_spacing;
    I scroll_direction;
    BOOL scroll_options[8];
    BOOL hidden,active,scroll_enabled,clips,metrics,attributes,needs_metrics;
};
static struct Fake objects[2048],classes[32],empty={0},datasets[4][2];
static U allocated,class_count,queries,native_actions,metric_invalidations;
static unsigned initial_header_layouts;
static int last_provider,last_scope;
static id expected_room;
static uint64_t catalog_revision=1;
uint64_t tas_emotes_catalog_revision(void) { return catalog_revision; }
static id raw_item(id flow,SEL sel,id path);
static id raw_header(id flow,SEL sel,id kind_name,id path);
static Size raw_size(id flow,SEL sel);
static id raw_elements(id flow,SEL sel,Rect query);
static Rect last_query;
static id create(const char *cls) { assert(allocated<2048);id o=&objects[allocated++];o->cls=cls;return o; }
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
    if(!strcmp(name,"palette"))return (Ivar)(uintptr_t)offsetof(struct Fake,palette);
    if(!strcmp(name,"titleLabel"))return (Ivar)(uintptr_t)offsetof(struct Fake,title);
    const char *names[]={"$__lazy_storage_$_recentEmotesButton","$__lazy_storage_$_channelEmotesButton",
        "$__lazy_storage_$_allEmotesButton","recentEmotesHighlight","channelEmotesHighlight","allEmotesHighlight"};
    for(U i=0;i<6;i++)if(!strcmp(name,names[i]))return (Ivar)(uintptr_t)(offsetof(struct Fake,views)+i*sizeof(id));
    return NULL;
}
ptrdiff_t ivar_getOffset(Ivar iv) { return (ptrdiff_t)(uintptr_t)iv; }
size_t class_getInstanceSize(Class c) { (void)c;return sizeof(struct Fake); }
Method class_getInstanceMethod(Class c,SEL sel) { (void)sel;return c && c->encoding ? c : NULL; }
const char *method_getTypeEncoding(Method m) { return ((id)m)->encoding; }
id objc_retain(id o) { return o; }
void objc_release(id o) { (void)o; }
id objc_loadWeakRetained(id *p) { return *p; }
id objc_initWeak(id *p,id o) { *p=o;return o; }
void objc_destroyWeak(id *p) { *p=nil; }
id objc_getAssociatedObject(id o,const void *key) {
    if(!o)return nil;
    if(key==&state_key || key==&footer_key || key==&recent_host_key)return o->host;
    if(key==&button_key)return o->button;
    if(key==&library_highlight_key)return o->highlight;
    if(key==&inline_attributes_key)return o->marker;
    return nil;
}
void objc_setAssociatedObject(id o,const void *key,id value,uintptr_t policy) {
    assert(policy==1);
    if(key==&footer_key || key==&recent_host_key)o->host=value;
    else if(key==&button_key)o->button=value;
    else if(key==&library_highlight_key)o->highlight=value;
    else if(key==&inline_attributes_key)o->marker=value;
    else assert(!"unexpected association");
}
void *ss_test_field(id o,const char *name) {
    if(!strcmp(name,"frame"))return &o->frame;
    if(!strcmp(name,"bounds"))return &o->bounds;
    if(!strcmp(name,"contentInset"))return &o->inset;
    if(!strcmp(name,"adjustedContentInset"))return &o->adjusted;
    if(!strcmp(name,"contentOffset"))return &o->offset;
    if(!strcmp(name,"sectionInset"))return &o->inset;
    if(!strcmp(name,"collectionViewContentSize"))return &o->content_size;
    assert(!"unexpected geometry");return NULL;
}
void ss_test_frame(id o,Rect value) { o->frame=value;o->bounds.size=value.size; }
id ss_test_view(const char *cls,Rect value) { id o=create(cls);ss_test_frame(o,value);return o; }
id ss_test_collection(Rect value,id flow) { assert(flow);id o=ss_test_view("UICollectionView",value);o->flow=flow;flow->collection=o;return o; }
Rect ss_test_convert(id footer) { return footer->frame; }
id ss_test_constraint(id anchor,double value) { anchor->constant=value;return anchor; }
void ss_test_size(id flow,Size value) { flow->bounds.size=value; }
void ss_test_offset(id content,Point value) { content->offset=value;content->bounds.origin=value; }
void ss_test_offset_animated(id content,Point value,BOOL animated) { assert(!animated);ss_test_offset(content,value); }
void ss_test_inset(id content,Insets value) { content->inset=value;content->adjusted=value; }
static Insets native_inset(id self,SEL sel,id content,id flow,I section) {
    (void)self;(void)sel;(void)content;(void)flow;(void)section;return (Insets){8,0,8,0};
}
static I geometry_section;
Insets ss_test_section(id o) { return native_inset(o,"inset",o,o->flow,geometry_section); }
static void remove_child(id parent,id child) {
    if(!parent)return;
    for(U i=0;i<parent->count;i++)if(parent->children[i]==child) {
        memmove(parent->children+i,parent->children+i+1,(parent->count-i-1)*sizeof(id));parent->count--;break;
    }
}
static id dispatch(id o,SEL sel,...) {
    if(!o)return nil;va_list args;va_start(args,sel);id result=nil;
    if(!strcmp(sel,"respondsToSelector:")) { (void)va_arg(args,SEL);result=(id)1; }
    else if(!strcmp(sel,"isKindOfClass:")) { Class c=va_arg(args,Class);result=(id)(uintptr_t)(!strcmp(o->cls,c->cls)); }
    else if(!strcmp(sel,"new") || !strcmp(sel,"alloc"))result=create(o->cls);
    else if(!strcmp(sel,"stringWithUTF8String:")) { result=create("NSString");result->text=va_arg(args,const char *); }
    else if(!strcmp(sel,"isEqual:")) { id other=va_arg(args,id);result=(id)(uintptr_t)(o==other || (o->text && other->text && !strcmp(o->text,other->text))); }
    else if(!strcmp(sel,"systemImageNamed:")) { assert(va_arg(args,id));result=create("UIImage"); }
    else if(!strcmp(sel,"setImage:forState:")) { assert(va_arg(args,id));assert(!va_arg(args,U)); }
    else if(!strcmp(sel,"setAccessibilityLabel:") || !strcmp(sel,"setAccessibilityIdentifier:") || !strcmp(sel,"setText:"))o->text=va_arg(args,id)->text;
    else if(!strcmp(sel,"widthAnchor") || !strcmp(sel,"heightAnchor"))result=o;
    else if(!strcmp(sel,"setActive:"))o->active=(BOOL)va_arg(args,int);
    else if(!strcmp(sel,"setScrollEnabled:"))o->scroll_enabled=(BOOL)va_arg(args,int);
    else if(!strcmp(sel,"setScrollDirection:"))o->scroll_direction=va_arg(args,I);
    else if(!strcmp(sel,"setKeyboardDismissMode:"))assert(va_arg(args,I)==0);
    else if(!strcmp(sel,"setCanCancelContentTouches:") || !strcmp(sel,"setDelaysContentTouches:") ||
            !strcmp(sel,"setAlwaysBounceHorizontal:") || !strcmp(sel,"setAlwaysBounceVertical:") ||
            !strcmp(sel,"setDirectionalLockEnabled:") || !strcmp(sel,"setShowsHorizontalScrollIndicator:") ||
            !strcmp(sel,"setShowsVerticalScrollIndicator:")) {
        const char *names[]={"setCanCancelContentTouches:","setDelaysContentTouches:","setAlwaysBounceHorizontal:",
            "setAlwaysBounceVertical:","setDirectionalLockEnabled:","setShowsHorizontalScrollIndicator:","setShowsVerticalScrollIndicator:"};
        U i=0;while(strcmp(sel,names[i]))i++;o->scroll_options[i]=(BOOL)va_arg(args,int);
    }
    else if(!strcmp(sel,"setClipsToBounds:"))o->clips=(BOOL)va_arg(args,int);
    else if(!strcmp(sel,"setInvalidateFlowLayoutDelegateMetrics:"))o->metrics=(BOOL)va_arg(args,int);
    else if(!strcmp(sel,"setInvalidateFlowLayoutAttributes:"))o->attributes=(BOOL)va_arg(args,int);
    else if(!strcmp(sel,"setContentInsetAdjustmentBehavior:"))assert(va_arg(args,I)==2);
    else if(!strcmp(sel,"setTranslatesAutoresizingMaskIntoConstraints:") || !strcmp(sel,"setUserInteractionEnabled:") || !strcmp(sel,"setAlwaysBounceVertical:")) { (void)va_arg(args,int); }
    else if(!strcmp(sel,"setHidden:"))o->hidden=(BOOL)va_arg(args,int);
    else if(!strcmp(sel,"isHidden"))result=(id)(uintptr_t)o->hidden;
    else if(!strcmp(sel,"setSelected:"))o->selected=(U)va_arg(args,int);
    else if(!strcmp(sel,"setTintColor:"))o->tint=va_arg(args,id);
    else if(!strcmp(sel,"tintColor"))result=o->tint;
    else if(!strcmp(sel,"setBackgroundColor:"))o->background=va_arg(args,id);
    else if(!strcmp(sel,"backgroundColor"))result=o->background;
    else if(!strcmp(sel,"secondaryLabelColor") || !strcmp(sel,"labelColor") || !strcmp(sel,"systemPurpleColor") || !strcmp(sel,"secondarySystemBackgroundColor") || !strcmp(sel,"clearColor"))result=o;
    else if(!strcmp(sel,"boldSystemFontOfSize:"))result=o;
    else if(!strcmp(sel,"setFont:")) { assert(va_arg(args,id)); }
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
    else if(!strcmp(sel,"setMinimumInteritemSpacing:"))o->interitem_spacing=va_arg(args,double);
    else if(!strcmp(sel,"setMinimumLineSpacing:"))o->line_spacing=va_arg(args,double);
    else if(!strcmp(sel,"registerClass:forCellWithReuseIdentifier:")) { assert(va_arg(args,Class));assert(va_arg(args,id)); }
    else if(!strcmp(sel,"setDataSource:") || !strcmp(sel,"setDelegate:"))o->host=va_arg(args,id);
    else if(!strcmp(sel,"setTextAlignment:") || !strcmp(sel,"setNumberOfLines:")) { (void)va_arg(args,I); }
    else if(!strcmp(sel,"setTextColor:"))o->tint=va_arg(args,id);
    else if(!strcmp(sel,"reloadData"))o->reloads++;
    else if(!strcmp(sel,"visibleCells"))result=&empty;
    else if(!strcmp(sel,"numberOfSections"))result=(id)(uintptr_t)o->sections;
    else if(!strcmp(sel,"collectionViewLayout"))result=o->flow;
    else if(!strcmp(sel,"collectionView"))result=o->collection;
    else if(!strcmp(sel,"delegate"))result=o;
    /* Reproduce cached delegate metrics and already-applied native frames.
     * Ordinary invalidation must NOT magically query fresh section insets. */
    else if(!strcmp(sel,"invalidateLayout")) { }
    else if(!strcmp(sel,"invalidationContextClass"))result=objc_getClass("UICollectionViewFlowLayoutInvalidationContext");
    else if(!strcmp(sel,"invalidateLayoutWithContext:")) {
        id context=va_arg(args,id);assert(context->metrics && context->attributes);
        o->needs_metrics=YES;metric_invalidations++;
    } else if(!strcmp(sel,"setNeedsLayout")) { }
    else if(!strcmp(sel,"layoutIfNeeded")) {
        if(!o->heading && o->deferred_heading) {
            /* The supplementary view exists only after the first native
             * layout. A provider gap must not already have shifted Recent. */
            assert(!o->host->context->library_height);
            o->heading=o->deferred_heading;o->deferred_heading=nil;initial_header_layouts++;
        }
        id flow=o->flow;
        if(flow && flow->needs_metrics) {
            flow->needs_metrics=NO;
            for(I i=0;i<(I)o->sections;i++)flow->cached_sections[i]=native_inset(o,"inset",o,flow,i);
            I section=o->host ? o->host->context->library_section : 0;
            if(section<(I)o->sections) {
                id path=create("NSIndexPath");path->section=section;
                flow->applied_first=rect(flow_item(flow,"item",path),"frame");
            }
            flow->applied_size=flow_size(flow,"collectionViewContentSize");
        }
    }
    else if(!strcmp(sel,"sectionHeadersPinToVisibleBounds"))result=(id)1;
    else if(!strcmp(sel,"mainBundle"))result=o;
    else if(!strcmp(sel,"localizedStringForKey:value:table:")) { result=va_arg(args,id);(void)va_arg(args,id);(void)va_arg(args,id); }
    else if(!strcmp(sel,"text")) { result=create("NSString");result->text=o->text; }
    else if(!strcmp(sel,"length"))result=(id)(uintptr_t)(o->text ? strlen(o->text) : 0);
    else if(!strcmp(sel,"supplementaryViewForElementKind:atIndexPath:")) { (void)va_arg(args,id);(void)va_arg(args,id);result=o->heading; }
    else if(!strcmp(sel,"indexPathForItem:inSection:")) { result=create("NSIndexPath");result->selected=(U)va_arg(args,I);result->section=va_arg(args,I); }
    else if(!strcmp(sel,"numberOfItemsInSection:")) { I section=va_arg(args,I);result=(id)(uintptr_t)o->item_counts[section]; }
    else if(!strcmp(sel,"representedElementKind"))result=o->element_kind;
    else if(!strcmp(sel,"indexPath"))result=o->path;
    else if(!strcmp(sel,"section"))result=(id)(uintptr_t)o->section;
    else if(!strcmp(sel,"layoutAttributesForSupplementaryViewOfKind:atIndexPath:")) {
        id kind_name=va_arg(args,id),path=va_arg(args,id);result=flow_header(o,sel,kind_name,path);
    } else if(!strcmp(sel,"layoutAttributesForItemAtIndexPath:")) { id path=va_arg(args,id);result=flow_item(o,sel,path); }
    else if(!strcmp(sel,"copy") || !strcmp(sel,"autorelease")) {
        if(!strcmp(sel,"copy")) { result=create(o->cls);*result=*o; } else result=o;
    } else if(!strcmp(sel,"setZIndex:")) { assert(va_arg(args,I)==1024); }
    else assert(!"unexpected library selector");
    va_end(args);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
static id raw_item(id flow,SEL sel,id path) {
    (void)sel;geometry_section=path->section;id content=flow->collection;
    if(path->section>=(I)content->sections || !content->item_counts[path->section])return nil;
    id attributes=path->selected ? flow->last : flow->first;
    attributes->frame=(Rect){{0,path->section*236+content->header_heights[path->section]+8+(path->selected ? 120 : 0)},{56,56}};
    attributes->path=path;attributes->element_kind=nil;attributes->marker=nil;
    return attributes;
}
static id raw_header(id flow,SEL sel,id kind_name,id path) {
    (void)sel;geometry_section=path->section;id content=flow->collection;
    if(!content->header_heights[path->section])return nil;
    id attributes=flow->native_header;
    attributes->frame=(Rect){{0,path->section*236},{390,content->header_heights[path->section]}};
    attributes->path=path;attributes->element_kind=kind_name;attributes->marker=nil;
    return attributes;
}
static Size raw_size(id flow,SEL sel) { (void)sel;return flow->content_size; }
static id raw_elements(id flow,SEL sel,Rect query) {
    (void)sel;last_query=query;id array=create("NSMutableArray");
    for(I section=0;section<(I)flow->collection->sections;section++) {
        if(!flow->collection->item_counts[section])continue;
        id path=create("NSIndexPath");path->section=section;
        id item=raw_item(flow,"item",path);
        if(intersects(item->frame,query))array->children[array->count++]=m0(item,"copy");
        id header=raw_header(flow,"header",str("UICollectionElementKindSectionHeader"),path);
        if(header)array->children[array->count++]=m0(header,"copy");
    }
    return array;
}
id tas_emotes_picker_copy(id room,int provider,int scope,id query,size_t limit) {
    assert(room==expected_room && !query && limit==6500);assert(provider>=0 && provider<4 && scope>=0 && scope<2);
    last_provider=provider;last_scope=scope;queries++;return &datasets[provider][scope];
}
static void native_action(id o,SEL sel) {
    native_actions++;State *s=o->host->context;id content=s->recent_content;
    if(!strcmp(sel,"channelEmotesButtonPressed") || !strcmp(sel,"allEmotesButtonPressed"))
        ss_test_offset(content,(Point){0,s->library_start+s->library_height});
    else if(!strcmp(sel,"recentEmotesButtonPressed"))ss_test_offset(content,(Point){0,-content->adjusted.top});
}
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
    (void)preview_placeholder_image; /* Composer rendering is mocked in this library-only harness. */
    (void)attachment_metadata_key;(void)thumbnail_url_key;(void)thumbnail_record_key;(void)library_grid_class;
    (void)request_native_catalog;(void)unified_matches;(void)image_request;(void)visual_text;
    struct Fake normal={.cls="UIColor"},active={.cls="UIColor"},room={.cls="NSString"};expected_room=&room;
    State s={.room=&room,.recent_menu_open=YES};struct Fake delegate={.context=&s};delegate_class=&delegate;
    struct Fake owner={.cls=INPUT,.host=&delegate},container={.cls=CONTAINER,.parent=&owner,.bounds={{0,0},{390,300}}};owner.container=&container;
    struct Fake native={.cls=PALETTE,.parent=&container},footer={.cls=FOOTER,.parent=&container,.frame={{0,252},{390,48}},.bounds={{0,0},{390,48}}};
    struct Fake decoy={.cls="UICollectionView",.parent=&container};container.palette=&native;
    struct Fake first={.cls="UICollectionViewLayoutAttributes"},last={.cls="UICollectionViewLayoutAttributes"},header={.cls="UICollectionViewLayoutAttributes"};
    struct Fake flow={.cls="UICollectionViewFlowLayout",.collection=&native,.first=&first,.last=&last,.native_header=&header,.content_size={390,472}};
    for(U i=0;i<4;i++)flow.cached_sections[i]=(Insets){8,0,8,0};
    struct Fake title={.cls="UILabel",.text="Frequently Used"},heading={.cls=PALETTE_HEADER,.title=&title,.bounds={{0,0},{390,44}}};
    native.flow=&flow;native.bounds=(Rect){{0,0},{390,300}};native.sections=2;
    native.encoding="{UIEdgeInsets=dddd}40@0:8@16@24q32";native.host=&delegate;
    for(U i=0;i<4;i++) { native.item_counts[i]=3;native.header_heights[i]=44; }
    s.recent_content=&native;original_flow_item=(IMP)raw_item;original_flow_header=(IMP)raw_header;
    original_flow_size=(IMP)raw_size;original_flow_elements=(IMP)raw_elements;
    container.children[container.count++]=&decoy;container.children[container.count++]=&native;container.children[container.count++]=&footer;
    struct Fake buttons={.cls="UIStackView"},highlights={.cls="UIStackView"},views[6]={0};footer.stack=&buttons;footer.highlights=&highlights;
    for(U i=0;i<6;i++) { views[i].cls=i<3 ? "UIButton":"UIView";views[i].tint=&normal;footer.views[i]=&views[i]; }
    views[0].tint=&active;views[3].background=&active;
    rebuilt_stack(&buttons,&empty,&views[0],&views[1],&views[2]);rebuilt_stack(&highlights,&empty,&views[3],&views[4],&views[5]);
    s.owner=&owner;s.footer=&footer;
    bind_recents(&delegate,&container);assert(s.recent_content==&native && !decoy.host);
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
    /* The library exists inline before selecting its footer shortcut. */
    rebuilt_stack(&buttons,button,&views[0],&views[1],&views[2]);rebuilt_stack(&highlights,highlight,&views[3],&views[4],&views[5]);
    install_footer(&footer,&owner);make_panel(&delegate);refresh_library(&s);place_library_panel(&s,&native);
    /* No realized heading yet: leave native Recent in its own coordinates,
     * then complete the initial layout without requiring a user scroll. */
    assert(!s.library_height && s.panel->hidden && !metric_invalidations);
    title.text=NULL;native.deferred_heading=&heading;place_library_panel(&s,&native);
    assert(initial_header_layouts==1 && !s.library_height && s.panel->hidden && !s.recent_heading_observed);
    title.text="";place_library_panel(&s,&native);assert(!s.library_height && !s.recent_heading_observed);
    title.text="Frequently Used";heading.bounds.size.height=0;place_library_panel(&s,&native);
    assert(!s.library_height && s.panel->hidden && !s.recent_heading_observed);
    heading.bounds.size.height=44;place_library_panel(&s,&native);
    assert(initial_header_layouts==1 && s.library_section==1 && s.library_start==236);
    /* Image arrivals and timer ticks reuse the display snapshot. */
    U initial_queries=queries,initial_reloads=s.grid->reloads;
    for(int i=0;i<100;i++)refresh_library(&s);
    assert(queries==initial_queries && s.grid->reloads==initial_reloads);
    /* A catalog update invalidates even with unchanged room/provider/scope. */
    catalog_revision++;refresh_library(&s);assert(queries==initial_queries+1);
    struct Fake other_room={.cls="NSString"};
    s.room=&other_room;expected_room=&other_room;refresh_library(&s);assert(queries==initial_queries+2);
    s.room=&room;expected_room=&room;refresh_library(&s);assert(queries==initial_queries+3);
    assert(s.panel->parent==&native && !native.hidden && !s.tab && !button->selected);
    assert(s.library_section==1 && s.library_start==236 && s.library_height==410);
    native.heading=nil;place_library_panel(&s,&native);
    assert(s.library_section==1 && s.library_start==236 && initial_header_layouts==1); /* offscreen header recycling keeps the observation */
    native.heading=&heading;
    assert(metric_invalidations && s.panel->clips && s.grid->clips);
    assert(flow.cached_sections[1].top==8 && flow.applied_first.origin.y==698);
    assert(flow.applied_size.height==882 && flow.applied_size.width==390);
    assert(s.panel->frame.origin.y==236 && s.panel->frame.size.height==410);
    assert(header.frame.origin.y==236 && first.frame.origin.y==288); /* native caches and delegate insets stay native */
    third_party_tab(&delegate,"ssThirdParty:",button);
    assert(s.tab==1 && native.offset.y==236 && s.panel->parent==&native && !native.hidden);
    assert(s.provider->count==4 && s.scope->count==2 && s.grid->host==&delegate && s.grid->scroll_enabled);
    assert(s.grid->flow->scroll_direction==1 && s.grid->flow->bounds.size.height==56);
    assert(s.grid->flow->interitem_spacing==4 && s.grid->flow->line_spacing==4);
    assert(s.grid->scroll_options[0] && !s.grid->scroll_options[1] && s.grid->scroll_options[2]);
    assert(!s.grid->scroll_options[3] && s.grid->scroll_options[4] && s.grid->scroll_options[5] && !s.grid->scroll_options[6]);
    const char *providers[]={"All","7TV","BTTV","FFZ"};for(U i=0;i<4;i++)assert(!strcmp(s.provider->children[i]->text,providers[i]));
    assert(!strcmp(s.scope->children[0]->text,"Channel") && !strcmp(s.scope->children[1]->text,"Global"));
    assert(s.grid->frame.origin.y==106 && s.grid->frame.size.height==296);
    assert((s.grid->frame.size.height+s.grid->flow->interitem_spacing)/
        (s.grid->flow->bounds.size.height+s.grid->flow->interitem_spacing)==5);
    assert(button->selected && highlight->background==&active && !views[3].background && views[0].tint==&normal);
    for(int p=0;p<4;p++) {
        ss_test_offset(s.grid,(Point){600,0});
        s.scope->selected=1;scope_changed(&delegate,"ssScope:",s.scope);assert(last_scope==1);
        assert(!s.grid->offset.x && !s.grid->offset.y && native.offset.y==236);
        ss_test_offset(s.grid,(Point){1200,0});
        s.provider->selected=(U)p;provider_changed(&delegate,"ssProvider:",s.provider);
        assert(s.library==p && !s.library_scope && !s.scope->selected && last_provider==p && !last_scope);
        assert(!s.grid->offset.x && !s.grid->offset.y && native.offset.y==236);
        assert(item_count(&delegate,"collectionView:numberOfItemsInSection:",s.grid,0)==(I)datasets[p][0].count);
    }
    /* Extra entries add horizontal columns without moving native emotes down.
     * Outer scrolling, refreshes and rotation preserve horizontal browsing. */
    assert(s.library_height==410);
    ss_test_offset(s.grid,(Point){1000,0});
    ss_test_offset(&native,(Point){0,342});place_library_panel(&s,&native);
    assert(s.grid->offset.x==1000 && !s.grid->offset.y && s.grid->frame.origin.y==106 && s.grid->frame.size.height==296 && s.tab==1);
    assert(s.panel->frame.origin.y==236 && s.panel->frame.size.height==410);
    datasets[3][0].count=6500;refresh_library(&s);place_library_panel(&s,&native);
    assert(s.library_height==410 && s.grid->frame.size.height==296 && s.grid->offset.x==1000);
    assert(flow.cached_sections[1].top==8 && flow.applied_first.origin.y>=s.library_start+s.library_height);
    ss_test_offset(&native,(Point){0,30000});place_library_panel(&s,&native);
    assert(s.grid->offset.x==1000 && !s.grid->offset.y && s.grid->frame.size.height==296 && !s.tab);
    datasets[3][0].count=301;refresh_library(&s);ss_test_offset(&native,(Point){0,342});place_library_panel(&s,&native);
    assert(s.grid->offset.x==1000 && s.library_height==410);
    rebuilt_stack(&buttons,button,&views[0],&views[1],&views[2]);rebuilt_stack(&highlights,highlight,&views[3],&views[4],&views[5]);
    install_footer(&footer,&owner);assert(buttons.children[1]==button && button->selected && s.tab==1 && s.panel->parent==&native);
    struct Fake themed={.cls="UIColor"};original_footer_apply=(IMP)native_footer_apply;
    footer_apply(&footer,"apply:",&themed);
    assert(button->selected && highlight->background==&themed && !views[4].background && s.library==3 && !s.library_scope);
    native.bounds.size.width=844;place_library_panel(&s,&native);
    assert(s.grid->frame.size.width==836 && s.grid->frame.size.height==296 && s.library_height==410 && s.grid->offset.x==1000);
    for(U i=0;i<5;i++)original_footer_actions[i]=(IMP)native_action;
    footer_action(&footer,"backspaceButtonPressed");assert(s.tab==1 && !native.hidden);
    footer_action(&footer,"channelEmotesButtonPressed");
    assert(!s.tab && !native.hidden && s.panel->parent==&native && !button->selected && !highlight->background);
    assert(views[4].background==&themed && views[1].tint==&themed && native_actions==2);
    /* Scrolling back to the section highlights the shortcut automatically. */
    ss_test_offset(&native,(Point){0,s.library_start});place_library_panel(&s,&native);assert(button->selected && s.tab==1);
    footer.views[0]=nil;footer.views[3]=nil;footer_layout(&footer,"layoutSubviews");
    assert(buttons.children[0]==button && highlights.children[0]==highlight);
    third_party_tab(&delegate,"ssThirdParty:",button);
    assert(s.tab==1 && button->selected && highlight->background==&themed && !native.hidden);
    footer_action(&footer,"allEmotesButtonPressed");assert(!s.tab && !native.hidden && s.panel->parent==&native);
    /* Empty intermediate sets and missing headers must not swallow the gap. */
    native.sections=3;native.item_counts[1]=0;native.header_heights[2]=0;flow.content_size.height=664;
    place_library_panel(&s,&native);
    assert(s.library_section==2 && s.library_start==472 && flow.applied_first.origin.y==890);
    id section_path=create("NSIndexPath");section_path->section=2;
    id shifted=flow_item(&flow,"item",section_path);
    assert(shifted!=&first && shifted->frame.origin.y==890 && first.frame.origin.y==480);
    assert(inline_attributes(&flow,shifted)==shifted); /* never translate twice */
    Rect gap={{0,472},{390,300}};ss_test_offset(&native,gap.origin);
    id gap_items=flow_elements(&flow,"elements",gap);assert(!gap_items->count);
    Rect below={{0,882},{390,100}};ss_test_offset(&native,below.origin);
    id below_items=flow_elements(&flow,"elements",below);
    assert(last_query.origin.y==472 && last_query.size.height==100 && below_items->count==1);
    assert(below_items->children[0]->frame.origin.y==890);
    assert(flow_size(&flow,"size").height==1074); /* bottom of the provider library is part of native content size */
    /* Direct and array header queries agree and cannot cover the owned panel. */
    native.header_heights[2]=44;place_library_panel(&s,&native);
    id corrected=flow_header(&flow,"header",str("UICollectionElementKindSectionHeader"),section_path);
    assert(corrected->frame.origin.y==882 && header.frame.origin.y==472);
    assert(inline_attributes(&flow,corrected)==corrected);
    /* Native objects without our association retain their original geometry. */
    native.host=nil;assert(flow_item(&flow,"item",section_path)==&first && first.frame.origin.y==524);
    assert(flow_size(&flow,"size").height==664);native.host=&delegate;
    /* With only Recent present, layout content size reserves the library tail
     * without changing either native content inset. */
    native.sections=1;flow.content_size.height=236;native.inset.bottom=12;native.adjusted.bottom=12;
    place_library_panel(&s,&native);assert(native.inset.bottom==12 && s.library_start==236 && flow_size(&flow,"size").height==646);
    native.sections=2;native.item_counts[1]=3;title.text="Channel";flow.content_size.height=472;
    place_library_panel(&s,&native);
    assert(native.inset.bottom==12 && !s.library_section && !s.library_start);
    assert(flow.applied_first.origin.y==462); /* account emotes remain below the library */
    datasets[3][0].count=0;catalog_revision++;refresh_library(&s);place_library_panel(&s,&native);
    assert(s.library_height==178 && !s.empty->hidden);
    native.sections=0;flow.content_size.height=0;place_library_panel(&s,&native);
    assert(native.inset.bottom==12 && flow_size(&flow,"size").height==178);
    detach_recents(&s);assert(!s.panel->parent && !native.hidden && !s.library_height && native.inset.bottom==12);
    /* Cold headerless and empty collections still get an inline library. */
    assert(!s.recent_heading_observed);native.heading=nil;native.sections=2;
    native.header_heights[0]=0;native.item_counts[0]=3;flow.content_size.height=472;
    bind_recents(&delegate,&container);place_library_panel(&s,&native);
    assert(s.recent_heading_observed && s.library_section==0 && s.library_start==0 && s.library_height==178 && !s.panel->hidden);
    detach_recents(&s);native.sections=0;flow.content_size.height=0;
    bind_recents(&delegate,&container);place_library_panel(&s,&native);
    assert(s.library_height==178 && !s.panel->hidden && s.library_start==0);
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
    def test_inline_library_scroll_geometry_navigation_rebuild_and_scope_reset(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        source = composer.recent_geometry_source()
        source = replace_body(source, "static id delegate_for(id owner)", "return objc_getAssociatedObject(owner,&state_key);")
        source = replace_body(source, "static void refresh(id delegate)", "State *s=state(delegate);if(!s->panel)make_panel(delegate);refresh_library(s);place_library_panel(s,s->recent_content);")
        for signature, body in (("static void render(id delegate)", "(void)delegate;"),
                                ("static void expand(id delegate)", "(void)delegate;"),
                                ("static void start_tick(id delegate)", "(void)delegate;"),
                                ("static void set_thumbnail(id image_view,id metadata)", "(void)image_view;(void)metadata;")):
            source = replace_body(source, signature, body)
        source = source.replace('static id view(const char *c,Rect r) { return ((id (*)(id,SEL,Rect))objc_msgSend)(m0((id)objc_getClass(c),"alloc"),sel_registerName("initWithFrame:"),r); }',
            'extern id ss_test_view(const char *,Rect);\nextern id ss_test_collection(Rect,id);\nextern Rect ss_test_convert(id);\nextern id ss_test_constraint(id,double);\nextern void ss_test_size(id,Size);\nstatic id view(const char *c,Rect r) { return ss_test_view(c,r); }')
        source = source.replace('((id (*)(id,SEL,Rect,id))objc_msgSend)(m0((id)library_grid_class(),"alloc"),sel_registerName("initWithFrame:collectionViewLayout:"),(Rect){{0,106},{320,296}},flow)',
            'ss_test_collection((Rect){{0,106},{320,296}},flow)')
        source = source.replace('((void (*)(id,SEL,Size))objc_msgSend)(flow,sel_registerName("setItemSize:"),(Size){56,56})', 'ss_test_size(flow,(Size){56,56})')
        source = source.replace('((Rect (*)(id,SEL,Rect,id))objc_msgSend)(footer,sel_registerName("convertRect:toView:"),rect(footer,"bounds"),container)', 'ss_test_convert(footer)')
        source = source.replace('((id (*)(id,SEL,double))objc_msgSend)(m0(item,"widthAnchor"),sel_registerName("constraintEqualToConstant:"),width)', 'ss_test_constraint(m0(item,"widthAnchor"),width)')
        source = source.replace('((id (*)(id,SEL,double))objc_msgSend)(m0(highlight,"heightAnchor"),sel_registerName("constraintEqualToConstant:"),3.0)', 'ss_test_constraint(m0(highlight,"heightAnchor"),3.0)')
        composer.ComposerTests().compile_run(HARNESS.replace('#include "SSComposer.c"', source), [zig, "cc", "-fblocks"], runtime=True)
