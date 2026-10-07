#include "TASDiagnostics.h"
#include "TASPrivacy.h"
#include "TASEmotes.h"
#include "TASEmoteUI.h"
#include "SSComposer.h"
#include "TASEmoteProbe.h"

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

#define TAS_DIAGNOSTICS_KEY "TASDiagnosticsEnabled"
#define TAS_DIAGNOSTICS_DIRECTORY "Streamside"
#define TAS_DIAGNOSTICS_FILENAME "diagnostics-r5.log"
#define TAS_DIAGNOSTICS_LIMIT (512ULL * 1024ULL)
#define TAS_REPORT_VERSION "3.0.0-build.60"
#define TAS_LOADED_NOTICE_KEY "TASLoadedNoticeShown220R8"
#define TAS_EMOTES_KEY "TASThirdPartyEmotesEnabled"

extern id objc_retain(id object);
extern void objc_release(id object);
extern void objc_setAssociatedObject(id object, const void *key, id value, uintptr_t policy);
extern id objc_getAssociatedObject(id object, const void *key);

static pthread_mutex_t g_diag_lock = PTHREAD_MUTEX_INITIALIZER;
static uint64_t g_metrics[TAS_DIAG_METRIC_COUNT];
static uint64_t g_logged_events;
static id g_diagnostics_path;
#if TAS_EMOTE_DIAGNOSTIC
static char g_probe_notice_key;
#endif
static Class g_settings_class;
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

static id data_from_bytes(const void *bytes, size_t length) {
    return ((id (*)(id, SEL, const void *, NSUInteger))objc_msgSend)(
        (id)objc_getClass("NSData"), sel_registerName("dataWithBytes:length:"), bytes, (NSUInteger)length);
}

static size_t data_length(id data) {
    return data ? (size_t)((NSUInteger (*)(id, SEL))objc_msgSend)(data, sel_registerName("length")) : 0;
}

static id defaults(void) {
    return msg0((id)objc_getClass("NSUserDefaults"), "standardUserDefaults");
}

static bool diagnostics_enabled(void) {
    return bmsg1(defaults(), "boolForKey:", nsstr(TAS_DIAGNOSTICS_KEY));
}

static bool emotes_preference(void) {
    return bmsg1(defaults(), "boolForKey:", nsstr(TAS_EMOTES_KEY));
}

static void set_diagnostics_enabled(bool enabled) {
    ((void (*)(id, SEL, BOOL, id))objc_msgSend)(
        defaults(), sel_registerName("setBool:forKey:"), enabled ? YES : NO, nsstr(TAS_DIAGNOSTICS_KEY));
}

static id diagnostics_path_locked(void) {
    if (g_diagnostics_path) return g_diagnostics_path;

    id manager = msg0((id)objc_getClass("NSFileManager"), "defaultManager");
    id urls = ((id (*)(id, SEL, NSUInteger, NSUInteger))objc_msgSend)(
        manager, sel_registerName("URLsForDirectory:inDomains:"), (NSUInteger)14, (NSUInteger)1);
    id base_url = msg0(urls, "firstObject");
    id base_path = msg0(base_url, "path");
    if (!base_path) {
        id environment = msg0(msg0((id)objc_getClass("NSProcessInfo"), "processInfo"), "environment");
        id home = msg1(environment, "objectForKey:", nsstr("HOME"));
        base_path = msg1(home, "stringByAppendingPathComponent:", nsstr("Library/Application Support"));
    }
    if (!base_path) return nil;

    id directory = msg1(base_path, "stringByAppendingPathComponent:", nsstr(TAS_DIAGNOSTICS_DIRECTORY));
    ((BOOL (*)(id, SEL, id, BOOL, id, id *))objc_msgSend)(
        manager, sel_registerName("createDirectoryAtPath:withIntermediateDirectories:attributes:error:"),
        directory, YES, nil, NULL);
    /* 2.2.0 wrote URL paths. Remove that file before showing a report. */
    id legacy_path = msg1(directory, "stringByAppendingPathComponent:", nsstr("diagnostics.log"));
    ((BOOL (*)(id, SEL, id, id *))objc_msgSend)(
        manager, sel_registerName("removeItemAtPath:error:"), legacy_path, NULL);
    id path = msg1(directory, "stringByAppendingPathComponent:", nsstr(TAS_DIAGNOSTICS_FILENAME));
    g_diagnostics_path = objc_retain(path);
    return g_diagnostics_path;
}

