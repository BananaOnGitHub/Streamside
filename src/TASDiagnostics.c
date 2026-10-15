#include "TASDiagnostics.h"
#include "TASImageDemand.h"
#include "TASPrivacy.h"
#include "TASEmotes.h"
#include "TASImageTransport.h"
#include "TASRNComposerUI.h"
#include "TASEmoteUI.h"
#include "SSComposer.h"
#include "TASEmoteProbe.h"
#include "TASEmoteImageProbe.h"
#ifndef TAS_CHAT_TRACE_DIAGNOSTIC
#define TAS_CHAT_TRACE_DIAGNOSTIC 0
#endif

#include <objc/objc.h>
#include <objc/runtime.h>
#include <objc/message.h>

#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

typedef unsigned long NSUInteger;
typedef long NSInteger;
typedef double CGFloat;

typedef struct {
    CGFloat x;
    CGFloat y;
} TASPoint;

typedef struct {
    CGFloat width;
    CGFloat height;
} TASSize;

typedef struct {
    TASPoint origin;
    TASSize size;
} TASRect;

#define TAS_DIAGNOSTICS_DIRECTORY "Streamside"
#define TAS_DIAGNOSTICS_FILENAME "diagnostics-r5.log"
#define TAS_REPORT_VERSION "3.1.0-build.12"
#define TAS_LOADED_NOTICE_KEY "TASLoadedNoticeShown220R8"
#define TAS_EMOTES_KEY "TASThirdPartyEmotesEnabled"

extern id objc_retain(id object);
extern void objc_release(id object);
extern void objc_setAssociatedObject(id object, const void *key, id value, uintptr_t policy);
extern id objc_getAssociatedObject(id object, const void *key);

static pthread_mutex_t g_diag_lock = PTHREAD_MUTEX_INITIALIZER;
static uint64_t g_metrics[TAS_DIAG_METRIC_COUNT];
#if TAS_EMOTE_DIAGNOSTIC
static char g_probe_notice_key;
#endif
static Class g_settings_class;
static Class g_diagnostic_settings_class;
static char g_diagnostic_selector_owner_key;
static Class g_log_class;
static IMP g_settings_super_view_did_load;
static IMP g_settings_super_view_will_appear;
static IMP g_log_super_view_did_load;
static IMP g_log_super_view_will_appear;
static IMP g_app_settings_original_view_did_appear;
static IMP g_view_controller_original_view_did_appear;
static IMP g_view_controller_original_present;
static IMP g_chat_settings_original_view_did_appear;
static bool g_chat_settings_hooked;
static IMP g_native_action_sheet_original_view_did_appear;
static bool g_native_action_sheet_hooked;
static IMP g_sheet_sections, g_sheet_rows, g_sheet_cell, g_sheet_select, g_sheet_header;
static char g_reload_sheet_key;
static uint64_t g_presented_sheets, g_chat_presenter_sheets;
static uint64_t g_chat_titled_sheets, g_chat_controller_appear, g_chat_controller_presented;
static uint64_t g_reload_actions_added;
static uint64_t g_native_action_sheets_seen, g_native_reload_buttons_added, g_native_reload_button_taps;
static uint64_t g_chat_button_taps, g_presented_controllers;
static uint64_t g_presented_navigation;
static IMP g_control_original_send_action;
static time_t g_chat_button_last_tap;
static char g_chat_button_target[96], g_chat_button_action[96];
static char g_last_presented_class[96], g_last_appeared_after_tap[96];
static char g_last_navigation_top[96], g_last_navigation_visible[96];
#define MENU_INC(value) ((void)__atomic_add_fetch(&(value), 1, __ATOMIC_RELAXED))
#define MENU_GET(value) __atomic_load_n(&(value), __ATOMIC_RELAXED)
static Class g_bootstrap_class;
static id g_bootstrap_observer;
static bool g_app_settings_hooked;
static char g_log_text_view_key;

static bool install_native_action_sheet_probe(void);

static id msg0(id object, const char *selector) {
    return ((id (*)(id, SEL))objc_msgSend)(object, sel_registerName(selector));
}

static id msg1(id object, const char *selector, id a) {
    return ((id (*)(id, SEL, id))objc_msgSend)(object, sel_registerName(selector), a);
}

static void vmsg1(id object, const char *selector, id a) {
    ((void (*)(id, SEL, id))objc_msgSend)(object, sel_registerName(selector), a);
}

static void vmsg_integer(id object, const char *selector, NSInteger value) {
    ((void (*)(id, SEL, NSInteger))objc_msgSend)(object, sel_registerName(selector), value);
}

static void vmsg_bool(id object, const char *selector, BOOL value) {
    ((void (*)(id, SEL, BOOL))objc_msgSend)(object, sel_registerName(selector), value);
}

static BOOL bmsg0(id object, const char *selector) {
    return ((BOOL (*)(id, SEL))objc_msgSend)(object, sel_registerName(selector));
}

static BOOL bmsg1(id object, const char *selector, id value) {
    return ((BOOL (*)(id, SEL, id))objc_msgSend)(object, sel_registerName(selector), value);
}

static NSInteger imsg0(id object, const char *selector) {
    return ((NSInteger (*)(id, SEL))objc_msgSend)(object, sel_registerName(selector));
}

static id nsstr(const char *value) {
    if (!value) value = "";
    return msg1((id)objc_getClass("NSString"), "stringWithUTF8String:", (id)value);
}

static const char *utf8(id value) {
    return value ? ((const char *(*)(id, SEL))objc_msgSend)(value, sel_registerName("UTF8String")) : NULL;
}

static id defaults(void) {
    return msg0((id)objc_getClass("NSUserDefaults"), "standardUserDefaults");
}

static unsigned saved_diagnostic_config(void) {
    id value=msg1(defaults(),"objectForKey:",nsstr(TAS_DIAG_CONFIG_KEY));
    if(!bmsg1(value,"isKindOfClass:",(id)objc_getClass("NSNumber")))return 1U;
    return value ? tas_diag_config_normalize((unsigned)imsg0(value,"unsignedIntValue")) : 1U;
}
void tas_diagnostics_load_preferences(void) {
    tas_diag_policy_initialize(saved_diagnostic_config());
}
static void save_diagnostic_config(unsigned word) {
    ((void (*)(id,SEL,NSInteger,id))objc_msgSend)(defaults(),sel_registerName("setInteger:forKey:"),
        (NSInteger)tas_diag_config_normalize(word),nsstr(TAS_DIAG_CONFIG_KEY));
}
static bool emotes_preference(void) {
    return bmsg1(defaults(), "boolForKey:", nsstr(TAS_EMOTES_KEY));
}
/* Delete obsolete logs once; never mix their labels/configuration into a new
 * process. New category rings are fixed-size, in-memory session evidence. */
