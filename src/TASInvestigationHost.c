#include "TASInvestigationHost.h"
#include "TASInvestigationReport.h"
#include <dispatch/dispatch.h>
#include <dlfcn.h>
#include <mach-o/loader.h>
#include <math.h>
#include <objc/message.h>
#include <objc/objc.h>
#include <objc/runtime.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

extern id objc_retain(id);
extern void objc_release(id);
extern id objc_initWeak(id *, id);
extern id objc_storeWeak(id *, id);
extern id objc_loadWeakRetained(id *);
extern void objc_destroyWeak(id *);
extern id objc_getAssociatedObject(id, const void *);
extern void objc_setAssociatedObject(id, const void *, id, uintptr_t);
typedef struct {
    const char *js_name, *objc_name;
    BOOL synchronous;
} MethodInfo;
static pthread_mutex_t host_lock = PTHREAD_MUTEX_INITIALIZER;
static id module_weak, timer, target;
static ptrdiff_t callable_offset;
static IMP parent_init, parent_dealloc, admitted_callable;
static const void *react_image;
static unsigned source_epoch, ready_caps;
static bool supported, pong, started;
static unsigned timer_queued;
static uint64_t probe_deadline, last_capture;
static char module_epoch_key;
static TASInvDonor evidence;
static char fingerprints[8][65];
static const char *const module_name = "StreamsideInvestigation";
/* Compiled snapshot, lifecycle and reward-route adapters. Per-field coverage
 * remains explicit when a mounted donor handle is unavailable. */