void tas_diag_metric(TASDiagnosticMetric metric, uint64_t amount) {
    if (metric < 0 || metric >= TAS_DIAG_METRIC_COUNT) return;
    pthread_mutex_lock(&g_diag_lock);
    g_metrics[metric] += amount;
    pthread_mutex_unlock(&g_diag_lock);
}

static void append_log_line_locked(const char *line) {
    id path = diagnostics_path_locked();
    if (!path) return;
    id manager = msg0((id)objc_getClass("NSFileManager"), "defaultManager");
    id handle = msg1((id)objc_getClass("NSFileHandle"), "fileHandleForWritingAtPath:", path);
    if (!handle) {
        ((BOOL (*)(id, SEL, id, id, id))objc_msgSend)(
            manager, sel_registerName("createFileAtPath:contents:attributes:"),
            path, data_from_bytes("", 0), nil);
        handle = msg1((id)objc_getClass("NSFileHandle"), "fileHandleForWritingAtPath:", path);
    }
    if (!handle) return;

    unsigned long long offset = ((unsigned long long (*)(id, SEL))objc_msgSend)(
        handle, sel_registerName("seekToEndOfFile"));
    if (offset >= TAS_DIAGNOSTICS_LIMIT) {
        ((void (*)(id, SEL, unsigned long long))objc_msgSend)(
            handle, sel_registerName("truncateFileAtOffset:"), 0ULL);
        ((void (*)(id, SEL, unsigned long long))objc_msgSend)(
            handle, sel_registerName("seekToFileOffset:"), 0ULL);
        char rotated[160];
        snprintf(rotated, sizeof(rotated), "[%lld] LOG_ROTATED previous log exceeded 512 KiB\n",
                 (long long)time(NULL));
        vmsg1(handle, "writeData:", data_from_bytes(rotated, strlen(rotated)));
    }
    vmsg1(handle, "writeData:", data_from_bytes(line, strlen(line)));
    msg0(handle, "synchronizeFile");
    msg0(handle, "closeFile");
}

void tas_diag_log(const char *event, const char *detail) {
    if (!diagnostics_enabled()) return;
    char line[2048];
    snprintf(line, sizeof(line), "[%lld] %s%s%s\n", (long long)time(NULL),
             event ? event : "EVENT", detail && detail[0] ? " " : "", detail ? detail : "");
    pthread_mutex_lock(&g_diag_lock);
    g_logged_events++;
    append_log_line_locked(line);
    pthread_mutex_unlock(&g_diag_lock);
}

void tas_diag_log_url(const char *event, const char *url, const char *detail) {
    if (!diagnostics_enabled()) return;
    char label[64];
    char combined[1536];
    tas_label_url(url, label, sizeof(label));
    snprintf(combined, sizeof(combined), "resource=%s%s%s", label,
             detail && detail[0] ? " " : "", detail ? detail : "");
    tas_diag_log(event, combined);
}

void tas_diag_log_stream(const char *event, const char *channel, const char *url,
                         const char *detail) {
    if (!diagnostics_enabled()) return;
    char channel_label[64], url_label[64], combined[1536];
    tas_label_channel(channel, channel_label, sizeof(channel_label));
    tas_label_url(url, url_label, sizeof(url_label));
    snprintf(combined, sizeof(combined), "channel=%s resource=%s%s%s",
             channel_label, url_label, detail && detail[0] ? " " : "",
             detail ? detail : "");
    tas_diag_log(event, combined);
}