static void remove_legacy_logs(void) {
    id manager=msg0((id)objc_getClass("NSFileManager"),"defaultManager");
    id urls=((id (*)(id,SEL,NSUInteger,NSUInteger))objc_msgSend)(manager,sel_registerName("URLsForDirectory:inDomains:"),14,1);
    id path=msg1(msg0(msg0(urls,"firstObject"),"path"),"stringByAppendingPathComponent:",nsstr(TAS_DIAGNOSTICS_DIRECTORY));
    if(!path)return;
    const char *names[]={"diagnostics.log",TAS_DIAGNOSTICS_FILENAME};
    for(unsigned i=0;i<2;i++) ((BOOL (*)(id,SEL,id,id *))objc_msgSend)(manager,sel_registerName("removeItemAtPath:error:"),msg1(path,"stringByAppendingPathComponent:",nsstr(names[i])),NULL);
}
void tas_diag_metric(TASDiagnosticMetric metric, uint64_t amount) {
    if (metric < 0 || metric >= TAS_DIAG_METRIC_COUNT) return;
    pthread_mutex_lock(&g_diag_lock);g_metrics[metric]+=amount;pthread_mutex_unlock(&g_diag_lock);
}
void tas_diag_log(const char *event,const char *detail) {
    unsigned category,level;tas_diag_classify(event,&category,&level);
    tas_diag_event_store(category,level,event,detail);
}
void tas_diag_log_url(const char *event,const char *url,const char *detail) {
    unsigned category,level;tas_diag_classify(event,&category,&level);
    if(!tas_diag_wants(category,level))return;
    char label[64],combined[384];tas_label_url(url,label,sizeof(label));
    snprintf(combined,sizeof(combined),"resource=%s%s%s",label,detail&&*detail?" ":"",detail?detail:"");
    tas_diag_log(event,combined);
}
void tas_diag_log_stream(const char *event,const char *channel,const char *url,const char *detail) {
    unsigned category,level;tas_diag_classify(event,&category,&level);
    if(!tas_diag_wants(category,level))return;
    char a[64],b[64],combined[384];tas_label_channel(channel,a,sizeof(a));tas_label_url(url,b,sizeof(b));
    snprintf(combined,sizeof(combined),"channel=%s resource=%s%s%s",a,b,detail&&*detail?" ":"",detail?detail:"");
    tas_diag_log(event,combined);
}
static void report_append(id report,const char *value) { vmsg1(report,"appendString:",nsstr(value)); }
static id diagnostic_report_create(void) {
    id bundle=msg0((id)objc_getClass("NSBundle"),"mainBundle");
    const char *version=utf8(msg1(bundle,"objectForInfoDictionaryKey:",nsstr("CFBundleShortVersionString")));
    const char *build=utf8(msg1(bundle,"objectForInfoDictionaryKey:",nsstr("CFBundleVersion")));
    char header[4096],config[2048];
    tas_diag_configuration_report(saved_diagnostic_config(),config,sizeof(config));
    snprintf(header,sizeof(header),"Streamside iOS diagnostic report\nPort build: %s\nTwitch: %s (%s)\n%s"
        "Privacy: no chat text, channel/room identities, full URLs/paths, headers, tokens or manifests. Labels reset each launch.\n"
        "Experimental modules compiled: emote=%d image-demand=%d chat-trace=%d\n"
        "All diagnostic changes apply after fully closing and relaunching Twitch. Functional interception stays enabled.\n",
        TAS_REPORT_VERSION,version?version:"unknown",build?build:"unknown",config,TAS_EMOTE_DIAGNOSTIC,TAS_IMAGE_DEMAND_DIAGNOSTIC,TAS_CHAT_TRACE_DIAGNOSTIC);
    id report=msg1((id)objc_getClass("NSMutableString"),"stringWithString:",nsstr(header));
    for(unsigned category=0;category<TAS_DIAG_CATEGORIES;category++) {
        if(!tas_diag_wants(category,TAS_DIAG_SUMMARY))continue;
        char text[8192];snprintf(text,sizeof(text),"\n--- %s ---\n",tas_diag_category_name(category));report_append(report,text);
        if(category==TAS_DIAG_GENERAL) {
            tas_emotes_status_category(category,text,sizeof(text));report_append(report,text);
            pthread_mutex_lock(&g_diag_lock);uint64_t hls=g_metrics[TAS_DIAG_HLS_FAILURE],tokens=g_metrics[TAS_DIAG_TOKEN_FAILURE];pthread_mutex_unlock(&g_diag_lock);
            snprintf(text,sizeof(text),"Essential failure counters: HLS=%llu access-token=%llu (no playback event details)\n",(unsigned long long)hls,(unsigned long long)tokens);report_append(report,text);
        }
        if(category==TAS_DIAG_PLAYBACK) {
            uint64_t m[TAS_DIAG_METRIC_COUNT];pthread_mutex_lock(&g_diag_lock);memcpy(m,g_metrics,sizeof(m));pthread_mutex_unlock(&g_diag_lock);
            snprintf(text,sizeof(text),"Operational counters (whole launch, even while logging is disabled):\n"
                "HLS intercepted: %llu\nMaster/variant/ad manifests: %llu/%llu/%llu\n"
                "Clean swaps/suppressed segments: %llu/%llu\nToken failures/unmapped variants: %llu/%llu\n"
                "Synthetic segments/GraphQL rewrites/HLS failures: %llu/%llu/%llu\n",
                (unsigned long long)m[0],(unsigned long long)m[1],(unsigned long long)m[2],(unsigned long long)m[3],
                (unsigned long long)m[4],(unsigned long long)m[5],(unsigned long long)m[6],(unsigned long long)m[7],
                (unsigned long long)m[8],(unsigned long long)m[9],(unsigned long long)m[10]);report_append(report,text);
        }
        if(category==TAS_DIAG_RENDERING || category==TAS_DIAG_CHAT || category==TAS_DIAG_COMPOSER) {
            tas_emotes_status_category(category,text,sizeof(text));report_append(report,text);
        }
        if(category==TAS_DIAG_IMAGES){tas_image_transport_status(text,sizeof(text));report_append(report,text);
#if TAS_EMOTE_DIAGNOSTIC
            if(tas_diag_wants(category,TAS_DIAG_DETAILED)){tas_image_probe_status(text,sizeof(text));report_append(report,text);}
#endif
        }
        if(category==TAS_DIAG_RENDERING){tas_emote_ui_status(text,sizeof(text));report_append(report,text);}
        if(category==TAS_DIAG_CHAT) report_append(report,TAS_CHAT_TRACE_DIAGNOSTIC?"Rolling trace compiled; Detailed required for collection.\n":"Rolling trace unavailable: not compiled into this build.\n");
        if(category==TAS_DIAG_COMPOSER) {
            ss_composer_status(text,sizeof(text));report_append(report,text);
            tas_rn_composer_ui_status(text,sizeof(text));report_append(report,text);
            snprintf(text,sizeof(text),"Settings integration: reload actions/row taps=%llu/%llu; native sheet hook=%s\n",(unsigned long long)MENU_GET(g_reload_actions_added),(unsigned long long)MENU_GET(g_native_reload_button_taps),g_native_action_sheet_hooked?"installed":"missing");report_append(report,text);
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
            if(tas_diag_wants(category,TAS_DIAG_DETAILED)){
                char demand[32768];tas_demand_status(demand,sizeof(demand));report_append(report,demand);
                ss_legacy_palette_status(text,sizeof(text));report_append(report,text);
            }
#endif
        }
#if TAS_EMOTE_DIAGNOSTIC
        if(category==TAS_DIAG_RENDERING && tas_diag_wants(category,TAS_DIAG_DETAILED)){
            char probe[16384];tas_emote_probe_status(probe,sizeof(probe));report_append(report,probe);
            if(strlen(probe)>=sizeof(probe)-1)report_append(report,"\n[emote probe export truncated: bounded buffer]\n");
        }
#endif
        tas_diag_events_report(category,text,sizeof(text));report_append(report,text);
    }
    return objc_retain(report);
}
static void clear_diagnostic_log(void) {
    tas_diag_events_clear();
    tas_diag_log("LOG_CLEARED","Session event rings cleared; operational counters and experimental traces unchanged");
}

static id make_bar_button(const char *title, id target, const char *action) {
    id item = msg0((id)objc_getClass("UIBarButtonItem"), "alloc");
    return ((id (*)(id, SEL, id, NSInteger, id, SEL))objc_msgSend)(
        item, sel_registerName("initWithTitle:style:target:action:"),
        nsstr(title), (NSInteger)0, target, sel_registerName(action));
}

static void show_notice(id controller, const char *title, const char *message) {
    id alert = ((id (*)(id, SEL, id, id, NSInteger))objc_msgSend)(
        (id)objc_getClass("UIAlertController"),
        sel_registerName("alertControllerWithTitle:message:preferredStyle:"),
        nsstr(title), nsstr(message), (NSInteger)1);
    id action = ((id (*)(id, SEL, id, NSInteger, id))objc_msgSend)(
        (id)objc_getClass("UIAlertAction"), sel_registerName("actionWithTitle:style:handler:"),
        nsstr("OK"), (NSInteger)0, nil);
    vmsg1(alert, "addAction:", action);
    ((void (*)(id, SEL, id, BOOL, id))objc_msgSend)(
        controller, sel_registerName("presentViewController:animated:completion:"), alert, YES, nil);
}

static id table_cell(NSInteger style) {
    id cell = msg0((id)objc_getClass("UITableViewCell"), "alloc");
    cell = ((id (*)(id, SEL, NSInteger, id))objc_msgSend)(
        cell, sel_registerName("initWithStyle:reuseIdentifier:"), style, nil);
    return cell;
}

static void set_cell_text(id cell, const char *title, const char *detail) {
    vmsg1(msg0(cell, "textLabel"), "setText:", nsstr(title));
    if (detail) vmsg1(msg0(cell, "detailTextLabel"), "setText:", nsstr(detail));
}

static void settings_view_did_load(id self, SEL command) {
    if (g_settings_super_view_did_load) {
        ((void (*)(id, SEL))g_settings_super_view_did_load)(self, command);
    }
    vmsg1(self, "setTitle:", nsstr("Streamside"));
}

static void settings_view_will_appear(id self, SEL command, BOOL animated) {
    if (g_settings_super_view_will_appear) {
        ((void (*)(id, SEL, BOOL))g_settings_super_view_will_appear)(self, command, animated);
    }
    msg0(msg0(self, "tableView"), "reloadData");
}

