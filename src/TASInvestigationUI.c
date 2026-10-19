/* Native opt-in control, outside the transcript React tree. Never makes a
 * window key, changes insets, edits focus, scrolls, remounts, or polls. */
#include "TASInvestigationUI.h"
#include "TASInvestigationHost.h"
#include "TASInvestigationReport.h"
#include <objc/message.h>
#include <objc/runtime.h>
#include <stdio.h>
#include <stdlib.h>
extern id objc_retain(id);
extern void objc_release(id);
extern id objc_initWeak(id *, id);
extern id objc_storeWeak(id *, id);
extern id objc_loadWeakRetained(id *);
typedef struct {
    double x, y, width, height;
} Rect;
typedef struct {
    double top, left, bottom, right;
} Insets;
static Class page_class;
static IMP super_load, super_appear;
static id owner, page_weak, button;
static bool visible;
static id m0(id o, const char *s) { return ((id(*)(id, SEL))objc_msgSend)(o, sel_registerName(s)); }
static id m1(id o, const char *s, id a) {
    return ((id(*)(id, SEL, id))objc_msgSend)(o, sel_registerName(s), a);
}
static id ns(const char *s) {
    return m1((id)objc_getClass("NSString"), "stringWithUTF8String:", (id)s);
}
static long index_value(id o, const char *s) {
    return ((long (*)(id, SEL))objc_msgSend)(o, sel_registerName(s));
}
static void title(id control, const char *value) {
    ((void (*)(id, SEL, id, unsigned long))objc_msgSend)(
        control, sel_registerName("setTitle:forState:"), ns(value), 0);
}
static void hide(void) {
    visible = false;
    if (button) {
        m0(button, "removeFromSuperview");
        objc_release(button);
        button = nil;
    }
}
void tas_inv_ui_changed(void) {
    if (!page_class)
        return;
    TASInvStatus s = tas_inv_status();
    if (s.pending == TAS_INV_CAPTURE && !tas_inv_report_started(s.generation, s.sequence))
        return;
    if (s.state == TAS_INV_UNSUPPORTED || s.state == TAS_INV_DORMANT)
        hide();
    if (button) {
        title(button, s.pending == TAS_INV_CAPTURE ? "Capturing…" : "Capture");
        ((void (*)(id, SEL, BOOL))objc_msgSend)(button, sel_registerName("setEnabled:"),
                                                s.state == TAS_INV_ARMED && !s.pending);
    }
    id page = objc_loadWeakRetained(&page_weak);
    if (page) {
        m0(m0(page, "tableView"), "reloadData");
        objc_release(page);
    }
}
static void capture(id self, SEL cmd, id sender) {
    (void)sender;
    (void)self;
    (void)cmd;
    if (tas_inv_host_request)
        tas_inv_host_request(
            TAS_INV_CAPTURE); /* No reporting UI until a separate explicit user action. */
    tas_inv_ui_changed();
}
static void background(id self, SEL cmd, id note) {
    (void)self;
    (void)cmd;
    (void)note;
    if (tas_inv_host_request)
        tas_inv_host_request(TAS_INV_STOP);
    hide();
    tas_inv_ui_changed();
}
static void show(id page) {
    TASInvStatus s = tas_inv_status();
    if (s.state != TAS_INV_ARMED || s.pending)
        return;
    id window = m0(m0(page, "view"), "window");
    if (!window)
        return;
    Rect bounds = ((Rect(*)(id, SEL))objc_msgSend)(window, sel_registerName("bounds"));
    Insets insets = ((Insets(*)(id, SEL))objc_msgSend)(window, sel_registerName("safeAreaInsets"));
    button = objc_retain(((id(*)(id, SEL, long))objc_msgSend)(
        (id)objc_getClass("UIButton"), sel_registerName("buttonWithType:"), 1));
    Rect frame = {bounds.width - insets.right - 96, insets.top + 8, 88, 44};
    ((void (*)(id, SEL, Rect))objc_msgSend)(button, sel_registerName("setFrame:"), frame);
    ((void (*)(id, SEL, unsigned long))objc_msgSend)(
        button, sel_registerName("setAutoresizingMask:"), 1 | 8);
    m1(button,
       "setBackgroundColor:", m0((id)objc_getClass("UIColor"), "secondarySystemBackgroundColor"));
    m1(button, "setAccessibilityLabel:", ns("Capture Streamside investigation"));
    ((void (*)(id, SEL, id, SEL, unsigned long))objc_msgSend)(
        button, sel_registerName("addTarget:action:forControlEvents:"), owner,
        sel_registerName("capture:"), 1UL << 6);
    m1(window, "addSubview:", button);
    visible = true;
    tas_inv_ui_changed();
}
static void notice(id page, const char *message) {
    id alert = ((id(*)(id, SEL, id, id, long))objc_msgSend)(
        (id)objc_getClass("UIAlertController"),
        sel_registerName("alertControllerWithTitle:message:preferredStyle:"), ns("Investigations"),
        ns(message), 1);
    id action = ((id(*)(id, SEL, id, long, id))objc_msgSend)(
        (id)objc_getClass("UIAlertAction"), sel_registerName("actionWithTitle:style:handler:"),
        ns("OK"), 0, nil);
    m1(alert, "addAction:", action);
    ((void (*)(id, SEL, id, BOOL, id))objc_msgSend)(
        page, sel_registerName("presentViewController:animated:completion:"), alert, YES, nil);
}
static void load(id self, SEL cmd) {
    if (super_load)
        ((void (*)(id, SEL))super_load)(self, cmd);
    m1(self, "setTitle:", ns("Investigations"));
}
static void appear(id self, SEL cmd, BOOL animated) {
    if (super_appear)
        ((void (*)(id, SEL, BOOL))super_appear)(self, cmd, animated);
    objc_storeWeak(&page_weak, self);
    tas_inv_ui_changed();
}
static long sections(id self, SEL cmd, id table) {
    (void)self;
    (void)cmd;
    (void)table;
    return 2;
}
static long rows(id self, SEL cmd, id table, long section) {
    (void)self;
    (void)cmd;
    (void)table;
    return section ? 3 : 5;
}
static id header(id self, SEL cmd, id table, long section) {
    (void)self;
    (void)cmd;
    (void)table;
    return ns(section ? "Frozen capture" : "RN chat gaps");
}
static id footer(id self, SEL cmd, id table, long section) {
    (void)self;
    (void)cmd;
    (void)table;
    return ns(section ? "Captures stay in memory until you copy or export them. Stop preserves the "
                        "frozen capture. Reports contain numeric observations; missing "
                        "observations do not prove a dropped message."
                      : "Arm without relaunching, return to the stream, then use the optional "
                        "Capture button. No preset change is needed. Capture returns to Armed. "
                        "Collection stops when Twitch enters the background. This development "
                        "candidate still requires device validation.");
}
static id cell(id self, SEL cmd, id table, id path) {
    (void)self;
    (void)cmd;
    (void)table;
    long section = index_value(path, "section"), row = index_value(path, "row");
    id c = ((id(*)(id, SEL, long, id))objc_msgSend)(
        m0((id)objc_getClass("UITableViewCell"), "alloc"),
        sel_registerName("initWithStyle:reuseIdentifier:"), 3, nil);
    const char *name = NULL, *detail = NULL;
    char status[512];
    TASInvStatus state = tas_inv_status();
    bool enabled = true;
    if (!section) {
        if (!row) {
            name = tas_inv_state_name(state.state);
            const char *message =
                state.pending == TAS_INV_ARM    ? "Arming…"
                : state.pending == TAS_INV_STOP ? "Stopping…"
                : state.state == TAS_INV_ARMED
                    ? "Retaining recent events. Capture returns to Armed."
                : state.state == TAS_INV_CAPTURING
                    ? "Freezing recent history and reading current state."
                : state.state == TAS_INV_DORMANT    ? "Ready to arm. Collection is off."
                : state.reason == TAS_INV_BAD_DONOR ? "This Twitch build is not supported."
                : state.reason == TAS_INV_TIMEOUT
                    ? "Chat did not respond in time. Relaunch Twitch to reset."
                : state.reason == TAS_INV_BAD_INTEGRITY || state.reason == TAS_INV_BAD_MANIFEST
                    ? "The investigation configuration failed validation."
                    : "The chat runtime is not ready for this session.";
            snprintf(status, sizeof(status), "%s", message);
            detail = status;
            enabled = false;
        } else if (row == 1) {
            name = "Arm";
            enabled = state.state == TAS_INV_DORMANT && !state.pending;
        } else if (row == 2) {
            name = "Capture Snapshot";
            enabled = state.state == TAS_INV_ARMED && !state.pending;
        } else if (row == 3) {
            name = "Stop";
            enabled =
                state.state == TAS_INV_ARMED || state.state == TAS_INV_CAPTURING || state.pending;
        } else {
            name = "In-chat Capture button";
            detail = visible ? "Shown" : "Hidden";
            enabled = visible || (state.state == TAS_INV_ARMED && !state.pending);
        }
    } else
        name = row == 0 ? "Export Capture" : row == 1 ? "Copy Capture" : "Refresh Status";
    m1(m0(c, "textLabel"), "setText:", ns(name));
    if (detail)
        m1(m0(c, "detailTextLabel"), "setText:", ns(detail));
    ((void (*)(id, SEL, long))objc_msgSend)(m0(c, "detailTextLabel"),
                                            sel_registerName("setNumberOfLines:"), 0);
    ((void (*)(id, SEL, BOOL))objc_msgSend)(c, sel_registerName("setUserInteractionEnabled:"),
                                            enabled);
    ((void (*)(id, SEL, double))objc_msgSend)(m0(c, "contentView"), sel_registerName("setAlpha:"),
                                              enabled ? 1.0 : 0.55);
    return m0(c, "autorelease");
}
static void export_report(id page, id table, id path, bool copy) {
    if (!tas_inv_report_available()) {
        notice(page, "Capture a snapshot first.");
        return;
    }
    char *buffer = malloc(65536);
    if (!buffer)
        return;
    size_t n = tas_inv_report_format(buffer, 65536);
    id text = n ? objc_retain(ns(buffer)) : nil;
    free(buffer);
    if (!text)
        return;
    if (copy) {
        m1(m0((id)objc_getClass("UIPasteboard"), "generalPasteboard"), "setString:", text);
        objc_release(text);
        notice(page, "The frozen numeric capture was copied.");
        return;
    }
    id items = ((id(*)(id, SEL, id))objc_msgSend)((id)objc_getClass("NSArray"),
                                                  sel_registerName("arrayWithObject:"), text);
    id activity = ((id(*)(id, SEL, id, id))objc_msgSend)(
        m0((id)objc_getClass("UIActivityViewController"), "alloc"),
        sel_registerName("initWithActivityItems:applicationActivities:"), items, nil);
    id popover = m0(activity, "popoverPresentationController");
    m1(popover, "setSourceView:", table);
    Rect rect = ((Rect(*)(id, SEL, id))objc_msgSend)(
        table, sel_registerName("rectForRowAtIndexPath:"), path);
    ((void (*)(id, SEL, Rect))objc_msgSend)(popover, sel_registerName("setSourceRect:"), rect);
    ((void (*)(id, SEL, id, BOOL, id))objc_msgSend)(
        page, sel_registerName("presentViewController:animated:completion:"), activity, YES, nil);
    objc_release(activity);
    objc_release(text);
}
static void select_row(id self, SEL cmd, id table, id path) {
    (void)cmd;
    ((void (*)(id, SEL, id, BOOL))objc_msgSend)(
        table, sel_registerName("deselectRowAtIndexPath:animated:"), path, YES);
    long section = index_value(path, "section"), row = index_value(path, "row");
    if (!section) {
        if (row >= 1 && row <= 3) {
            unsigned op = row == 1 ? TAS_INV_ARM : row == 2 ? TAS_INV_CAPTURE : TAS_INV_STOP;
            if (tas_inv_host_request && !tas_inv_host_request(op))
                notice(self, "The action is unavailable. Refresh status; captures also have a "
                             "short cooldown.");
            if (op == TAS_INV_STOP)
                hide();
        } else if (row == 4) {
            if (visible)
                hide();
            else
                show(self);
        }
    } else if (row < 2)
        export_report(self, table, path, row == 1);
    tas_inv_ui_changed();
}
static bool initialize(void) {
    if (page_class)
        return true;
    Class parent = objc_getClass("UITableViewController"), base = objc_getClass("NSObject");
    if (!parent || !base)
        return false;
    Class cls = objc_allocateClassPair(parent, "TASInvestigationsViewController", 0),
          observer = objc_allocateClassPair(base, "TASInvestigationActions", 0);
    if (!cls || !observer)
        return false;
    bool ok = class_addMethod(cls, sel_registerName("viewDidLoad"), (IMP)load, "v@:") &&
              class_addMethod(cls, sel_registerName("viewWillAppear:"), (IMP)appear, "v@:B") &&
              class_addMethod(cls, sel_registerName("numberOfSectionsInTableView:"), (IMP)sections,
                              "q@:@") &&
              class_addMethod(cls, sel_registerName("tableView:numberOfRowsInSection:"), (IMP)rows,
                              "q@:@q") &&
              class_addMethod(cls, sel_registerName("tableView:titleForHeaderInSection:"),
                              (IMP)header, "@@:@q") &&
              class_addMethod(cls, sel_registerName("tableView:titleForFooterInSection:"),
                              (IMP)footer, "@@:@q") &&
              class_addMethod(cls, sel_registerName("tableView:cellForRowAtIndexPath:"), (IMP)cell,
                              "@@:@@") &&
              class_addMethod(cls, sel_registerName("tableView:didSelectRowAtIndexPath:"),
                              (IMP)select_row, "v@:@@") &&
              class_addMethod(observer, sel_registerName("capture:"), (IMP)capture, "v@:@") &&
              class_addMethod(observer, sel_registerName("background:"), (IMP)background, "v@:@");
    if (!ok) {
        objc_disposeClassPair(cls);
        objc_disposeClassPair(observer);
        return false;
    }
    super_load = class_getMethodImplementation(parent, sel_registerName("viewDidLoad"));
    super_appear = class_getMethodImplementation(parent, sel_registerName("viewWillAppear:"));
    objc_registerClassPair(cls);
    objc_registerClassPair(observer);
    page_class = cls;
    owner = m0((id)observer, "new");
    objc_initWeak(&page_weak, nil);
    id center = m0((id)objc_getClass("NSNotificationCenter"), "defaultCenter");
    ((void (*)(id, SEL, id, SEL, id, id))objc_msgSend)(
        center, sel_registerName("addObserver:selector:name:object:"), owner,
        sel_registerName("background:"), ns("UIApplicationDidEnterBackgroundNotification"), nil);
    return true;
}
void tas_inv_ui_open(id parent) {
    if (!initialize())
        return;
    id page = ((id(*)(id, SEL, long))objc_msgSend)(m0((id)page_class, "alloc"),
                                                   sel_registerName("initWithStyle:"), 2);
    ((void (*)(id, SEL, id, BOOL))objc_msgSend)(m0(parent, "navigationController"),
                                                sel_registerName("pushViewController:animated:"),
                                                page, YES);
    objc_release(page);
}