static id diagnostic_log_data_locked(void) {
    id path = diagnostics_path_locked();
    if (!path) return nil;
    return msg1((id)objc_getClass("NSData"), "dataWithContentsOfFile:", path);
}

static id diagnostic_report_create(void) {
    uint64_t metrics[TAS_DIAG_METRIC_COUNT];
    uint64_t events;
    id log_data;
    pthread_mutex_lock(&g_diag_lock);
    memcpy(metrics, g_metrics, sizeof(metrics));
    events = g_logged_events;
    log_data = objc_retain(diagnostic_log_data_locked());
    pthread_mutex_unlock(&g_diag_lock);

    id bundle = msg0((id)objc_getClass("NSBundle"), "mainBundle");
    const char *app_version = utf8(msg1(bundle, "objectForInfoDictionaryKey:", nsstr("CFBundleShortVersionString")));
    const char *app_build = utf8(msg1(bundle, "objectForInfoDictionaryKey:", nsstr("CFBundleVersion")));
    char header[4096];
    snprintf(header, sizeof(header),
        "Streamside iOS diagnostic report\n"
        "Port build: %s\n"
        "Twitch: %s (%s)\n"
        "Diagnostic logging: %s\n"
        "Privacy: channel names, room IDs, chat text, full URLs and paths, query strings/fragments, headers, access tokens, and manifest contents are not stored.\n"
        "Labels stay with the same channel or playlist until Twitch restarts; then reset.\n"
        "Log limit: 512 KiB\n\n"
        "Session counters\n"
        "HLS intercepted: %llu\n"
        "Master manifests: %llu\n"
        "Variant manifests: %llu\n"
        "Ad-marked manifests: %llu\n"
        "Clean alternate swaps: %llu\n"
        "Suppressed ad segments: %llu\n"
        "Access-token failures: %llu\n"
        "Unmapped variants: %llu\n"
        "Synthetic segment responses: %llu\n"
        "GraphQL rewrites: %llu\n"
        "HLS failures: %llu\n"
        "Logged events this launch: %llu\n",
        TAS_REPORT_VERSION, app_version ? app_version : "unknown", app_build ? app_build : "unknown",
        diagnostics_enabled() ? "enabled" : "disabled",
        (unsigned long long)metrics[TAS_DIAG_HLS_INTERCEPTED],
        (unsigned long long)metrics[TAS_DIAG_MASTER_MANIFEST],
        (unsigned long long)metrics[TAS_DIAG_VARIANT_MANIFEST],
        (unsigned long long)metrics[TAS_DIAG_AD_MANIFEST],
        (unsigned long long)metrics[TAS_DIAG_CLEAN_ALTERNATE],
        (unsigned long long)metrics[TAS_DIAG_STRIPPED_SEGMENT],
        (unsigned long long)metrics[TAS_DIAG_TOKEN_FAILURE],
        (unsigned long long)metrics[TAS_DIAG_UNMAPPED_VARIANT],
        (unsigned long long)metrics[TAS_DIAG_SYNTHETIC_SEGMENT],
        (unsigned long long)metrics[TAS_DIAG_GRAPHQL_REWRITE],
        (unsigned long long)metrics[TAS_DIAG_HLS_FAILURE],
        (unsigned long long)events);

    id report = msg1((id)objc_getClass("NSMutableString"), "stringWithString:", nsstr(header));
    char emote_status[4096], menu_status[1536];
    char button_target[96], button_action[96], presented_class[96], appeared_class[96];
    char navigation_top[96], navigation_visible[96];
    pthread_mutex_lock(&g_diag_lock);
    snprintf(button_target, sizeof(button_target), "%s", g_chat_button_target);
    snprintf(button_action, sizeof(button_action), "%s", g_chat_button_action);
    snprintf(presented_class, sizeof(presented_class), "%s", g_last_presented_class);
    snprintf(appeared_class, sizeof(appeared_class), "%s", g_last_appeared_after_tap);
    snprintf(navigation_top, sizeof(navigation_top), "%s", g_last_navigation_top);
    snprintf(navigation_visible, sizeof(navigation_visible), "%s", g_last_navigation_visible);
    pthread_mutex_unlock(&g_diag_lock);
    tas_emotes_status(emote_status, sizeof(emote_status));
    snprintf(menu_status, sizeof(menu_status),
             "Chat menu (this launch)\n"
             "Chat Settings controller seen/presented: %llu/%llu\n"
             "Action sheets seen/from Chat Settings/titled Chat Settings: %llu/%llu/%llu\n"
             "Reload actions inserted: %llu\n"
             "Native action-sheet hook/seen/reload rows/row taps: %s/%llu/%llu/%llu\n"
             "Chat settings button taps/total presentations: %llu/%llu\n"
             "Button target/action: %s/%s\n"
             "Last presented/appeared after tap: %s/%s\n"
             "Navigation presentations/top/visible: %llu/%s/%s\n\n--- Log ---\n",
             (unsigned long long)MENU_GET(g_chat_controller_appear),
             (unsigned long long)MENU_GET(g_chat_controller_presented),
             (unsigned long long)MENU_GET(g_presented_sheets),
             (unsigned long long)MENU_GET(g_chat_presenter_sheets),
             (unsigned long long)MENU_GET(g_chat_titled_sheets),
             (unsigned long long)MENU_GET(g_reload_actions_added),
             g_native_action_sheet_hooked ? "installed" : "missing",
             (unsigned long long)MENU_GET(g_native_action_sheets_seen),
             (unsigned long long)MENU_GET(g_native_reload_buttons_added),
             (unsigned long long)MENU_GET(g_native_reload_button_taps),
             (unsigned long long)MENU_GET(g_chat_button_taps),
             (unsigned long long)MENU_GET(g_presented_controllers),
             button_target[0] ? button_target : "none",
             button_action[0] ? button_action : "none",
             presented_class[0] ? presented_class : "none",
             appeared_class[0] ? appeared_class : "none",
             (unsigned long long)MENU_GET(g_presented_navigation),
             navigation_top[0] ? navigation_top : "none",
             navigation_visible[0] ? navigation_visible : "none");
    vmsg1(report, "appendString:", nsstr(emote_status));
#if TAS_EMOTE_DIAGNOSTIC
    char probe_status[393216];
    tas_emote_probe_status(probe_status,sizeof(probe_status));
    vmsg1(report,"appendString:",nsstr(probe_status));
#endif
    char ui_status[2048];
    tas_emote_ui_status(ui_status, sizeof(ui_status));
    vmsg1(report, "appendString:", nsstr(ui_status));
    char composer_status[1024];
    ss_composer_status(composer_status, sizeof(composer_status));
    vmsg1(report, "appendString:", nsstr(composer_status));
    vmsg1(report, "appendString:", nsstr(menu_status));
    if (log_data && data_length(log_data)) {
        id log_text = msg0((id)objc_getClass("NSString"), "alloc");
        log_text = ((id (*)(id, SEL, id, NSUInteger))objc_msgSend)(
            log_text, sel_registerName("initWithData:encoding:"), log_data, (NSUInteger)4);
        if (log_text) {
            vmsg1(report, "appendString:", log_text);
            objc_release(log_text);
        }
    } else {
        vmsg1(report, "appendString:", nsstr("No diagnostic entries yet.\n"));
    }
    if (log_data) objc_release(log_data);
    return objc_retain(report);
}