static NSInteger settings_number_of_sections(id self, SEL command, id table) {
    (void)self;
    (void)command;
    (void)table;
    return 3;
}

static NSInteger settings_rows_in_section(id self, SEL command, id table, NSInteger section) {
    (void)self;
    (void)command;
    (void)table;
    if (section == 0) return 1;
    if (section == 1) return 3;
    if (section == 2) return 1;
    return 0;
}

static id settings_header(id self, SEL command, id table, NSInteger section) {
    (void)self;
    (void)command;
    (void)table;
    if (section == 0) return nsstr("Status");
    if (section == 1) return nsstr("Third-Party Emotes");
    if (section == 2) return nsstr("Diagnostics");
    return nil;
}

static id settings_footer(id self, SEL command, id table, NSInteger section) {
    (void)self;
    (void)command;
    (void)table;
    if (section == 1) {
        return nsstr("7TV, BTTV and FFZ emotes in chat and the text box. Horizontal suggestions include Twitch and subscriber emotes and open automatically or with a colon. Off restores Twitch's suggestions. The emote button opens the library. Changes to the enable switch take effect after relaunching Twitch.");
    }
    return nil;
}

static id settings_cell(id self, SEL command, id table, id index_path) {
    (void)self;
    (void)command;
    (void)table;
    NSInteger section = imsg0(index_path, "section");
    NSInteger row = imsg0(index_path, "row");
    id cell = table_cell(1);
    if (section == 0) {
        set_cell_text(cell, "Ad Blocking", "Enabled · VAFT v24");
        vmsg_integer(cell, "setSelectionStyle:", 0);
    } else if (section == 1 && row == 0) {
        bool saved = emotes_preference();
        bool active = tas_emotes_enabled_this_launch();
        set_cell_text(cell, "Show Third-Party Emotes",
                      saved == active ? (active ? "Enabled" : "Disabled") :
                      (saved ? "On after relaunch" : "Off after relaunch"));
        id toggle = msg0(msg0((id)objc_getClass("UISwitch"), "alloc"), "init");
        ((void (*)(id, SEL, BOOL, BOOL))objc_msgSend)(
            toggle, sel_registerName("setOn:animated:"), saved ? YES : NO, NO);
        ((void (*)(id, SEL, id, SEL, NSUInteger))objc_msgSend)(
            toggle, sel_registerName("addTarget:action:forControlEvents:"),
            self, sel_registerName("tas_emotesSwitchChanged:"), (NSUInteger)(1UL << 12));
        vmsg1(toggle, "setAccessibilityIdentifier:", nsstr("TASEmotesSwitch"));
        vmsg1(cell, "setAccessoryView:", toggle);
        vmsg_integer(cell, "setSelectionStyle:", 0);
        objc_release(toggle);
    } else if (section == 1 && row == 1) {
        set_cell_text(cell, "Clear Emote Cache", "Clears stored third-party emote definitions");
    } else if (section == 1 && row == 2) {
        set_cell_text(cell, "Suggestions", "Emote names as you type");
        id items = msg0((id)objc_getClass("NSMutableArray"), "array");
        const char *labels[] = {"Auto", ":name", "Off"};
        for (int i = 0; i < 3; i++) vmsg1(items, "addObject:", nsstr(labels[i]));
        id control = msg1(msg0((id)objc_getClass("UISegmentedControl"), "alloc"), "initWithItems:", items);
        vmsg_integer(control, "setSelectedSegmentIndex:", ss_composer_suggestion_mode());
        ((void (*)(id, SEL, id, SEL, NSUInteger))objc_msgSend)(control,
            sel_registerName("addTarget:action:forControlEvents:"), self,
            sel_registerName("ss_suggestionsChanged:"), (NSUInteger)(1UL << 12));
        vmsg1(control, "setAccessibilityLabel:", nsstr("Emote suggestion mode"));
        vmsg1(cell, "setAccessoryView:", control); vmsg_integer(cell, "setSelectionStyle:", 0);
        objc_release(control);
    } else {
        unsigned saved=saved_diagnostic_config();
        char detail[96];snprintf(detail,sizeof(detail),"%s · %s",tas_diag_preset_name(tas_diag_preset_for(saved)),
            saved&TAS_DIAG_DETAIL_BIT?"Detailed":"Summary");
        set_cell_text(cell,"Diagnostics",detail);
        vmsg_integer(cell,"setAccessoryType:",1);
    }
    return msg0(cell, "autorelease");
}

static bool diagnostic_custom_selected(void) {
    return tas_diag_preset_for(saved_diagnostic_config())==TAS_DIAG_CUSTOM;
}

static bool diagnostic_restart_pending(void) {
    return ((saved_diagnostic_config()^tas_diag_policy_word())&~TAS_DIAG_CUSTOM_BIT)!=0;
}

static void diagnostic_settings_view_did_load(id self,SEL command) {
    if(g_settings_super_view_did_load)((void (*)(id,SEL))g_settings_super_view_did_load)(self,command);
    vmsg1(self,"setTitle:",nsstr("Diagnostics"));
}

static NSInteger diagnostic_settings_sections(id self,SEL command,id table) {
    (void)self;(void)command;(void)table;
    return diagnostic_custom_selected()?4:3;
}

static NSInteger diagnostic_settings_rows(id self,SEL command,id table,NSInteger section) {
    (void)self;(void)command;(void)table;
    if(section<2)return 1;
    if(section==2 && diagnostic_custom_selected())return TAS_DIAG_CATEGORIES;
    return TAS_EMOTE_DIAGNOSTIC?4:3;
}

static id diagnostic_settings_header(id self,SEL command,id table,NSInteger section) {
    (void)self;(void)command;(void)table;
    if(section==0)return nsstr("Preset");
    if(section==1)return nsstr("Detail");
    if(section==2 && diagnostic_custom_selected())return nsstr("Categories");
    return nsstr("Report");
}

static id diagnostic_settings_footer(id self,SEL command,id table,NSInteger section) {
    (void)self;(void)command;(void)table;
    if(section==0) {
        const char *descriptions[]={
            "General diagnostics with essential failures.",
            "General and Playback diagnostics for ad blocking.",
            "General, Rendering, Images and Composer diagnostics for emotes.",
            "General and Chat diagnostics for messages and redemptions.",
            "Choose individual diagnostic categories below."
        };
        return nsstr(descriptions[tas_diag_preset_for(saved_diagnostic_config())]);
    }
    if(section==1) {
        const char *detail=saved_diagnostic_config()&TAS_DIAG_DETAIL_BIT?
            "Bounded event traces and available experimental probes.":"Counters and essential failures.";
        char note[256];snprintf(note,sizeof(note),"%s%s",detail,diagnostic_restart_pending()?
            " Fully close and relaunch Twitch to apply changes.":"");
        return nsstr(note);
    }
    return nil;
}

static id diagnostic_settings_cell(id self,SEL command,id table,id index_path) {
    (void)command;(void)table;
    NSInteger section=imsg0(index_path,"section"),row=imsg0(index_path,"row");
    unsigned saved=saved_diagnostic_config();id cell=table_cell(1);
    if(section==0 || section==1) {
        set_cell_text(cell,section?"Detail":"Preset",section?(saved&TAS_DIAG_DETAIL_BIT?"Detailed":"Summary"):
            tas_diag_preset_name(tas_diag_preset_for(saved)));
        vmsg_integer(cell,"setAccessoryType:",1);
    } else if(section==2 && diagnostic_custom_selected()) {
        set_cell_text(cell,tas_diag_category_name((unsigned)row),NULL);
        vmsg_integer(msg0(cell,"textLabel"),"setNumberOfLines:",0);
        id toggle=msg0(msg0((id)objc_getClass("UISwitch"),"alloc"),"init");
        vmsg_integer(toggle,"setTag:",row);
        ((void (*)(id,SEL,BOOL,BOOL))objc_msgSend)(toggle,sel_registerName("setOn:animated:"),(saved&(1U<<row))?YES:NO,NO);
        ((void (*)(id,SEL,id,SEL,NSUInteger))objc_msgSend)(toggle,sel_registerName("addTarget:action:forControlEvents:"),self,sel_registerName("tas_diagnosticCategoryChanged:"),(NSUInteger)(1UL<<12));
        vmsg1(toggle,"setAccessibilityLabel:",nsstr(tas_diag_category_name((unsigned)row)));
        vmsg1(cell,"setAccessoryView:",toggle);vmsg_integer(cell,"setSelectionStyle:",0);objc_release(toggle);
    } else if(row==0) {
        set_cell_text(cell,"View Diagnostic Report",NULL);vmsg_integer(cell,"setAccessoryType:",1);
    } else if(row==1) set_cell_text(cell,"Copy Diagnostic Report",NULL);
    else if(row==2) set_cell_text(cell,"Clear Diagnostic Log",NULL);
    else set_cell_text(cell,"Inspect Emote","Rendering + Detailed required at launch");
    return msg0(cell,"autorelease");
}