#define TAS_INV_HOST_CAPABILITIES 6U
static id m0(id o, const char *s) { return ((id(*)(id, SEL))objc_msgSend)(o, sel_registerName(s)); }
static id m1(id o, const char *s, id a) {
    return ((id(*)(id, SEL, id))objc_msgSend)(o, sel_registerName(s), a);
}
static id ns(const char *s) {
    return m1((id)objc_getClass("NSString"), "stringWithUTF8String:", (id)s);
}
static bool kind(id o, const char *name) {
    return o && ((BOOL(*)(id, SEL, id))objc_msgSend)(o, sel_registerName("isKindOfClass:"),
                                                     (id)objc_getClass(name));
}
static const char *text(id o) {
    return kind(o, "NSString")
               ? ((const char *(*)(id, SEL))objc_msgSend)(o, sel_registerName("UTF8String"))
               : NULL;
}
static id box(unsigned value) {
    return ((id(*)(id, SEL, unsigned))objc_msgSend)(
        (id)objc_getClass("NSNumber"), sel_registerName("numberWithUnsignedInt:"), value);
}
static bool integer(id o, unsigned *out) {
    if (!kind(o, "NSNumber"))
        return false;
    double n = ((double (*)(id, SEL))objc_msgSend)(o, sel_registerName("doubleValue"));
    if (!isfinite(n) || n < 0 || n > UINT32_MAX || floor(n) != n)
        return false;
    *out = (unsigned)n;
    return true;
}
static uint64_t now_ms(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t))
        return 0;
    return (uint64_t)t.tv_sec * 1000 + (uint64_t)t.tv_nsec / 1000000;
}
bool tas_inv_host_sha256(const void *data, size_t length, unsigned char out[32]) {
    typedef unsigned char *(*SHA)(const void *, uint32_t, unsigned char *);
    SHA sha = (SHA)dlsym(RTLD_DEFAULT, "CC_SHA256");
    return sha && length <= UINT32_MAX && sha(data, (uint32_t)length, out);
}
static void hex(const unsigned char *input, unsigned n, char *output) {
    static const char digits[] = "0123456789abcdef";
    for (unsigned i = 0; i < n; i++) {
        output[i * 2] = digits[input[i] >> 4];
        output[i * 2 + 1] = digits[input[i] & 15];
    }
    output[n * 2] = 0;
}
static bool image(const struct mach_header_64 *h, intptr_t slide, char *uuid, char *sha) {
    if (!h || h->magic != MH_MAGIC_64 || h->cputype != CPU_TYPE_ARM64 || h->ncmds > 4096 ||
        h->sizeofcmds > 2097152)
        return false;
    const unsigned char *p = (const unsigned char *)(h + 1), *end = p + h->sizeofcmds;
    bool found_uuid = false, found_text = false;
    unsigned char digest[32];
    for (unsigned i = 0; i < h->ncmds; i++) {
        if ((size_t)(end - p) < sizeof(struct load_command))
            return false;
        const struct load_command *c = (const struct load_command *)p;
        if (c->cmdsize < 8 || c->cmdsize > (size_t)(end - p))
            return false;
        if (c->cmd == LC_UUID) {
            if (c->cmdsize != sizeof(struct uuid_command) || found_uuid)
                return false;
            hex(((const struct uuid_command *)c)->uuid, 16, uuid);
            found_uuid = true;
        }
        if (c->cmd == LC_SEGMENT_64) {
            const struct segment_command_64 *s = (const struct segment_command_64 *)c;
            if (c->cmdsize < sizeof(*s) ||
                s->nsects > (c->cmdsize - sizeof(*s)) / sizeof(struct section_64))
                return false;
            const struct section_64 *sections = (const struct section_64 *)(s + 1);
            for (unsigned k = 0; k < s->nsects; k++)
                if (!strncmp(sections[k].sectname, "__text", 16) &&
                    !strncmp(sections[k].segname, "__TEXT", 16)) {
                    if (found_text || sections[k].addr < s->vmaddr ||
                        sections[k].size > s->vmsize - (sections[k].addr - s->vmaddr) ||
                        sections[k].size > UINT32_MAX)
                        return false;
                    const void *bytes =
                        (const void *)(uintptr_t)(sections[k].addr + (uint64_t)slide);
                    if (!tas_inv_host_sha256(bytes, (size_t)sections[k].size, digest))
                        return false;
                    hex(digest, 32, sha);
                    found_text = true;
                }
        }
        p += c->cmdsize;
    }
    return p == end && found_uuid && found_text;
}
static bool native_profile(void) {
    typedef uint32_t (*Count)(void);
    typedef const struct mach_header_64 *(*Header)(uint32_t);
    typedef const char *(*Name)(uint32_t);
    typedef intptr_t (*Slide)(uint32_t);
    Count count = (Count)dlsym(RTLD_DEFAULT, "_dyld_image_count");
    Header header = (Header)dlsym(RTLD_DEFAULT, "_dyld_get_image_header");
    Name name = (Name)dlsym(RTLD_DEFAULT, "_dyld_get_image_name");
    Slide slide = (Slide)dlsym(RTLD_DEFAULT, "_dyld_get_image_vmaddr_slide");
    if (!count || !header || !name || !slide)
        return false;
    id info = m0(m0((id)objc_getClass("NSBundle"), "mainBundle"), "infoDictionary");
    const char *v = text(m1(info, "objectForKey:", ns("CFBundleShortVersionString"))),
               *b = text(m1(info, "objectForKey:", ns("CFBundleVersion")));
    if (!v || !b || strcmp(v, "31.6.2") || strcmp(b, "262872150334984303"))
        return false;
    bool main = false, react = false, hermes = false;
    uint32_t n = count();
    if (!n || n > 4096)
        return false;
    for (uint32_t i = 0; i < n; i++) {
        const char *path = name(i);
        if (!path)
            continue;
        if (i == 0) {
            main = image(header(i), slide(i), fingerprints[0], fingerprints[1]);
        }
        if (strstr(path, "/React.framework/React")) {
            if (react)
                return false;
            react = image(header(i), slide(i), fingerprints[2], fingerprints[3]);
            if (react)
                react_image = header(i);
        }
        if (strstr(path, "/hermesvm.framework/hermesvm")) {
            if (hermes)
                return false;
            hermes = image(header(i), slide(i), fingerprints[4], fingerprints[5]);
        }
    }
    evidence = (TASInvDonor){.version = "31.6.2",
                             .build = "262872150334984303",
                             .main_uuid = fingerprints[0],
                             .main_text_sha256 = fingerprints[1],
                             .hermes_uuid = fingerprints[4],
                             .hermes_text_sha256 = fingerprints[5],
                             .hbc_sha256 =
                                 "20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458",
                             .hbc_version = 98,
                             .hbc_bytes = 28682408};
    return main && react && hermes &&
           !strcmp(fingerprints[2], "ee15b752fb4635f2b0bba46636572385") &&
           !strcmp(fingerprints[3],
                   "0d68cf0f54f1b72c166ac3695935071ee1a258085dd16ad63fbd7bba94889c48") &&
           tas_inv_donor_matches(&evidence);
}
static bool abi(Class c, const char *selector, const char *encoding) {
    Method m = c ? class_getInstanceMethod(c, sel_registerName(selector)) : NULL;
    const char *type = m ? method_getTypeEncoding(m) : NULL;
    return type && !strcmp(type, encoding);
}
static id *callable_slot(id self) { return (id *)((unsigned char *)self + callable_offset); }
static id instance_init(id self, SEL cmd) {
    id value = ((id(*)(id, SEL))parent_init)(self, cmd);
    if (value)
        objc_initWeak(callable_slot(value), nil);
    return value;
}
static void instance_dealloc(id self, SEL cmd) {
    objc_destroyWeak(callable_slot(self));
    ((void (*)(id, SEL))parent_dealloc)(self, cmd);
}
static void set_callable(id self, SEL cmd, id callable) {
    (void)cmd;
    Class c = objc_getClass("RCTCallableJSModules");
    if (callable && object_getClass(callable) != c)
        return;
    objc_storeWeak(callable_slot(self), callable);
}
static id get_callable(id self) { return objc_loadWeakRetained(callable_slot(self)); }
static unsigned bound_epoch(id self) {
    unsigned n = 0;
    integer(objc_getAssociatedObject(self, &module_epoch_key), &n);
    return n;
}
static void update_timer(void);
static bool invoke(unsigned, unsigned, unsigned, const TASInvManifest *);
static void emergency_stop(void) {
    TASInvStatus s = tas_inv_status();
    tas_inv_report_interrupt();
    if (s.generation < UINT32_MAX && s.sequence < UINT32_MAX)
        invoke(TAS_INV_STOP, s.generation + 1, s.sequence + 1, NULL);
}