static void clear_diagnostic_log(void) {
    pthread_mutex_lock(&g_diag_lock);
    id path = diagnostics_path_locked();
    if (path) {
        ((BOOL (*)(id, SEL, id, BOOL))objc_msgSend)(
            data_from_bytes("", 0), sel_registerName("writeToFile:atomically:"), path, YES);
    }
    g_logged_events = 0;
    pthread_mutex_unlock(&g_diag_lock);
    tas_diag_log("LOG_CLEARED", "The on-disk diagnostic log was cleared");
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
    return 4;
}

static NSInteger settings_rows_in_section(id self, SEL command, id table, NSInteger section) {
    (void)self;
    (void)command;
    (void)table;
    if (section == 0) return 1;
    if (section == 2) return TAS_EMOTE_DIAGNOSTIC ? 2 : 1;
    if (section == 1) return 3;
    if (section == 3) return 3;
    return 0;
}

static id settings_header(id self, SEL command, id table, NSInteger section) {
    (void)self;
    (void)command;
    (void)table;
    if (section == 0) return nsstr("Status");
    if (section == 1) return nsstr("Third-Party Emotes");
    if (section == 2) return nsstr("Diagnostics");
    if (section == 3) return nsstr("Diagnostic Report");
    return nil;
}

static id settings_footer(id self, SEL command, id table, NSInteger section) {
    (void)self;
    (void)command;
    (void)table;
    if (section == 1) {
        return nsstr("7TV, BTTV and FFZ emotes in chat. The emote keyboard includes a third-party tab and recents. Suggestions can be automatic, colon-triggered, or off. Changes to the enable switch take effect after relaunching Twitch.");
    }
    if (section == 2) {
#if TAS_EMOTE_DIAGNOSTIC
        return nsstr("Inspect Emote traces one code you enter until Twitch restarts. That code is included in the copied report; chat messages are not stored. The trace works while Diagnostic Logging is off.");
#else
        return nsstr("Logging is off by default. When enabled, channel names and playlist URLs appear as temporary labels (for example, channel-a1b2). Labels reset when Twitch restarts. The log holds up to 512 KiB.");
#endif
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
#if TAS_EMOTE_DIAGNOSTIC
    } else if (section == 2 && row == 1) {
        set_cell_text(cell,"Inspect Emote","Trace one code that remains text");
        id notice=objc_getAssociatedObject(self,&g_probe_notice_key);
        if (notice) vmsg1(msg0(cell,"detailTextLabel"),"setText:",notice);
#endif
    } else if (section == 2) {
        set_cell_text(cell, "Diagnostic Logging", diagnostics_enabled() ? "Enabled" : "Disabled");
        id toggle = msg0(msg0((id)objc_getClass("UISwitch"), "alloc"), "init");
        ((void (*)(id, SEL, BOOL, BOOL))objc_msgSend)(
            toggle, sel_registerName("setOn:animated:"), diagnostics_enabled() ? YES : NO, NO);
        ((void (*)(id, SEL, id, SEL, NSUInteger))objc_msgSend)(
            toggle, sel_registerName("addTarget:action:forControlEvents:"),
            self, sel_registerName("tas_diagnosticsSwitchChanged:"), (NSUInteger)(1UL << 12));
        vmsg1(toggle, "setAccessibilityIdentifier:", nsstr("TASDiagnosticsSwitch"));
        vmsg1(cell, "setAccessoryView:", toggle);
        vmsg_integer(cell, "setSelectionStyle:", 0);
        objc_release(toggle);
    } else if (section == 3 && row == 0) {
        set_cell_text(cell, "View Diagnostic Report", "Session summary and sanitized event log");
        vmsg_integer(cell, "setAccessoryType:", 1);
    } else if (section == 3 && row == 1) {
        set_cell_text(cell, "Copy Diagnostic Report", "Copies the complete report to the clipboard");
    } else {
        set_cell_text(cell, "Clear Diagnostic Log", "Removes stored event entries");
    }
    return msg0(cell, "autorelease");
}