static void diagnostic_select_option(bool preset,unsigned option) {
    unsigned word=saved_diagnostic_config();
    if(preset)word=option==TAS_DIAG_CUSTOM?word|TAS_DIAG_CUSTOM_BIT:tas_diag_preset_word(option);
    else word=option?word|TAS_DIAG_DETAIL_BIT:word&~TAS_DIAG_DETAIL_BIT;
    save_diagnostic_config(word);
}

static void diagnostic_show_selector(id self,id table,id index_path,bool preset) {
    id alert=((id (*)(id,SEL,id,id,NSInteger))objc_msgSend)((id)objc_getClass("UIAlertController"),
        sel_registerName("alertControllerWithTitle:message:preferredStyle:"),nsstr(preset?"Preset":"Detail"),nil,(NSInteger)0);
    /* Plain C blocks do not retain captured ObjC objects. The presented alert
     * owns the page until selection/cancellation; handlers borrow the alert. */
    objc_setAssociatedObject(alert,&g_diagnostic_selector_owner_key,self,1);
    unsigned saved=saved_diagnostic_config();
    unsigned selected=preset?tas_diag_preset_for(saved):((saved&TAS_DIAG_DETAIL_BIT)?1:0);
    for(unsigned option=0;option<(preset?5U:2U);option++) {
        const char *name=preset?tas_diag_preset_name(option):(option?"Detailed":"Summary");
        char title[96];snprintf(title,sizeof(title),"%s%s",option==selected?"✓ ":"",name);
        id action=((id (*)(id,SEL,id,NSInteger,id))objc_msgSend)((id)objc_getClass("UIAlertAction"),
            sel_registerName("actionWithTitle:style:handler:"),nsstr(title),(NSInteger)0,(id)^(id action) {
                (void)action;diagnostic_select_option(preset,option);
                id owner=objc_getAssociatedObject(alert,&g_diagnostic_selector_owner_key);
                msg0(msg0(owner,"tableView"),"reloadData");
            });
        vmsg1(alert,"addAction:",action);
    }
    id cancel=((id (*)(id,SEL,id,NSInteger,id))objc_msgSend)((id)objc_getClass("UIAlertAction"),
        sel_registerName("actionWithTitle:style:handler:"),nsstr("Cancel"),(NSInteger)1,nil);
    vmsg1(alert,"addAction:",cancel);
    id anchor=msg1(table,"cellForRowAtIndexPath:",index_path);if(!anchor)anchor=table;
    id popover=msg0(alert,"popoverPresentationController");
    vmsg1(popover,"setSourceView:",anchor);
    TASRect bounds=((TASRect (*)(id,SEL))objc_msgSend)(anchor,sel_registerName("bounds"));
    ((void (*)(id,SEL,TASRect))objc_msgSend)(popover,sel_registerName("setSourceRect:"),bounds);
    ((void (*)(id,SEL,id,BOOL,id))objc_msgSend)(self,sel_registerName("presentViewController:animated:completion:"),alert,YES,nil);
}

static void diagnostic_category_changed(id self,SEL command,id sender) {
    (void)command;NSInteger category=imsg0(sender,"tag");
    if(category<0 || category>=TAS_DIAG_CATEGORIES)return;
    unsigned word=saved_diagnostic_config()|TAS_DIAG_CUSTOM_BIT,bit=1U<<category;
    save_diagnostic_config(bmsg0(sender,"isOn")?word|bit:word&~bit);
    msg0(msg0(self,"tableView"),"reloadData");
}

static void emotes_switch_changed(id self, SEL command, id sender) {
    (void)command;
    ((void (*)(id, SEL, BOOL, id))objc_msgSend)(
        defaults(), sel_registerName("setBool:forKey:"), bmsg0(sender, "isOn"), nsstr(TAS_EMOTES_KEY));
    msg0(msg0(self, "tableView"), "reloadData");
}

static void suggestions_changed(id self, SEL command, id sender) {
    (void)self; (void)command;
    ss_composer_set_suggestion_mode((int)imsg0(sender, "selectedSegmentIndex"));
}

static void update_log_text(id self) {
    id text_view = objc_getAssociatedObject(self, &g_log_text_view_key);
    if (!text_view) return;
    id report = diagnostic_report_create();
    vmsg1(text_view, "setText:", report);
    objc_release(report);
}

static void log_copy(id self, SEL command) {
    (void)command;
    id report = diagnostic_report_create();
    vmsg1(msg0((id)objc_getClass("UIPasteboard"), "generalPasteboard"), "setString:", report);
    objc_release(report);
    show_notice(self, "Copied", "The diagnostic report was copied to the clipboard.");
}

static void log_view_did_load(id self, SEL command) {
    if (g_log_super_view_did_load) {
        ((void (*)(id, SEL))g_log_super_view_did_load)(self, command);
    }
    vmsg1(self, "setTitle:", nsstr("Diagnostic Report"));
    id parent = msg0(self, "view");
    TASRect bounds = ((TASRect (*)(id, SEL))objc_msgSend)(parent, sel_registerName("bounds"));
    id text_view = msg0((id)objc_getClass("UITextView"), "alloc");
    text_view = ((id (*)(id, SEL, TASRect))objc_msgSend)(
        text_view, sel_registerName("initWithFrame:"), bounds);
    vmsg_integer(text_view, "setAutoresizingMask:", (NSInteger)18);
    vmsg_bool(text_view, "setEditable:", NO);
    vmsg_bool(text_view, "setSelectable:", YES);
    vmsg_bool(text_view, "setAlwaysBounceVertical:", YES);
    id font = ((id (*)(id, SEL, CGFloat, CGFloat))objc_msgSend)(
        (id)objc_getClass("UIFont"), sel_registerName("monospacedSystemFontOfSize:weight:"),
        (CGFloat)12.0, (CGFloat)0.0);
    vmsg1(text_view, "setFont:", font);
    vmsg1(text_view, "setBackgroundColor:", msg0((id)objc_getClass("UIColor"), "systemBackgroundColor"));
    vmsg1(text_view, "setTextColor:", msg0((id)objc_getClass("UIColor"), "labelColor"));
    vmsg1(parent, "addSubview:", text_view);
    objc_setAssociatedObject(self, &g_log_text_view_key, text_view, 1);
    objc_release(text_view);

    id copy = make_bar_button("Copy", self, "tas_copyDiagnosticReport");
    vmsg1(msg0(self, "navigationItem"), "setRightBarButtonItem:", copy);
    objc_release(copy);
    update_log_text(self);
}

static void log_view_will_appear(id self, SEL command, BOOL animated) {
    if (g_log_super_view_will_appear) {
        ((void (*)(id, SEL, BOOL))g_log_super_view_will_appear)(self, command, animated);
    }
    update_log_text(self);
}

