/* Native opt-in control, outside the transcript React tree. Never makes a
 * window key, changes insets, edits focus, scrolls, remounts, or polls. */
#include "TASInvestigationUI.h"
#include "TASInvestigationHost.h"
#include "TASInvestigationReport.h"
#include <dispatch/dispatch.h>
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
typedef struct {
    double x, y;
} Point;
static Class page_class, overlay_window_class, overlay_controller_class;
static IMP super_load, super_appear, super_overlay_layout;
static id owner, page_weak, button, overlay_window;
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
static Rect rect(id o, const char *selector) {
    return ((Rect(*)(id, SEL))objc_msgSend)(o, sel_registerName(selector));
}
static Insets safe_insets(id o) {
    return ((Insets(*)(id, SEL))objc_msgSend)(o, sel_registerName("safeAreaInsets"));
}
static Point button_point(id window, Point point) {
    return ((Point(*)(id, SEL, Point, id))objc_msgSend)(
        button, sel_registerName("convertPoint:fromView:"), point, window);
}
static BOOL can_key(id self, SEL cmd) {
    (void)self;
    (void)cmd;
    return NO;
}
static id overlay_hit(id self, SEL cmd, Point point, id event) {
    (void)cmd;
    if (!visible || self != overlay_window || !button)
        return nil;
    // Returning nil outside the button lets UIKit try the underlying app window.
    // Never return the full-screen root view or the window itself.
    return ((id(*)(id, SEL, Point, id))objc_msgSend)(button, sel_registerName("hitTest:withEvent:"),
                                                     button_point(self, point), event);
}
static void overlay_layout(id self, SEL cmd) {
    if (super_overlay_layout)
        ((void (*)(id, SEL))super_overlay_layout)(self, cmd);
    if (!overlay_window || !button || m0(overlay_window, "rootViewController") != self)
        return;
    id view = m0(self, "view");
    Rect bounds = rect(view, "bounds");
    Insets insets = safe_insets(view);
    Rect frame = {bounds.width - insets.right - 96, insets.top + 8, 88, 44};
    ((void (*)(id, SEL, Rect))objc_msgSend)(button, sel_registerName("setFrame:"), frame);
}
static void hide(void) {
    visible = false;
    if (overlay_window)
        ((void (*)(id, SEL, BOOL))objc_msgSend)(overlay_window, sel_registerName("setHidden:"),
                                                YES);
    if (button) {
        m0(button, "removeFromSuperview");
        objc_release(button);
        button = nil;
    }
    if (overlay_window) {
        m1(overlay_window, "setRootViewController:", nil);
        objc_release(overlay_window);
        overlay_window = nil;
    }
}
void tas_inv_ui_changed(void) {
    if (!page_class)
        return;
    TASInvStatus s = tas_inv_status();
    if (s.pending == TAS_INV_CAPTURE && !tas_inv_report_started(s.generation, s.sequence))
        return;
    if (s.state == TAS_INV_UNSUPPORTED || s.state == TAS_INV_DORMANT || s.state == TAS_INV_STOPPING)
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
static void scene_closed(id self, SEL cmd, id note) {
    if (overlay_window && m0(note, "object") == m0(overlay_window, "windowScene"))
        background(self, cmd, note);
}
static void show(id page) {
    TASInvStatus s = tas_inv_status();
    if (s.state != TAS_INV_ARMED || s.pending || visible)
        return;
    id window = m0(m0(page, "view"), "window");
    id scene = m0(window, "windowScene");
    if (!window || !scene)
        return;
    // A separate, explicitly non-key window survives the settings transition.
    // Bind to the originating scene; never search app/keyboard/PiP windows.
    overlay_window = ((id(*)(id, SEL, id))objc_msgSend)(
        m0((id)overlay_window_class, "alloc"), sel_registerName("initWithWindowScene:"), scene);
    id controller = m0((id)overlay_controller_class, "new");
    button = objc_retain(((id(*)(id, SEL, long))objc_msgSend)(
        (id)objc_getClass("UIButton"), sel_registerName("buttonWithType:"), 1));
    if (!overlay_window || !controller || !button) {
        if (controller)
            objc_release(controller);
        hide();
        return;
    }
    ((void (*)(id, SEL, Rect))objc_msgSend)(overlay_window, sel_registerName("setFrame:"),
                                            rect(window, "frame"));
    ((void (*)(id, SEL, double))objc_msgSend)(overlay_window, sel_registerName("setWindowLevel:"),
                                              1001.0);
    id clear = m0((id)objc_getClass("UIColor"), "clearColor");
    m1(overlay_window, "setBackgroundColor:", clear);
    m1(overlay_window, "setRootViewController:", controller);
    id view = m0(controller, "view");
    m1(view, "setBackgroundColor:", clear);
    ((void (*)(id, SEL, BOOL))objc_msgSend)(view, sel_registerName("setAccessibilityViewIsModal:"),
                                            NO);
    m1(button,
       "setBackgroundColor:", m0((id)objc_getClass("UIColor"), "secondarySystemBackgroundColor"));
    m1(button, "setAccessibilityLabel:", ns("Capture Streamside investigation"));
    ((void (*)(id, SEL, id, SEL, unsigned long))objc_msgSend)(
        button, sel_registerName("addTarget:action:forControlEvents:"), owner,
        sel_registerName("capture:"), 1UL << 6);
    m1(view, "addSubview:", button);
    visible = true;
    // Visibility only: makeKeyAndVisible/makeKeyWindow would disturb the editor.
    ((void (*)(id, SEL, BOOL))objc_msgSend)(overlay_window, sel_registerName("setHidden:"), NO);
    m0(view, "setNeedsLayout");
    m0(view, "layoutIfNeeded");
    objc_release(controller);
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
    return section ? 4 : 5;
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
    if (section)
        return ns("Captures stay in memory until you copy or export them. Stop preserves "
                  "frozen evidence. Numeric observations do not prove a dropped message.");
    TASInvManifest manifest;
    char digest[65];
    unsigned source;
    char description[768];
    if (!tas_inv_configuration(&manifest, digest, &source))
        return ns("The built-in configuration is unavailable.");
    snprintf(description, sizeof(description),
             "%s\nBuilt-in configuration · revision %u · bundled and integrity verified. "
             "Compatibility: Twitch 31.6.2, runtime ABI 1. "
             "Arm without relaunching; Capture returns to Armed. Stop ends collection. "
             "Background, thermal or memory safety stops require explicit rearming. "
             "Remote configuration updates are not installed in this version.",
             manifest.description, manifest.version);
    return ns(description);
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
                : state.reason == TAS_INV_THERMAL
                    ? "Stopped for device temperature. Let it cool before arming."
                : state.reason == TAS_INV_MEMORY
                    ? "Stopped after a memory warning. Arm again explicitly."
                : state.reason == TAS_INV_BACKGROUND ? "Collection stopped in the background."
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
            if (state.state == TAS_INV_UNSUPPORTED && tas_inv_host_explanation)
                tas_inv_host_explanation(status, sizeof(status));
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
        name = row == 0   ? "Export Capture"
               : row == 1 ? "Copy Capture"
               : row == 2 ? "Refresh Status"
                          : "Copy Runtime Status";
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
/* One job/copy/buffer globally, including the queued main-thread handoff. */
static struct {
    id page, table, path;
    bool copy;
    size_t length;
} export_job;
static char export_buffer[65536];
static void export_finish(void) {
    id text = export_job.length && !tas_inv_report_export_cancelled()
                  ? objc_retain(ns(export_buffer))
                  : nil;
    if (!text)
        goto done;
    if (export_job.copy) {
        m1(m0((id)objc_getClass("UIPasteboard"), "generalPasteboard"), "setString:", text);
        notice(export_job.page, "The frozen numeric capture was copied.");
        goto done;
    }
    if (!m0(m0(export_job.page, "view"), "window"))
        goto done;
    id items = ((id(*)(id, SEL, id))objc_msgSend)((id)objc_getClass("NSArray"),
                                                  sel_registerName("arrayWithObject:"), text);
    id activity = ((id(*)(id, SEL, id, id))objc_msgSend)(
        m0((id)objc_getClass("UIActivityViewController"), "alloc"),
        sel_registerName("initWithActivityItems:applicationActivities:"), items, nil);
    id popover = m0(activity, "popoverPresentationController");
    m1(popover, "setSourceView:", export_job.table);
    Rect rect = ((Rect(*)(id, SEL, id))objc_msgSend)(
        export_job.table, sel_registerName("rectForRowAtIndexPath:"), export_job.path);
    ((void (*)(id, SEL, Rect))objc_msgSend)(popover, sel_registerName("setSourceRect:"), rect);
    ((void (*)(id, SEL, id, BOOL, id))objc_msgSend)(
        export_job.page, sel_registerName("presentViewController:animated:completion:"), activity,
        YES, nil);
    objc_release(activity);
done:
    if (text)
        objc_release(text);
    objc_release(export_job.page);
    objc_release(export_job.table);
    objc_release(export_job.path);
    export_job.page = export_job.table = export_job.path = nil;
    tas_inv_report_export_end();
}
static void export_worker(void *unused) {
    (void)unused;
    export_job.length = tas_inv_report_export_format(export_buffer, sizeof(export_buffer));
    id queue = m0((id)objc_getClass("NSOperationQueue"), "mainQueue");
    m1(queue, "addOperationWithBlock:", (id) ^ { export_finish(); });
}
static void export_report(id page, id table, id path, bool copy) {
    if (!tas_inv_report_available()) {
        notice(page, "Capture a snapshot first.");
        return;
    }
    if (!tas_inv_report_export_begin()) {
        notice(page, "An export is already in progress.");
        return;
    }
    export_job.page = objc_retain(page);
    export_job.table = objc_retain(table);
    export_job.path = objc_retain(path);
    export_job.copy = copy;
    export_job.length = 0;
    dispatch_async_f(dispatch_get_global_queue(0, 0), NULL, export_worker);
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
    else if (row == 3 && tas_inv_host_status) {
        char status[1024];
        tas_inv_host_status(status, sizeof(status));
        m1(m0((id)objc_getClass("UIPasteboard"), "generalPasteboard"), "setString:", ns(status));
        notice(self, "The runtime startup status was copied.");
    }
    tas_inv_ui_changed();
}
static bool initialize(void) {
    if (page_class)
        return true;
    Class parent = objc_getClass("UITableViewController"), base = objc_getClass("NSObject"),
          window_base = objc_getClass("UIWindow"),
          controller_base = objc_getClass("UIViewController");
    if (!parent || !base || !window_base || !controller_base)
        return false;
    Class cls = objc_allocateClassPair(parent, "TASInvestigationsViewController", 0),
          observer = objc_allocateClassPair(base, "TASInvestigationActions", 0),
          window = objc_allocateClassPair(window_base, "TASInvestigationCaptureWindow", 0),
          controller =
              objc_allocateClassPair(controller_base, "TASInvestigationCaptureController", 0);
    if (!cls || !observer || !window || !controller) {
        if (cls)
            objc_disposeClassPair(cls);
        if (observer)
            objc_disposeClassPair(observer);
        if (window)
            objc_disposeClassPair(window);
        if (controller)
            objc_disposeClassPair(controller);
        return false;
    }
    bool ok =
        class_addMethod(cls, sel_registerName("viewDidLoad"), (IMP)load, "v@:") &&
        class_addMethod(cls, sel_registerName("viewWillAppear:"), (IMP)appear, "v@:B") &&
        class_addMethod(cls, sel_registerName("numberOfSectionsInTableView:"), (IMP)sections,
                        "q@:@") &&
        class_addMethod(cls, sel_registerName("tableView:numberOfRowsInSection:"), (IMP)rows,
                        "q@:@q") &&
        class_addMethod(cls, sel_registerName("tableView:titleForHeaderInSection:"), (IMP)header,
                        "@@:@q") &&
        class_addMethod(cls, sel_registerName("tableView:titleForFooterInSection:"), (IMP)footer,
                        "@@:@q") &&
        class_addMethod(cls, sel_registerName("tableView:cellForRowAtIndexPath:"), (IMP)cell,
                        "@@:@@") &&
        class_addMethod(cls, sel_registerName("tableView:didSelectRowAtIndexPath:"),
                        (IMP)select_row, "v@:@@") &&
        class_addMethod(observer, sel_registerName("capture:"), (IMP)capture, "v@:@") &&
        class_addMethod(observer, sel_registerName("background:"), (IMP)background, "v@:@") &&
        class_addMethod(observer, sel_registerName("sceneClosed:"), (IMP)scene_closed, "v@:@") &&
        class_addMethod(window, sel_registerName("canBecomeKeyWindow"), (IMP)can_key, "B@:") &&
        class_addMethod(window, sel_registerName("hitTest:withEvent:"), (IMP)overlay_hit,
                        "@@:{CGPoint=dd}@") &&
        class_addMethod(controller, sel_registerName("viewDidLayoutSubviews"), (IMP)overlay_layout,
                        "v@:");
    if (!ok) {
        objc_disposeClassPair(cls);
        objc_disposeClassPair(observer);
        objc_disposeClassPair(window);
        objc_disposeClassPair(controller);
        return false;
    }
    super_load = class_getMethodImplementation(parent, sel_registerName("viewDidLoad"));
    super_appear = class_getMethodImplementation(parent, sel_registerName("viewWillAppear:"));
    super_overlay_layout =
        class_getMethodImplementation(controller_base, sel_registerName("viewDidLayoutSubviews"));
    objc_registerClassPair(window);
    objc_registerClassPair(controller);
    overlay_window_class = window;
    overlay_controller_class = controller;
    objc_registerClassPair(cls);
    objc_registerClassPair(observer);
    page_class = cls;
    owner = m0((id)observer, "new");
    objc_initWeak(&page_weak, nil);
    id center = m0((id)objc_getClass("NSNotificationCenter"), "defaultCenter");
    ((void (*)(id, SEL, id, SEL, id, id))objc_msgSend)(
        center, sel_registerName("addObserver:selector:name:object:"), owner,
        sel_registerName("background:"), ns("UIApplicationDidEnterBackgroundNotification"), nil);
    const char *scene_notes[] = {"UISceneDidEnterBackgroundNotification",
                                 "UISceneDidDisconnectNotification"};
    for (unsigned i = 0; i < sizeof(scene_notes) / sizeof(scene_notes[0]); i++)
        ((void (*)(id, SEL, id, SEL, id, id))objc_msgSend)(
            center, sel_registerName("addObserver:selector:name:object:"), owner,
            sel_registerName("sceneClosed:"), ns(scene_notes[i]), nil);
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