static void settings_switch_changed(id self, SEL command, id sender) {
    (void)command;
    bool enabled = bmsg0(sender, "isOn");
    set_diagnostics_enabled(enabled);
    if (enabled) tas_diag_log("LOGGING_ENABLED", "Diagnostic logging enabled from Twitch settings");
    msg0(msg0(self, "tableView"), "reloadData");
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

static void settings_did_select(id self, SEL command, id table, id index_path) {
    (void)command;
    NSInteger section = imsg0(index_path, "section");
    NSInteger row = imsg0(index_path, "row");
    ((void (*)(id, SEL, id, BOOL))objc_msgSend)(
        table, sel_registerName("deselectRowAtIndexPath:animated:"), index_path, YES);
#if TAS_EMOTE_DIAGNOSTIC
    if (section==2 && row==1) {
        id alert=((id (*)(id,SEL,id,id,NSInteger))objc_msgSend)((id)objc_getClass("UIAlertController"),
            sel_registerName("alertControllerWithTitle:message:preferredStyle:"),nsstr("Inspect Emote"),
            nsstr("Enter the exact code after you notice a failure. Recent playback is already being recorded; selecting it retrieves retained history. Copy the diagnostic report. Bounded history expires after ten minutes and resets when Twitch restarts."),(NSInteger)1);
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
    if (section == 1 && row == 1) {
        tas_emotes_clear_cache();
        show_notice(self, "Emote Cache Cleared",
                    "New chat messages will reload third-party emotes when you return to chat.");
        return;
    }
    if (section != 3) return;
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
        show_notice(self, "Cleared", "The stored diagnostic event log was cleared.");
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
        pthread_mutex_lock(&g_diag_lock);
        snprintf(g_last_appeared_after_tap, sizeof(g_last_appeared_after_tap), "%s",
                 class_getName(object_getClass(self)));
        pthread_mutex_unlock(&g_diag_lock);
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
        pthread_mutex_lock(&g_diag_lock);
        snprintf(g_last_presented_class, sizeof(g_last_presented_class), "%s",
                 class_getName(object_getClass(presented)));
        pthread_mutex_unlock(&g_diag_lock);
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
        pthread_mutex_lock(&g_diag_lock);
        snprintf(g_last_navigation_top, sizeof(g_last_navigation_top), "%s",
                 top ? class_getName(object_getClass(top)) : "none");
        snprintf(g_last_navigation_visible, sizeof(g_last_navigation_visible), "%s",
                 visible ? class_getName(object_getClass(visible)) : "none");
        pthread_mutex_unlock(&g_diag_lock);
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
        pthread_mutex_lock(&g_diag_lock);
        snprintf(g_chat_button_target, sizeof(g_chat_button_target), "%s",
                 target ? class_getName(object_getClass(target)) : "none");
        snprintf(g_chat_button_action, sizeof(g_chat_button_action), "%s",
                 action ? sel_getName(action) : "none");
        pthread_mutex_unlock(&g_diag_lock);
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
        pthread_mutex_lock(&g_diag_lock);
        snprintf(g_last_appeared_after_tap, sizeof(g_last_appeared_after_tap), "%s",
                 class_getName(object_getClass(self)));
        pthread_mutex_unlock(&g_diag_lock);
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
        class_addMethod(g_settings_class, sel_registerName("tas_diagnosticsSwitchChanged:"), (IMP)settings_switch_changed, "v@:@");
        class_addMethod(g_settings_class, sel_registerName("ss_suggestionsChanged:"), (IMP)suggestions_changed, "v@:@");
        class_addMethod(g_settings_class, sel_registerName("tas_emotesSwitchChanged:"), (IMP)emotes_switch_changed, "v@:@");
        objc_registerClassPair(g_settings_class);
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
    pthread_mutex_lock(&g_diag_lock);
    diagnostics_path_locked();
    pthread_mutex_unlock(&g_diag_lock);
    bool settings_registered = register_settings_class();
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