static void diagnostic_settings_did_select(id self, SEL command, id table, id index_path) {
    (void)command;
    NSInteger section = imsg0(index_path, "section");
    NSInteger row = imsg0(index_path, "row");
    ((void (*)(id, SEL, id, BOOL))objc_msgSend)(
        table, sel_registerName("deselectRowAtIndexPath:animated:"), index_path, YES);
#if TAS_EMOTE_DIAGNOSTIC
    if (section>=2 && !(section==2 && diagnostic_custom_selected()) && row==3) {
        if(!tas_diag_wants(TAS_DIAG_RENDERING,TAS_DIAG_DETAILED)) {
            show_notice(self,"Collection disabled","Choose Emotes or enable Emote Rendering + Detailed, then fully close and relaunch Twitch before starting a trace.");
            return;
        }
        id alert=((id (*)(id,SEL,id,id,NSInteger))objc_msgSend)((id)objc_getClass("UIAlertController"),
            sel_registerName("alertControllerWithTitle:message:preferredStyle:"),nsstr("Inspect Emote"),
            nsstr("Requires Emote Rendering + Detailed at launch. Entering a code includes that target in the report, but never chat messages. Compiled history is bounded, expires after ten minutes, and resets on relaunch."),(NSInteger)1);
        ((void (*)(id,SEL,id))objc_msgSend)(alert,sel_registerName("addTextFieldWithConfigurationHandler:"),(id)^(id field) {
            vmsg1(field,"setPlaceholder:",nsstr("Emote code (case sensitive)"));
            vmsg_integer(field,"setAutocorrectionType:",1);
            vmsg_integer(field,"setAutocapitalizationType:",0);
        });
        id field=objc_retain(msg0(msg0(alert,"textFields"),"firstObject"));
        id controller=objc_retain(self);
        id start=((id (*)(id,SEL,id,NSInteger,id))objc_msgSend)((id)objc_getClass("UIAlertAction"),
            sel_registerName("actionWithTitle:style:handler:"),nsstr("Start Trace"),(NSInteger)0,(id)^(id action) {
                (void)action;
                bool started=tas_emote_probe_set(utf8(msg0(field,"text")));
                if (started) tas_emote_ui_probe_start();
                objc_setAssociatedObject(controller,&g_probe_notice_key,
                    nsstr(started ? "History selected; copy diagnostic report" : "Invalid code; tap to retry"),1);
                msg0(msg0(controller,"tableView"),"reloadData");
                objc_release(field); objc_release(controller);
            });
        id cancel=((id (*)(id,SEL,id,NSInteger,id))objc_msgSend)((id)objc_getClass("UIAlertAction"),
            sel_registerName("actionWithTitle:style:handler:"),nsstr("Cancel"),(NSInteger)1,(id)^(id action) {
                (void)action; objc_release(field); objc_release(controller);
            });
        vmsg1(alert,"addAction:",start); vmsg1(alert,"addAction:",cancel);
        ((void (*)(id,SEL,id,BOOL,id))objc_msgSend)(self,sel_registerName("presentViewController:animated:completion:"),alert,YES,nil);
        return;
    }
#endif
    if(section<2) {diagnostic_show_selector(self,table,index_path,section==0);return;}
    if(section==2 && diagnostic_custom_selected())return;
    if (row == 0) {
        id controller = msg0((id)g_log_class, "new");
        ((void (*)(id, SEL, id, BOOL))objc_msgSend)(
            msg0(self, "navigationController"), sel_registerName("pushViewController:animated:"),
            controller, YES);
        objc_release(controller);
    } else if (row == 1) {
        id report = diagnostic_report_create();
        vmsg1(msg0((id)objc_getClass("UIPasteboard"), "generalPasteboard"), "setString:", report);
        objc_release(report);
        show_notice(self, "Copied", "The diagnostic report was copied to the clipboard.");
    } else if (row == 2) {
        clear_diagnostic_log();
        msg0(table, "reloadData");
        show_notice(self, "Cleared", "Session event rings cleared. Launch counters and experimental traces were preserved.");
    }
}

static void settings_did_select(id self,SEL command,id table,id index_path) {
    (void)command;
    NSInteger section=imsg0(index_path,"section"),row=imsg0(index_path,"row");
    ((void (*)(id,SEL,id,BOOL))objc_msgSend)(table,sel_registerName("deselectRowAtIndexPath:animated:"),index_path,YES);
    if(section==1 && row==1) {
        tas_emotes_clear_cache();
        show_notice(self,"Emote Cache Cleared","New chat messages will reload third-party emotes when you return to chat.");
    } else if(section==2 && g_diagnostic_settings_class) {
        id controller=msg0((id)g_diagnostic_settings_class,"alloc");
        controller=((id (*)(id,SEL,NSInteger))objc_msgSend)(controller,sel_registerName("initWithStyle:"),(NSInteger)2);
        ((void (*)(id,SEL,id,BOOL))objc_msgSend)(msg0(self,"navigationController"),sel_registerName("pushViewController:animated:"),controller,YES);
        objc_release(controller);
    }
}

static void open_ad_block_settings(id self, SEL command) {
    (void)command;
    if (g_settings_class && ((BOOL (*)(id, SEL, Class))objc_msgSend)(
            self, sel_registerName("isKindOfClass:"), g_settings_class)) return;

    id navigation = msg0(self, "navigationController");
    id controllers = msg0(navigation, "viewControllers");
    NSInteger count = imsg0(controllers, "count");
    for (NSInteger i = 0; i < count; i++) {
        id existing = ((id (*)(id, SEL, NSUInteger))objc_msgSend)(
            controllers, sel_registerName("objectAtIndex:"), (NSUInteger)i);
        if (g_settings_class && ((BOOL (*)(id, SEL, Class))objc_msgSend)(
                existing, sel_registerName("isKindOfClass:"), g_settings_class)) {
            ((id (*)(id, SEL, id, BOOL))objc_msgSend)(
                navigation, sel_registerName("popToViewController:animated:"), existing, YES);
            return;
        }
    }

    id controller = msg0((id)g_settings_class, "alloc");
    controller = ((id (*)(id, SEL, NSInteger))objc_msgSend)(
        controller, sel_registerName("initWithStyle:"), (NSInteger)2);
    ((void (*)(id, SEL, id, BOOL))objc_msgSend)(
        navigation, sel_registerName("pushViewController:animated:"), controller, YES);
    objc_release(controller);
}

static bool navigation_has_ad_block_item(id navigation_item) {
    id items = msg0(navigation_item, "rightBarButtonItems");
    NSInteger count = imsg0(items, "count");
    for (NSInteger i = 0; i < count; i++) {
        id item = ((id (*)(id, SEL, NSUInteger))objc_msgSend)(
            items, sel_registerName("objectAtIndex:"), (NSUInteger)i);
        if (bmsg1(msg0(item, "accessibilityIdentifier"), "isEqualToString:",
                  nsstr("TASAdBlockSettingsButton"))) return true;
    }
    return false;
}

static void add_ad_block_navigation_item(id controller) {
    id navigation_item = msg0(controller, "navigationItem");
    if (!navigation_item || navigation_has_ad_block_item(navigation_item)) return;
    id item = make_bar_button("Streamside", controller, "tas_openAdBlockSettings");
    vmsg1(item, "setAccessibilityIdentifier:", nsstr("TASAdBlockSettingsButton"));
    id existing = msg0(navigation_item, "rightBarButtonItems");
    id items = existing ? msg0(existing, "mutableCopy") : msg0((id)objc_getClass("NSMutableArray"), "array");
    vmsg1(items, "addObject:", item);
    ((void (*)(id, SEL, id, BOOL))objc_msgSend)(
        navigation_item, sel_registerName("setRightBarButtonItems:animated:"), items, NO);
    if (existing) objc_release(items);
    objc_release(item);
}

static Class app_settings_class(void);

static bool is_main_settings(id controller) {
    return bmsg1(msg0(controller, "title"), "isEqualToString:", nsstr("Settings"));
}

static void app_settings_view_did_appear(id self, SEL command, BOOL animated) {
    if (g_app_settings_original_view_did_appear) {
        ((void (*)(id, SEL, BOOL))g_app_settings_original_view_did_appear)(self, command, animated);
    }
    if (is_main_settings(self)) {
        add_ad_block_navigation_item(self);
    }
}

static Class app_settings_class(void) {
    Class result = objc_getClass("_TtC6Twitch25AppSettingsViewController");
    if (!result) result = objc_getClass("Twitch.AppSettingsViewController");
    if (!result) result = objc_getClass("AppSettingsViewController");
    return result;
}

static bool install_app_settings_hook(void) {
    if (g_app_settings_hooked) return true;
    Class app_settings = app_settings_class();
    if (!app_settings) return false;
    class_addMethod(app_settings, sel_registerName("tas_openAdBlockSettings"),
                    (IMP)open_ad_block_settings, "v@:");
    SEL selector = sel_registerName("viewDidAppear:");
    Method method = class_getInstanceMethod(app_settings, selector);
    if (!method) return false;
    g_app_settings_original_view_did_appear = method_getImplementation(method);
    const char *types = method_getTypeEncoding(method);
    if (!class_addMethod(app_settings, selector, (IMP)app_settings_view_did_appear, types)) {
        method_setImplementation(method, (IMP)app_settings_view_did_appear);
    }
    g_app_settings_hooked = true;
    return true;
}

/* AppSettingsViewController can register after the constructor runs. */
static void view_controller_view_did_appear(id self, SEL command, BOOL animated) {
    if (g_view_controller_original_view_did_appear) {
        ((void (*)(id, SEL, BOOL))g_view_controller_original_view_did_appear)(self, command, animated);
    }
    if (tas_emotes_enabled_this_launch() &&
        time(NULL) - g_chat_button_last_tap <= 5 && g_chat_button_last_tap) {
        if(tas_diag_wants(TAS_DIAG_COMPOSER,TAS_DIAG_DETAILED)) {
        pthread_mutex_lock(&g_diag_lock);
        snprintf(g_last_appeared_after_tap, sizeof(g_last_appeared_after_tap), "%s",
                 class_getName(object_getClass(self)));
        pthread_mutex_unlock(&g_diag_lock);
        }
    }
    if (!is_main_settings(self)) return;
    Class actual_class = object_getClass(self);
    class_addMethod(actual_class, sel_registerName("tas_openAdBlockSettings"),
                    (IMP)open_ad_block_settings, "v@:");
    if (app_settings_class()) install_app_settings_hook();
    add_ad_block_navigation_item(self);
}