static void schedule_timer(void) {
    if (__atomic_exchange_n(&timer_queued, 1, __ATOMIC_ACQ_REL))
        return;
    id queue = m0((id)objc_getClass("NSOperationQueue"), "mainQueue");
    m1(queue, "addOperationWithBlock:", (id) ^ { update_timer(); });
}
static void timeout(id self, SEL cmd, id fired) {
    (void)self;
    (void)cmd;
    if (fired != timer)
        return;
    bool expired = tas_inv_expire(now_ms());
    pthread_mutex_lock(&host_lock);
    if (probe_deadline && now_ms() >= probe_deadline) {
        probe_deadline = 0;
        pong = false;
        expired = true;
    }
    pthread_mutex_unlock(&host_lock);
    if (expired) {
        tas_inv_invalidate(TAS_INV_TIMEOUT);
        emergency_stop();
    }
    update_timer();
}
static void update_timer(void) {
    __atomic_store_n(&timer_queued, 0, __ATOMIC_RELEASE);
    if (timer) {
        m0(timer, "invalidate");
        objc_release(timer);
        timer = nil;
    }
    TASInvStatus status = tas_inv_status();
    uint64_t deadline = status.pending ? status.deadline_ms : 0;
    pthread_mutex_lock(&host_lock);
    if (!deadline)
        deadline = probe_deadline;
    pthread_mutex_unlock(&host_lock);
    if (!deadline || !target)
        return;
    uint64_t now = now_ms();
    double interval = deadline > now ? (double)(deadline - now) / 1000 : 0.001;
    timer = objc_retain(((id(*)(id, SEL, double, id, SEL, id, BOOL))objc_msgSend)(
        (id)objc_getClass("NSTimer"),
        sel_registerName("scheduledTimerWithTimeInterval:target:selector:userInfo:repeats:"),
        interval, target, sel_registerName("deadline:"), nil, NO));
}
static bool invoke(unsigned operation, unsigned generation, unsigned sequence,
                   const TASInvManifest *manifest) {
    pthread_mutex_lock(&host_lock);
    id self = objc_loadWeakRetained(&module_weak);
    unsigned epoch = source_epoch;
    pthread_mutex_unlock(&host_lock);
    if (!self)
        return false;
    id callable = get_callable(self);
    IMP current =
        class_getMethodImplementation(objc_getClass("RCTCallableJSModules"),
                                      sel_registerName("invokeModule:method:withArgs:onComplete:"));
    if (!callable || current != admitted_callable || bound_epoch(self) != epoch) {
        if (callable)
            objc_release(callable);
        objc_release(self);
        return false;
    }
    id parameters = m0((id)objc_getClass("NSMutableArray"), "array");
    if (manifest) {
        m1(parameters, "addObject:", box(manifest->events));
        m1(parameters, "addObject:", box(manifest->return_armed ? 1 : 0));
        for (unsigned k = 0; k < TAS_INV_LIMITS; k++)
            m1(parameters, "addObject:", box(manifest->limits[k]));
    }
    id args = m0((id)objc_getClass("NSMutableArray"), "array");
    m1(args, "addObject:", box(operation));
    m1(args, "addObject:", box(generation));
    m1(args, "addObject:", box(sequence));
    m1(args, "addObject:", parameters);
    ((void (*)(id, SEL, id, id, id, id))objc_msgSend)(
        callable, sel_registerName("invokeModule:method:withArgs:onComplete:"), ns(module_name),
        ns("command"), args, nil);
    objc_release(callable);
    objc_release(self);
    return true;
}
static void probe(void *context) {
    (void)context;
    if (!invoke(0, 0, 0, NULL)) {
        tas_inv_invalidate(TAS_INV_NO_RUNTIME);
        pthread_mutex_lock(&host_lock);
        probe_deadline = 0;
        pthread_mutex_unlock(&host_lock);
    }
    schedule_timer();
}
static id ready(id self, SEL cmd, id abi_value, id caps_value) {
    (void)cmd;
    unsigned version = 0, caps = 0;
    if (!integer(abi_value, &version) || version != TAS_INV_ABI || !integer(caps_value, &caps) ||
        (caps & ~TAS_INV_HOST_CAPABILITIES))
        return box(0);
    id callable = get_callable(self);
    if (!callable)
        return box(0);
    objc_release(callable);
    pthread_mutex_lock(&host_lock);
    unsigned epoch = source_epoch, previous = bound_epoch(self);
    if (!supported || !epoch || (previous && previous != epoch)) {
        pthread_mutex_unlock(&host_lock);
        return box(0);
    }
    objc_setAssociatedObject(self, &module_epoch_key, box(epoch), 1);
    objc_storeWeak(&module_weak, self);
    ready_caps = caps;
    pong = false;
    probe_deadline = now_ms() + 2000;
    pthread_mutex_unlock(&host_lock);
    dispatch_async_f(dispatch_get_global_queue(0, 0), NULL, probe);
    return box(epoch);
}
static void ack(id self, SEL cmd, id epoch_value, id generation_value, id sequence_value,
                id operation_value, id success_value) {
    (void)cmd;
    unsigned epoch = 0, generation = 0, sequence = 0, operation = 0, success = 0;
    if (!integer(epoch_value, &epoch) || !integer(generation_value, &generation) ||
        !integer(sequence_value, &sequence) || !integer(operation_value, &operation) ||
        !integer(success_value, &success) || success > 1)
        return;
    pthread_mutex_lock(&host_lock);
    id current = objc_loadWeakRetained(&module_weak);
    bool valid = current == self && epoch == source_epoch && bound_epoch(self) == epoch;
    if (current)
        objc_release(current);
    if (valid && operation == 0 && generation == 0 && sequence == 0 && success) {
        pong = true;
        probe_deadline = 0;
        unsigned caps = ready_caps;
        pthread_mutex_unlock(&host_lock);
        tas_inv_admit(&evidence, caps, epoch);
        schedule_timer();
        return;
    }
    pthread_mutex_unlock(&host_lock);
    if (valid) {
        if (operation == TAS_INV_CAPTURE && success &&
            !tas_inv_report_complete(generation, sequence))
            success = 0;
        bool accepted = tas_inv_ack(generation, sequence, operation, success != 0);
        if (accepted && !success)
            emergency_stop();
    }
    schedule_timer();
}
static id report(id self, SEL cmd, id epoch_value, id generation_value, id sequence_value,
                 id payload) {
    (void)cmd;
    unsigned epoch = 0, g = 0, s = 0;
    if (!integer(epoch_value, &epoch) || !integer(generation_value, &g) ||
        !integer(sequence_value, &s) || !kind(payload, "NSString") ||
        ((unsigned long (*)(id, SEL))objc_msgSend)(payload, sel_registerName("length")) > 8192)
        return box(0);
    const char *bytes = text(payload);
    if (!bytes)
        return box(0);
    size_t n = strnlen(bytes, 8193);
    if (!n || n > 8192)
        return box(0);
    pthread_mutex_lock(&host_lock);
    id current = objc_loadWeakRetained(&module_weak);
    TASInvStatus status = tas_inv_status();
    bool valid = current == self && epoch == source_epoch && bound_epoch(self) == epoch &&
                 status.state == TAS_INV_CAPTURING && status.pending == TAS_INV_CAPTURE &&
                 status.generation == g && status.sequence == s;
    if (current)
        objc_release(current);
    bool ok = valid && tas_inv_report_accept(g, s, bytes, n, now_ms());
    pthread_mutex_unlock(&host_lock);
    return box(ok ? 1 : 0);
}
static const MethodInfo *report_export(id self, SEL cmd) {
    (void)self;
    (void)cmd;
    static const MethodInfo m = {"report",
                                 "report:(NSNumber *)epoch generation:(NSNumber *)generation "
                                 "sequence:(NSNumber *)sequence payload:(NSString *)payload",
                                 YES};
    return &m;
}
static void invalidate(id self, SEL cmd) {
    (void)cmd;
    pthread_mutex_lock(&host_lock);
    id current = objc_loadWeakRetained(&module_weak);
    bool owned = current == self;
    if (current)
        objc_release(current);
    if (owned) {
        objc_storeWeak(&module_weak, nil);
        pong = false;
        probe_deadline = 0;
    }
    pthread_mutex_unlock(&host_lock);
    if (owned) {
        tas_inv_report_interrupt();
        tas_inv_invalidate(TAS_INV_NO_RUNTIME);
        schedule_timer();
    }
}
static id moduleName(id self, SEL cmd) {
    (void)self;
    (void)cmd;
    return ns(module_name);
}
static BOOL mainQueue(id self, SEL cmd) {
    (void)self;
    (void)cmd;
    return NO;
}
static const MethodInfo *ready_export(id self, SEL cmd) {
    (void)self;
    (void)cmd;
    static const MethodInfo m = {
        "ready", "ready:(NSNumber *)abi capabilities:(NSNumber *)capabilities", YES};
    return &m;
}
static const MethodInfo *ack_export(id self, SEL cmd) {
    (void)self;
    (void)cmd;
    static const MethodInfo m = {
        "ack",
        "ack:(NSNumber *)epoch generation:(NSNumber *)generation sequence:(NSNumber *)sequence "
        "operation:(NSNumber *)operation success:(NSNumber *)success",
        NO};
    return &m;
}
void tas_inv_host_initialize(void) {
    pthread_mutex_lock(&host_lock);
    if (started) {
        pthread_mutex_unlock(&host_lock);
        return;
    }
    started = true;
    objc_initWeak(&module_weak, nil);
    pthread_mutex_unlock(&host_lock);
    if (!tas_inv_initialize(tas_inv_host_sha256) || !native_profile())
        return;
    Class callable = objc_getClass("RCTCallableJSModules");
    if (!abi(callable, "invokeModule:method:withArgs:onComplete:", "v48@0:8@16@24@32@?40"))
        return;
    admitted_callable = class_getMethodImplementation(
        callable, sel_registerName("invokeModule:method:withArgs:onComplete:"));
    Dl_info owner;
    if (!dladdr((const void *)admitted_callable, &owner) || owner.dli_fbase != react_image ||
        (uintptr_t)admitted_callable - (uintptr_t)react_image != 0x7eaecU)
        return;

    void (*register_module)(Class) = (void (*)(Class))dlsym(RTLD_DEFAULT, "RCTRegisterModule");
    void *protocol = objc_getProtocol("RCTBridgeModule");
    Class parent = objc_getClass("NSObject");
    if (!register_module || !protocol || !parent || objc_getClass("TASInvestigationModule"))
        return;
    Class cls = objc_allocateClassPair(parent, "TASInvestigationModule", 0),
          clock = objc_allocateClassPair(parent, "TASInvestigationClock", 0);
    if (!cls || !clock)
        return;
    bool ok = class_addIvar(cls, "_tasCallable", sizeof(id), 3, "@") &&
              class_addProtocol(cls, protocol) &&
              class_addMethod(cls, sel_registerName("init"), (IMP)instance_init, "@16@0:8") &&
              class_addMethod(cls, sel_registerName("dealloc"), (IMP)instance_dealloc, "v16@0:8") &&
              class_addMethod(cls, sel_registerName("setCallableJSModules:"), (IMP)set_callable,
                              "v24@0:8@16") &&
              class_addMethod(cls, sel_registerName("ready:capabilities:"), (IMP)ready,
                              "@32@0:8@16@24") &&
              class_addMethod(cls, sel_registerName("ack:generation:sequence:operation:success:"),
                              (IMP)ack, "v56@0:8@16@24@32@40@48") &&
              class_addMethod(cls, sel_registerName("report:generation:sequence:payload:"),
                              (IMP)report, "@48@0:8@16@24@32@40") &&
              class_addMethod(object_getClass((id)cls),
                              sel_registerName("__rct_export__investigationReport"),
                              (IMP)report_export, "^v16@0:8") &&
              class_addMethod(cls, sel_registerName("invalidate"), (IMP)invalidate, "v16@0:8") &&
              class_addMethod(object_getClass((id)cls), sel_registerName("moduleName"),
                              (IMP)moduleName, "@16@0:8") &&
              class_addMethod(object_getClass((id)cls), sel_registerName("requiresMainQueueSetup"),
                              (IMP)mainQueue, "B16@0:8") &&
              class_addMethod(object_getClass((id)cls),
                              sel_registerName("__rct_export__investigationReady"),
                              (IMP)ready_export, "^v16@0:8") &&
              class_addMethod(object_getClass((id)cls),
                              sel_registerName("__rct_export__investigationAck"), (IMP)ack_export,
                              "^v16@0:8") &&
              class_addMethod(clock, sel_registerName("deadline:"), (IMP)timeout, "v24@0:8@16");
    if (!ok) {
        objc_disposeClassPair(cls);
        objc_disposeClassPair(clock);
        return;
    }
    parent_init = class_getMethodImplementation(parent, sel_registerName("init"));
    parent_dealloc = class_getMethodImplementation(parent, sel_registerName("dealloc"));
    objc_registerClassPair(cls);
    objc_registerClassPair(clock);
    callable_offset = ivar_getOffset(class_getInstanceVariable(cls, "_tasCallable"));
    target = m0(m0((id)clock, "alloc"), "init");
    register_module(cls);
    supported = true;
}
bool tas_inv_host_supported(void) { return __atomic_load_n(&supported, __ATOMIC_ACQUIRE); }
void tas_inv_host_source_admitted(void) {
    pthread_mutex_lock(&host_lock);
    if (source_epoch < 10000000)
        source_epoch++;
    else
        supported = false;
    objc_storeWeak(&module_weak, nil);
    pong = false;
    probe_deadline = 0;
    pthread_mutex_unlock(&host_lock);
    tas_inv_report_interrupt();
    tas_inv_invalidate(TAS_INV_NO_RUNTIME);
    schedule_timer();
}
bool tas_inv_host_request(unsigned operation) {
    pthread_mutex_lock(&host_lock);
    uint64_t now = now_ms();
    bool available = supported && pong &&
                     (operation != TAS_INV_CAPTURE || !last_capture || now >= last_capture + 3000);
    TASInvCommand command;
    bool begun = available && tas_inv_begin(operation, now, &command);
    if (begun && operation == TAS_INV_CAPTURE)
        last_capture = now;
    if (begun && operation == TAS_INV_STOP)
        tas_inv_report_interrupt();
    pthread_mutex_unlock(&host_lock);
    if (!begun)
        return false;
    bool ok = invoke(command.operation, command.generation, command.sequence, &command.manifest);
    if (!ok)
        tas_inv_invalidate(TAS_INV_NO_RUNTIME);
    schedule_timer();
    return ok;
}
void tas_inv_host_status(char *buffer, size_t capacity) {
    TASInvStatus s = tas_inv_status();
    pthread_mutex_lock(&host_lock);
    snprintf(buffer, capacity, "%s: %s; native=%u source=%u channel=%u; generation=%u pending=%u",
             tas_inv_state_name(s.state), tas_inv_reason_name(s.reason), supported ? 1 : 0,
             source_epoch, pong ? 1 : 0, s.generation, s.pending);
    pthread_mutex_unlock(&host_lock);
}
