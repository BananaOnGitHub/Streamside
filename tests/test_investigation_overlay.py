"""Production capture overlay ownership, hit testing and teardown in a UIKit facade.

UIKit's real scene/compositing/keyboard behavior still requires a device.
Only the typed platform geometry returns are supplied by this host facade.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_investigation_startup import function

ROOT=Path(__file__).resolve().parent.parent

class OverlayTests(unittest.TestCase):
 def test_settings_transition_passthrough_capture_rotation_and_teardown(self):
  source=(ROOT/'src/TASInvestigationUI.c').read_text().replace('void tas_inv_ui_changed(void) {','static void tas_inv_ui_changed(void) {')
  selected='\n'.join(function(source,n) for n in ['can_key','overlay_hit','overlay_layout','hide','tas_inv_ui_changed','capture','background','scene_closed','show'])
  prelude=r"""
#include "TASInvestigation.h"
#include <assert.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
typedef struct Obj *id;typedef id Class;typedef const char *SEL;typedef void (*IMP)(void);
typedef unsigned char BOOL;
#define YES 1
#define NO 0
#define nil ((id)0)
typedef struct{double x,y,width,height;}Rect;
typedef struct{double top,left,bottom,right;}Insets;
typedef struct{double x,y;}Point;
struct Obj{const char *name;id view,window,scene,root,parent,object;Rect frame,bounds;Insets insets;double level;bool hidden,enabled,modal;unsigned releases;};
static struct Obj scene={.name="scene"},other_scene={.name="other-scene"};
static struct Obj host={.name="app-window",.scene=&scene,.frame={0,0,390,844}};
static struct Obj page_view={.name="settings",.window=&host},page={.name="page",.view=&page_view};
static struct Obj overlay={.name="overlay",.hidden=true},root_view={.name="root-view",.bounds={0,0,390,844},.insets={47,0,34,0}};
static struct Obj root_controller={.name="root-controller",.view=&root_view},native_button={.name="button"};
static struct Obj win_class={.name="window-class"},controller_class={.name="controller-class"},button_class={.name="button-class"},color_class={.name="color-class"};
static Class page_class=(id)1,overlay_window_class=&win_class,overlay_controller_class=&controller_class;
static IMP super_overlay_layout;
static id owner,page_weak,button,overlay_window;
static bool visible,report_started;static unsigned requests,last_request,reloads,changes_at_request;
static unsigned ui_changes;static TASInvStatus status;
static SEL sel_registerName(const char *s){return s;}
static Class objc_getClass(const char *s){if(!strcmp(s,"UIButton"))return &button_class;assert(!strcmp(s,"UIColor"));return &color_class;}
static id objc_retain(id o){return o;}
static void objc_release(id o){if(o)o->releases++;}
static id objc_loadWeakRetained(id *p){return *p;}
TASInvStatus tas_inv_status(void){return status;}
static bool tas_inv_report_started(unsigned g,unsigned s){(void)g;(void)s;return report_started;}
static bool request(unsigned op){requests++;last_request=op;changes_at_request=ui_changes;return true;}
static bool (*tas_inv_host_request)(unsigned)=request;
static void tas_inv_ui_changed(void);
static void overlay_layout(id,SEL);
static id send(id o,SEL sel,...){
 if(!o)return nil;
 va_list a;va_start(a,sel);id result=nil;
 if(!strcmp(sel,"alloc")){assert(o==&win_class);result=&overlay;}
 else if(!strcmp(sel,"new")){assert(o==&controller_class);result=&root_controller;}
 else if(!strcmp(sel,"initWithWindowScene:")){assert(o==&overlay);o->scene=va_arg(a,id);result=o;}
 else if(!strcmp(sel,"buttonWithType:")){assert(o==&button_class);assert(va_arg(a,long)==1);result=&native_button;}
 else if(!strcmp(sel,"setFrame:")){o->frame=va_arg(a,Rect);ui_changes++;}
 else if(!strcmp(sel,"setWindowLevel:")){o->level=va_arg(a,double);}
 else if(!strcmp(sel,"setHidden:")){o->hidden=va_arg(a,int);ui_changes++;}
 else if(!strcmp(sel,"setEnabled:")){o->enabled=va_arg(a,int);ui_changes++;}
 else if(!strcmp(sel,"setAccessibilityViewIsModal:")){o->modal=va_arg(a,int);}
 else if(!strcmp(sel,"setRootViewController:")){o->root=va_arg(a,id);}
 else if(!strcmp(sel,"addSubview:")){id v=va_arg(a,id);v->parent=o;}
 else if(!strcmp(sel,"removeFromSuperview")){o->parent=nil;}
 else if(!strcmp(sel,"view"))result=o->view;
 else if(!strcmp(sel,"window"))result=o->window;
 else if(!strcmp(sel,"windowScene"))result=o->scene;
 else if(!strcmp(sel,"rootViewController"))result=o->root;
 else if(!strcmp(sel,"object"))result=o->object;
 else if(!strcmp(sel,"tableView"))result=o;
 else if(!strcmp(sel,"reloadData"))reloads++;
 else if(!strcmp(sel,"layoutIfNeeded"))overlay_layout(&root_controller,"viewDidLayoutSubviews");
 else if(!strcmp(sel,"setNeedsLayout")){}
 else if(!strcmp(sel,"hitTest:withEvent:")){
  assert(o==&native_button);Point p=va_arg(a,Point);(void)va_arg(a,id);
  if(!o->hidden && p.x>=0 && p.y>=0 && p.x<o->frame.width && p.y<o->frame.height)result=o;
 }
 else if(!strcmp(sel,"clearColor") || !strcmp(sel,"secondarySystemBackgroundColor"))result=o;
 else if(!strcmp(sel,"setBackgroundColor:") || !strcmp(sel,"setAccessibilityLabel:") || !strcmp(sel,"addTarget:action:forControlEvents:")){}
 else {assert(!"unexpected UIKit action (including focus/key-window changes)");}
 va_end(a);return result;
}
static id (*objc_msgSend)(id,SEL,...)=send;
static id m0(id o,const char *s){return send(o,s);}
static id m1(id o,const char *s,id a){return send(o,s,a);}
static id ns(const char *s){return (id)s;}
static void title(id o,const char *s){(void)o;(void)s;ui_changes++;}
static Rect rect(id o,const char *s){assert(o);return !strcmp(s,"frame")?o->frame:o->bounds;}
static Insets safe_insets(id o){return o->insets;}
static Point button_point(id w,Point p){assert(w==overlay_window);return (Point){p.x-button->frame.x,p.y-button->frame.y};}
"""
  main=r"""