static void present_controller(id self, SEL command, id presented, BOOL animated, id completion) {
    MENU_INC(g_presented_controllers);
    if (presented) {
        if(tas_diag_wants(TAS_DIAG_COMPOSER,TAS_DIAG_DETAILED)) {
        pthread_mutex_lock(&g_diag_lock);
        snprintf(g_last_presented_class, sizeof(g_last_presented_class), "%s",
                 class_getName(object_getClass(presented)));
        pthread_mutex_unlock(&g_diag_lock);
        }
    }
    Class chat_settings = objc_getClass("_TtC6Twitch22ChatSettingsController");
    bool from_chat_settings = chat_settings && bmsg1(self, "isKindOfClass:", (id)chat_settings);
    if (chat_settings && bmsg1(presented, "isKindOfClass:", (id)chat_settings))
        MENU_INC(g_chat_controller_presented);
    bool sheet = bmsg1(presented, "isKindOfClass:", (id)objc_getClass("UIAlertController")) &&
                 imsg0(presented, "preferredStyle") == 0;
    if (sheet) MENU_INC(g_presented_sheets);
    if (sheet && from_chat_settings) MENU_INC(g_chat_presenter_sheets);
    id title = sheet ? msg0(presented, "title") : nil;
    bool titled_chat_settings = title &&
        bmsg1(title, "localizedCaseInsensitiveContainsString:", nsstr("Chat Settings"));
    if (sheet && titled_chat_settings) MENU_INC(g_chat_titled_sheets);
    /* ChatSettingsController also creates or updates its own sheet. Matching
     * the presenter catches sheets whose title is absent or localized. */
    if (tas_emotes_enabled_this_launch() && sheet &&
        (from_chat_settings || titled_chat_settings)) {
        id actions = msg0(presented, "actions");
        bool present_already = false;
        for (NSInteger i = 0; i < imsg0(actions, "count"); i++) {
            id item = ((id (*)(id, SEL, NSUInteger))objc_msgSend)(
                actions, sel_registerName("objectAtIndex:"), (NSUInteger)i);
            if (bmsg1(msg0(item, "title"), "isEqualToString:", nsstr("Reload Emotes"))) {
                present_already = true;
                break;
            }
        }
        if (!present_already) {
            id action = ((id (*)(id, SEL, id, NSInteger, id))objc_msgSend)(
                (id)objc_getClass("UIAlertAction"),
                sel_registerName("actionWithTitle:style:handler:"),
                nsstr("Reload Emotes"), (NSInteger)0, (id)^(id selected) {
                    (void)selected;
                    tas_emotes_reload();
                });
            vmsg1(presented, "addAction:", action);
            MENU_INC(g_reload_actions_added);
        }
    }
    ((void (*)(id, SEL, id, BOOL, id))g_view_controller_original_present)(
        self, command, presented, animated, completion);
    if (tas_emotes_enabled_this_launch() &&
        bmsg1(presented, "isKindOfClass:", (id)objc_getClass("UINavigationController"))) {
        id top = msg0(presented, "topViewController");
        id visible = msg0(presented, "visibleViewController");
        MENU_INC(g_presented_navigation);
        if(tas_diag_wants(TAS_DIAG_COMPOSER,TAS_DIAG_DETAILED)) {
        pthread_mutex_lock(&g_diag_lock);
        snprintf(g_last_navigation_top, sizeof(g_last_navigation_top), "%s",
                 top ? class_getName(object_getClass(top)) : "none");
        snprintf(g_last_navigation_visible, sizeof(g_last_navigation_visible), "%s",
                 visible ? class_getName(object_getClass(visible)) : "none");
        pthread_mutex_unlock(&g_diag_lock);
        }
    }
}

static void control_send_action(id self, SEL command, SEL action, id target, id event) {
    id identifier = msg0(self, "accessibilityIdentifier");
    id label = msg0(self, "accessibilityLabel");
    bool chat_button = bmsg1(identifier, "isEqualToString:", nsstr("chat_settings_button")) ||
        bmsg1(label, "localizedCaseInsensitiveContainsString:", nsstr("Chat Settings"));
    if (chat_button) {
        MENU_INC(g_chat_button_taps);
        g_chat_button_last_tap = time(NULL);
        if(tas_diag_wants(TAS_DIAG_COMPOSER,TAS_DIAG_DETAILED)) {
        pthread_mutex_lock(&g_diag_lock);
        snprintf(g_chat_button_target, sizeof(g_chat_button_target), "%s",
                 target ? class_getName(object_getClass(target)) : "none");
        snprintf(g_chat_button_action, sizeof(g_chat_button_action), "%s",
                 action ? sel_getName(action) : "none");
        pthread_mutex_unlock(&g_diag_lock);
        }
    }
    ((void (*)(id, SEL, SEL, id, id))g_control_original_send_action)(
        self, command, action, target, event);
}

static void reload_emotes_button_tapped(id self, SEL command, id sender) {
    (void)self;
    (void)command;
    (void)sender;
    if (!tas_emotes_enabled_this_launch()) return;
    MENU_INC(g_native_reload_button_taps);
    tas_emotes_reload();
}

/* Append a real section to the native table. Existing section/row indices are
 * unchanged, and the table includes our row in its scrolling/content height. */
static bool reload_sheet(id self) {
    return objc_getAssociatedObject(self, &g_reload_sheet_key) != nil;
}
static NSInteger native_sections(id self, id table) {
    return ((NSInteger (*)(id, SEL, id))g_sheet_sections)(self,
        sel_registerName("numberOfSectionsInTableView:"), table);
}
static bool reload_section(id self, id table, NSInteger section) {
    return reload_sheet(self) && section == native_sections(self, table);
}
static NSInteger sheet_sections(id self, SEL sel, id table) {
    return ((NSInteger (*)(id, SEL, id))g_sheet_sections)(self, sel, table) + (reload_sheet(self) ? 1 : 0);
}
static NSInteger sheet_rows(id self, SEL sel, id table, NSInteger section) {
    if (reload_section(self, table, section)) return 1;
    return ((NSInteger (*)(id, SEL, id, NSInteger))g_sheet_rows)(self, sel, table, section);
}
static id sheet_header(id self, SEL sel, id table, NSInteger section) {
    if (reload_section(self, table, section)) return nil;
    return ((id (*)(id, SEL, id, NSInteger))g_sheet_header)(self, sel, table, section);
}
static id sheet_cell(id self, SEL sel, id table, id path) {
    if (!reload_section(self, table, imsg0(path, "section")))
        return ((id (*)(id, SEL, id, id))g_sheet_cell)(self, sel, table, path);
    id cell = msg1(table, "dequeueReusableCellWithIdentifier:", nsstr("TASReloadEmotesRow"));
    if (!cell) {
        cell = ((id (*)(id, SEL, NSInteger, id))objc_msgSend)(
            msg0((id)objc_getClass("UITableViewCell"), "alloc"),
            sel_registerName("initWithStyle:reuseIdentifier:"), (NSInteger)0, nsstr("TASReloadEmotesRow"));
        msg0(cell, "autorelease");
    }
    vmsg1(msg0(cell, "textLabel"), "setText:", nsstr("Reload Emotes"));
    vmsg1(msg0(cell, "textLabel"), "setTextColor:", msg0((id)objc_getClass("UIColor"), "labelColor"));
    vmsg1(cell, "setBackgroundColor:", msg0((id)objc_getClass("UIColor"), "secondarySystemBackgroundColor"));
    vmsg1(msg0(cell, "imageView"), "setImage:", msg1((id)objc_getClass("UIImage"), "systemImageNamed:", nsstr("arrow.clockwise")));
    vmsg1(cell, "setAccessibilityIdentifier:", nsstr("TASReloadEmotesChatMenuRow"));
    return cell;
}
static void sheet_select(id self, SEL sel, id table, id path) {
    if (!reload_section(self, table, imsg0(path, "section"))) {
        ((void (*)(id, SEL, id, id))g_sheet_select)(self, sel, table, path); return;
    }
    ((void (*)(id, SEL, id, BOOL))objc_msgSend)(table, sel_registerName("deselectRowAtIndexPath:animated:"), path, YES);
    MENU_INC(g_native_reload_button_taps);
    tas_emotes_reload();
    msg0(self, "close");
}
static id find_table(id view) {
    if (bmsg1(view, "isKindOfClass:", (id)objc_getClass("UITableView"))) return view;
    id children = msg0(view, "subviews");
    for (NSInteger i = 0; i < imsg0(children, "count"); i++) {
        id child = ((id (*)(id, SEL, NSUInteger))objc_msgSend)(children, sel_registerName("objectAtIndex:"), (NSUInteger)i);
        id table = find_table(child); if (table) return table;
    }
    return nil;
}
static bool add_native_reload_row(id controller) {
    if (reload_sheet(controller)) return true;
    id table = find_table(msg0(controller, "view"));
    if (!table) return false;
    objc_setAssociatedObject(controller, &g_reload_sheet_key, nsstr("reload"), 1);
    msg0(table, "reloadData");
    msg0(table, "layoutIfNeeded");
    msg0(msg0(controller, "view"), "setNeedsLayout");
    MENU_INC(g_native_reload_buttons_added);
    return true;
}

static void native_action_sheet_view_did_appear(id self, SEL command, BOOL animated) {
    if (g_native_action_sheet_original_view_did_appear)
        ((void (*)(id, SEL, BOOL))g_native_action_sheet_original_view_did_appear)(self, command, animated);
    MENU_INC(g_native_action_sheets_seen);
    if (tas_emotes_enabled_this_launch() && g_chat_button_last_tap &&
        time(NULL) - g_chat_button_last_tap <= 10) {
        if(tas_diag_wants(TAS_DIAG_COMPOSER,TAS_DIAG_DETAILED)) {
        pthread_mutex_lock(&g_diag_lock);
        snprintf(g_last_appeared_after_tap, sizeof(g_last_appeared_after_tap), "%s",
                 class_getName(object_getClass(self)));
        pthread_mutex_unlock(&g_diag_lock);
        }
        add_native_reload_row(self);
        g_chat_button_last_tap = 0;
    }
}

static bool install_native_action_sheet_probe(void) {
    if (g_native_action_sheet_hooked || !tas_emotes_enabled_this_launch())
        return g_native_action_sheet_hooked;
    Class cls = objc_getClass("_TtC12TwitchCoreUI25ActionSheetViewController");
    if (!cls) return false;
    SEL selector = sel_registerName("viewDidAppear:");
    Method method = class_getInstanceMethod(cls, selector);
    if (!method) return false;
    struct { const char *selector; IMP replacement; IMP *original; } hooks[] = {
        {"numberOfSectionsInTableView:", (IMP)sheet_sections, &g_sheet_sections},
        {"tableView:numberOfRowsInSection:", (IMP)sheet_rows, &g_sheet_rows},
        {"tableView:cellForRowAtIndexPath:", (IMP)sheet_cell, &g_sheet_cell},
        {"tableView:didSelectRowAtIndexPath:", (IMP)sheet_select, &g_sheet_select},
        {"tableView:viewForHeaderInSection:", (IMP)sheet_header, &g_sheet_header},
    };
    /* Validate the complete table surface before replacing any implementation. */
    for (size_t i = 0; i < sizeof(hooks)/sizeof(hooks[0]); i++)
        if (!class_getInstanceMethod(cls, sel_registerName(hooks[i].selector))) return false;
    g_native_action_sheet_original_view_did_appear = method_getImplementation(method);
    if (!class_addMethod(cls, selector, (IMP)native_action_sheet_view_did_appear,
                         method_getTypeEncoding(method)))
        method_setImplementation(method, (IMP)native_action_sheet_view_did_appear);
    for (size_t i = 0; i < sizeof(hooks)/sizeof(hooks[0]); i++) {
        SEL sel = sel_registerName(hooks[i].selector);
        Method m = class_getInstanceMethod(cls, sel);
        *hooks[i].original = method_getImplementation(m);
        if (!class_addMethod(cls, sel, hooks[i].replacement, method_getTypeEncoding(m)))
            method_setImplementation(m, hooks[i].replacement);
    }
    g_native_action_sheet_hooked = true;
    return true;
}

static void chat_settings_view_did_appear(id self, SEL command, BOOL animated) {
    ((void (*)(id, SEL, BOOL))g_chat_settings_original_view_did_appear)(self, command, animated);
    MENU_INC(g_chat_controller_appear);
}

static void install_chat_settings_probe(void) {
    if (g_chat_settings_hooked || !tas_emotes_enabled_this_launch()) return;
    Class cls = objc_getClass("_TtC6Twitch22ChatSettingsController");
    if (!cls) return;
    SEL selector = sel_registerName("viewDidAppear:");
    Method method = class_getInstanceMethod(cls, selector);
    if (!method) return;
    g_chat_settings_original_view_did_appear = method_getImplementation(method);
    if (!class_addMethod(cls, selector, (IMP)chat_settings_view_did_appear,
                         method_getTypeEncoding(method)))
        method_setImplementation(method, (IMP)chat_settings_view_did_appear);
    g_chat_settings_hooked = true;
}

static bool install_view_controller_fallback(void) {
    Class view_controller = objc_getClass("UIViewController");
    if (!view_controller) return false;
    Method method = class_getInstanceMethod(view_controller, sel_registerName("viewDidAppear:"));
    if (!method) return false;
    g_view_controller_original_view_did_appear = method_getImplementation(method);
    method_setImplementation(method, (IMP)view_controller_view_did_appear);
    if (tas_emotes_enabled_this_launch()) {
        Class control = objc_getClass("UIControl");
        Method send_action = class_getInstanceMethod(control, sel_registerName("sendAction:to:forEvent:"));
        if (send_action) {
            g_control_original_send_action = method_getImplementation(send_action);
            method_setImplementation(send_action, (IMP)control_send_action);
        }
        method = class_getInstanceMethod(view_controller, sel_registerName("presentViewController:animated:completion:"));
        if (method) {
            g_view_controller_original_present = method_getImplementation(method);
            method_setImplementation(method, (IMP)present_controller);
        }
    }
    return true;
}

static id visible_root_controller(void) {
    id application = msg0((id)objc_getClass("UIApplication"), "sharedApplication");
    id windows = msg0(application, "windows");
    NSInteger count = imsg0(windows, "count");
    id window = nil;
    for (NSInteger i = 0; i < count; i++) {
        id candidate = ((id (*)(id, SEL, NSUInteger))objc_msgSend)(
            windows, sel_registerName("objectAtIndex:"), (NSUInteger)i);
        if (bmsg0(candidate, "isKeyWindow")) {
            window = candidate;
            break;
        }
    }
    if (!window) window = msg0(windows, "firstObject");
    id controller = msg0(window, "rootViewController");
    for (int i = 0; controller && i < 12; i++) {
        id presented = msg0(controller, "presentedViewController");
        if (!presented) break;
        controller = presented;
    }
    return controller;
}

static void show_loaded_notice(id self, SEL command, id object) {
    (void)self;
    (void)command;
    (void)object;
    if (bmsg1(defaults(), "boolForKey:", nsstr(TAS_LOADED_NOTICE_KEY))) return;
    id controller = visible_root_controller();
    if (!controller) return;
    ((void (*)(id, SEL, BOOL, id))objc_msgSend)(
        defaults(), sel_registerName("setBool:forKey:"), YES, nsstr(TAS_LOADED_NOTICE_KEY));
    show_notice(controller, "VAFT loaded",
                "The VAFT module initialized. Open Profile → Settings, then tap Streamside.");
}

static void retry_app_settings_hook(id self, SEL command, id notification) {
    (void)command;
    (void)notification;
    tas_emotes_retry_hooks();
    tas_emote_ui_retry_hooks();
    ss_composer_retry_hooks();
    install_chat_settings_probe();
    install_native_action_sheet_probe();
    if (install_app_settings_hook()) {
        fprintf(stderr, "[TAS] AppSettingsViewController hook installed after application launch\n");
    }
    if (!bmsg1(defaults(), "boolForKey:", nsstr(TAS_LOADED_NOTICE_KEY))) {
        ((void (*)(id, SEL, SEL, id, double))objc_msgSend)(
            self, sel_registerName("performSelector:withObject:afterDelay:"),
            sel_registerName("tas_showLoadedNotice:"), nil, 1.25);
    }
}