int main(void){
 // The toggle cannot create an overlay before the investigation is armed.
 status.state=TAS_INV_DORMANT;show(&page);assert(!visible && !overlay_window);
 status.state=TAS_INV_ARMED;status.pending=TAS_INV_ARM;show(&page);assert(!visible);
 status.pending=0;host.scene=nil;show(&page);assert(!visible);host.scene=&scene;
 show(&page);assert(visible && overlay_window==&overlay && overlay.scene==&scene);
 assert(!can_key(&overlay,0) && !overlay.hidden && overlay.level>host.level);
 assert(overlay.root==&root_controller && button->parent==&root_view && !root_view.modal && button->enabled);
 assert(button->frame.x==294 && button->frame.y==55 && button->frame.width==88 && button->frame.height==44);
 id first=overlay_window;show(&page);assert(overlay_window==first);
 // Dismiss settings and replace/reorder the app's normal root content.
 page_view.window=nil;host.root=&other_scene;page_weak=nil;
 assert(visible && button->parent==&root_view && overlay.root==&root_controller);
 assert(overlay_hit(&overlay,0,(Point){300,60},nil)==button);
 assert(!overlay_hit(&overlay,0,(Point){100,400},nil));
 assert(!overlay_hit(&host,0,(Point){300,60},nil));
 assert(!overlay_hit(&overlay,0,(Point){382,60},nil));
 capture(nil,0,nil);assert(last_request==TAS_INV_CAPTURE && requests==1 && changes_at_request<ui_changes);
 // Preserve the first-transfer boundary; UI work cannot precede frozen history.
 status.pending=TAS_INV_CAPTURE;status.state=TAS_INV_CAPTURING;
 unsigned before=ui_changes;tas_inv_ui_changed();assert(ui_changes==before);
 report_started=true;tas_inv_ui_changed();assert(!button->enabled);
 status.pending=0;status.state=TAS_INV_ARMED;tas_inv_ui_changed();assert(button->enabled);
 // Native layout callbacks adapt the action to rotation and safe-area changes.
 root_view.bounds=(Rect){0,0,844,390};root_view.insets=(Insets){0,47,21,47};
 overlay_layout(&root_controller,"viewDidLayoutSubviews");assert(button->frame.x==701 && button->frame.y==8);
 assert(overlay_hit(&overlay,0,(Point){710,20},nil)==button);
 struct Obj note={.object=&other_scene};scene_closed(nil,0,&note);assert(visible && requests==1);
 note.object=&scene;scene_closed(nil,0,&note);assert(!visible && !button && !overlay_window && overlay.hidden);
 assert(last_request==TAS_INV_STOP && requests==2 && !overlay.root && !native_button.parent);
 assert(!overlay_hit(&overlay,0,(Point){710,20},nil));
 // Stop/readiness loss clears the same objects without waiting for navigation.
 page_view.window=&host;show(&page);assert(visible);
 status.state=TAS_INV_DORMANT;tas_inv_ui_changed();assert(!visible && !overlay_window);
 status.state=TAS_INV_ARMED;show(&page);assert(visible);
 background(nil,0,nil);assert(!visible && last_request==TAS_INV_STOP && requests==3);
}
"""
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'overlay.c';exe=Path(folder)/'overlay';path.write_text(prelude+selected+main)
   subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-cast-function-type','-I',str(ROOT/'src'),str(path),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