static bool register_hook_retry_observer(void) {
    Class superclass = objc_getClass("NSObject");
    if (!superclass) return false;
    g_bootstrap_class = objc_allocateClassPair(superclass, "TASDiagnosticsBootstrap", 0);
    if (!g_bootstrap_class) g_bootstrap_class = objc_getClass("TASDiagnosticsBootstrap");
    if (!g_bootstrap_class) return false;
    if (!objc_getClass("TASDiagnosticsBootstrap")) {
        class_addMethod(g_bootstrap_class, sel_registerName("tas_retryAppSettingsHook:"),
                        (IMP)retry_app_settings_hook, "v@:@");
        class_addMethod(g_bootstrap_class, sel_registerName("tas_showLoadedNotice:"),
                        (IMP)show_loaded_notice, "v@:@");
        class_addMethod(g_bootstrap_class, sel_registerName("tas_reloadEmotesFromChatMenu:"),
                        (IMP)reload_emotes_button_tapped, "v@:@");
        objc_registerClassPair(g_bootstrap_class);
    }
    g_bootstrap_observer = msg0((id)g_bootstrap_class, "new");
    if (!g_bootstrap_observer) return false;
    id center = msg0((id)objc_getClass("NSNotificationCenter"), "defaultCenter");
    if (!center) return false;
    SEL add_observer = sel_registerName("addObserver:selector:name:object:");
    ((void (*)(id, SEL, id, SEL, id, id))objc_msgSend)(
        center, add_observer, g_bootstrap_observer, sel_registerName("tas_retryAppSettingsHook:"),
        nsstr("UIApplicationDidFinishLaunchingNotification"), nil);
    ((void (*)(id, SEL, id, SEL, id, id))objc_msgSend)(
        center, add_observer, g_bootstrap_observer, sel_registerName("tas_retryAppSettingsHook:"),
        nsstr("UIApplicationDidBecomeActiveNotification"), nil);
    return true;
}

static bool register_settings_class(void) {
    Class superclass = objc_getClass("UITableViewController");
    if (!superclass) return false;
    g_settings_super_view_did_load = method_getImplementation(
        class_getInstanceMethod(superclass, sel_registerName("viewDidLoad")));
    g_settings_super_view_will_appear = method_getImplementation(
        class_getInstanceMethod(superclass, sel_registerName("viewWillAppear:")));
    g_settings_class = objc_allocateClassPair(superclass, "TASAdBlockSettingsViewController", 0);
    if (!g_settings_class) g_settings_class = objc_getClass("TASAdBlockSettingsViewController");
    if (!g_settings_class) return false;
    if (!objc_getClass("TASAdBlockSettingsViewController")) {
        class_addMethod(g_settings_class, sel_registerName("viewDidLoad"), (IMP)settings_view_did_load, "v@:");
        class_addMethod(g_settings_class, sel_registerName("viewWillAppear:"), (IMP)settings_view_will_appear, "v@:B");
        class_addMethod(g_settings_class, sel_registerName("numberOfSectionsInTableView:"), (IMP)settings_number_of_sections, "q@:@");
        class_addMethod(g_settings_class, sel_registerName("tableView:numberOfRowsInSection:"), (IMP)settings_rows_in_section, "q@:@q");
        class_addMethod(g_settings_class, sel_registerName("tableView:titleForHeaderInSection:"), (IMP)settings_header, "@@:@q");
        class_addMethod(g_settings_class, sel_registerName("tableView:titleForFooterInSection:"), (IMP)settings_footer, "@@:@q");
        class_addMethod(g_settings_class, sel_registerName("tableView:cellForRowAtIndexPath:"), (IMP)settings_cell, "@@:@@");
        class_addMethod(g_settings_class, sel_registerName("tableView:didSelectRowAtIndexPath:"), (IMP)settings_did_select, "v@:@@");
        class_addMethod(g_settings_class, sel_registerName("ss_suggestionsChanged:"), (IMP)suggestions_changed, "v@:@");
        class_addMethod(g_settings_class, sel_registerName("tas_emotesSwitchChanged:"), (IMP)emotes_switch_changed, "v@:@");
        objc_registerClassPair(g_settings_class);
    }
    return true;
}

static bool register_diagnostic_settings_class(void) {
    Class superclass=objc_getClass("UITableViewController");if(!superclass)return false;
    g_diagnostic_settings_class=objc_allocateClassPair(superclass,"TASDiagnosticSettingsViewController",0);
    if(!g_diagnostic_settings_class)g_diagnostic_settings_class=objc_getClass("TASDiagnosticSettingsViewController");
    if(!g_diagnostic_settings_class)return false;
    if(!objc_getClass("TASDiagnosticSettingsViewController")) {
        class_addMethod(g_diagnostic_settings_class,sel_registerName("viewDidLoad"),(IMP)diagnostic_settings_view_did_load,"v@:");
        class_addMethod(g_diagnostic_settings_class,sel_registerName("viewWillAppear:"),(IMP)settings_view_will_appear,"v@:B");
        class_addMethod(g_diagnostic_settings_class,sel_registerName("numberOfSectionsInTableView:"),(IMP)diagnostic_settings_sections,"q@:@");
        class_addMethod(g_diagnostic_settings_class,sel_registerName("tableView:numberOfRowsInSection:"),(IMP)diagnostic_settings_rows,"q@:@q");
        class_addMethod(g_diagnostic_settings_class,sel_registerName("tableView:titleForHeaderInSection:"),(IMP)diagnostic_settings_header,"@@:@q");
        class_addMethod(g_diagnostic_settings_class,sel_registerName("tableView:titleForFooterInSection:"),(IMP)diagnostic_settings_footer,"@@:@q");
        class_addMethod(g_diagnostic_settings_class,sel_registerName("tableView:cellForRowAtIndexPath:"),(IMP)diagnostic_settings_cell,"@@:@@");
        class_addMethod(g_diagnostic_settings_class,sel_registerName("tableView:didSelectRowAtIndexPath:"),(IMP)diagnostic_settings_did_select,"v@:@@");
        class_addMethod(g_diagnostic_settings_class,sel_registerName("tas_diagnosticCategoryChanged:"),(IMP)diagnostic_category_changed,"v@:@");
        objc_registerClassPair(g_diagnostic_settings_class);
    }
    return true;
}

static bool register_log_class(void) {
    Class superclass = objc_getClass("UIViewController");
    if (!superclass) return false;
    g_log_super_view_did_load = method_getImplementation(
        class_getInstanceMethod(superclass, sel_registerName("viewDidLoad")));
    g_log_super_view_will_appear = method_getImplementation(
        class_getInstanceMethod(superclass, sel_registerName("viewWillAppear:")));
    g_log_class = objc_allocateClassPair(superclass, "TASDiagnosticLogViewController", 0);
    if (!g_log_class) g_log_class = objc_getClass("TASDiagnosticLogViewController");
    if (!g_log_class) return false;
    if (!objc_getClass("TASDiagnosticLogViewController")) {
        class_addMethod(g_log_class, sel_registerName("viewDidLoad"), (IMP)log_view_did_load, "v@:");
        class_addMethod(g_log_class, sel_registerName("viewWillAppear:"), (IMP)log_view_will_appear, "v@:B");
        class_addMethod(g_log_class, sel_registerName("tas_copyDiagnosticReport"), (IMP)log_copy, "v@:");
        objc_registerClassPair(g_log_class);
    }
    return true;
}

void tas_diagnostics_initialize(void) {
    remove_legacy_logs();
    bool settings_registered = register_settings_class();
    settings_registered = register_diagnostic_settings_class() && settings_registered;
    bool log_registered = register_log_class();
    bool fallback = install_view_controller_fallback();
    bool retry_registered = register_hook_retry_observer();
    install_native_action_sheet_probe();
    tas_emote_ui_retry_hooks();
    ss_composer_retry_hooks();
    bool hooked = settings_registered && log_registered && install_app_settings_hook();
    fprintf(stderr, "[TAS] diagnostics UI %s (AppSettings hook %s; fallback %s; retry %s)\n",
            settings_registered && log_registered ? "registered" : "unavailable",
            hooked ? "installed" : "deferred",
            fallback ? "installed" : "unavailable",
            retry_registered ? "registered" : "unavailable");
    if (retry_registered && !bmsg1(defaults(), "boolForKey:", nsstr(TAS_LOADED_NOTICE_KEY))) {
        ((void (*)(id, SEL, SEL, id, double))objc_msgSend)(
            g_bootstrap_observer, sel_registerName("performSelector:withObject:afterDelay:"),
            sel_registerName("tas_showLoadedNotice:"), nil, 1.25);
    }
    tas_diag_log("PORT_LOADED", "VAFT v24 iOS port initialized; diagnostics UI registration attempted");
}
