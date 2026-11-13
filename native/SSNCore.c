#include "SSNCore.h"
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <pthread.h>
#if __APPLE__
#include <mach/mach.h>
#include <sys/sysctl.h>
#endif
#ifndef SSN_NATIVE
#error Build must explicitly choose baseline or native
#endif
static _Atomic uint64_t counts[SSN_PROBE_COUNT];
static _Atomic unsigned armed_mask, failures, state, rows, foregrounds, backgrounds, presentation_owner;
static _Atomic uint64_t started_ns, visible_ms, first_active_ms, launch_sequence;
static _Atomic unsigned navigation_armed;
static _Atomic uint64_t navigation_events[5],account_events[5],account_updates_retained,account_data_clears;
static _Atomic unsigned playback_phase,playback_error,playback_last_error;
static _Atomic uint64_t playback_events[9];
static uint64_t peak_footprint;
static bool baseline_verified;
static char report_path[1024], calibration_path[1024];
static pthread_mutex_t report_lock=PTHREAD_MUTEX_INITIALIZER;
static uint64_t clock_ns(void) {
    struct timespec t={0}; clock_gettime(CLOCK_MONOTONIC,&t);
    return (uint64_t)t.tv_sec*1000000000ull+(uint64_t)t.tv_nsec;
}
static void write_file(const char *path,const char *data,size_t length) {
    if (!*path) return;
    char temporary[1100]; snprintf(temporary,sizeof(temporary),"%s.tmp",path);
    int fd=open(temporary,O_WRONLY|O_CREAT|O_TRUNC,0600);
    if (fd<0) { atomic_fetch_or(&failures,1u<<9); return; }
    size_t done=0;
    while (done<length) { ssize_t n=write(fd,data+done,length-done); if(n<=0) break; done+=(size_t)n; }
    int synced=fsync(fd),closed=close(fd);
    if (done!=length || synced || closed || rename(temporary,path))
        atomic_fetch_or(&failures,1u<<9);
}
bool ssn_armed(void) { return atomic_load(&armed_mask)==(1u<<SSN_IMAGE_COUNT)-1; }
bool ssn_failed(void) { return atomic_load(&failures)!=0; }
bool ssn_calibrated(void) { return baseline_verified; }
unsigned ssn_state(void) { return atomic_load(&state); }
uint64_t ssn_count(unsigned i) { return i<SSN_PROBE_COUNT?atomic_load(&counts[i]):0; }
void ssn_arm_image(unsigned i,bool valid) {
    if (valid) atomic_fetch_or(&armed_mask,1u<<i); else ssn_failure(0);
}
void ssn_failure(unsigned code) { atomic_fetch_or(&failures,1u<<(code<31?code:31)); }
const char *ssn_state_text(void) {
    static const char *text[]={"Waiting for Twitch account restoration","No existing authorized session",
        "Checking existing Twitch account…","Loading followed channels…","Followed channels loaded",
        "No followed channels returned","Native request failed; session not verified",
        "Native service compatibility check failed; requests disabled","Account changed; old results cleared",
        "Runtime monitoring incomplete; native requests paused",
        "Account verified; followed-channel request failed"};
    unsigned s=ssn_state(); return s<sizeof(text)/sizeof(*text)?text[s]:"Unknown state";
}
void ssn_service(unsigned s,unsigned count) { atomic_store(&state,s); atomic_store(&rows,count); }
void ssn_presentation(unsigned owner) { atomic_store(&presentation_owner,owner<=3?owner:0); }
void ssn_navigation_armed(void) { atomic_store(&navigation_armed,1); }
bool ssn_navigation_guarded(void) { return atomic_load(&navigation_armed)!=0; }
void ssn_navigation_event(unsigned event) {
    if(event<5) atomic_fetch_add(&navigation_events[event],1);
    if(event==3) ssn_failure(11);
}
void ssn_account_observed(unsigned event,bool preserved) {
    if(event>=5) return;
    atomic_fetch_add(&account_events[event],1);
    if(preserved) atomic_fetch_add(&account_updates_retained,1);
}
void ssn_playback_status(unsigned phase,unsigned error) { atomic_store(&playback_phase,phase<=7?phase:7);atomic_store(&playback_error,error<=7?error:7);if(error) atomic_store(&playback_last_error,error<=7?error:7); }
void ssn_playback_event(unsigned event) { if(event<9) atomic_fetch_add(&playback_events[event],1); }
void ssn_account_data_cleared(void) { atomic_fetch_add(&account_data_clears,1); }
void ssn_scaffold_ready(void) { if(!visible_ms) visible_ms=(clock_ns()-started_ns)/1000000; }
void ssn_transition(bool foreground) {
    if(foreground) { atomic_fetch_add(&foregrounds,1); if(!first_active_ms) first_active_ms=(clock_ns()-started_ns)/1000000; } else atomic_fetch_add(&backgrounds,1);
    ssn_report();
}
const char *ssn_report_path(void) { return report_path; }
void ssn_core_start(const char *directory) {
    started_ns=clock_ns();
    snprintf(report_path,sizeof(report_path),"%s/%s.json",directory,SSN_NATIVE?"native-latest":"baseline-latest");
    snprintf(calibration_path,sizeof(calibration_path),"%s/baseline-calibration",directory);
    /* Keep the last terminated attempt for the next run/export. Do not erase its identity. */
    char previous[1100]; snprintf(previous,sizeof(previous),"%s/%s-previous.json",directory,SSN_NATIVE?"native":"baseline");
    rename(report_path,previous);
    char sequence_path[1100],sequence[32]={0};
    snprintf(sequence_path,sizeof(sequence_path),"%s/%s-sequence",directory,SSN_NATIVE?"native":"baseline");
    unsigned long long saved_sequence=0;
    int sequence_fd=open(sequence_path,O_RDONLY);
    if(sequence_fd>=0) { read(sequence_fd,sequence,sizeof(sequence)-1); close(sequence_fd); sscanf(sequence,"%llu",&saved_sequence); }
    launch_sequence=(uint64_t)saved_sequence+1; snprintf(sequence,sizeof(sequence),"%llu",(unsigned long long)launch_sequence);
    write_file(sequence_path,sequence,strlen(sequence));
    char stored[96]={0}; int fd=open(calibration_path,O_RDONLY);
    if(fd>=0) { ssize_t n=read(fd,stored,sizeof(stored)-1); close(fd);
        baseline_verified=n==(ssize_t)strlen(SSN_PROOF_ID) && !memcmp(stored,SSN_PROOF_ID,(size_t)n); }
}
static bool positive_control(void) {
    static const char *required[]={"rn_factory","rn_host","rn_instance","rn_root_surface",
        "rn_script_load","hermes_runtime","hermes_eval","worklet_runtime","hermes_implementation","hermes_engine"};
    if(!ssn_armed() || ssn_failed()) return false;
    for(unsigned r=0;r<sizeof(required)/sizeof(*required);r++) {
        bool seen=false;
        for(unsigned i=0;i<SSN_PROBE_COUNT;i++) if(!strcmp(required[r],ssn_specs[i].name) && ssn_count(i)) seen=true;
        if(!seen) return false;
    }
    return true;
}
void ssn_report(void) {
    if(!*report_path) return;
    pthread_mutex_lock(&report_lock);
    uint64_t footprint=0,resident=0; bool memory_available=false;
    char hardware[80]="unavailable",os[80]="unavailable";
#if __APPLE__
    task_vm_info_data_t info={0}; mach_msg_type_number_t length=TASK_VM_INFO_COUNT;
    if(task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&info,&length)==KERN_SUCCESS && length>=TASK_VM_INFO_REV1_COUNT) {
        footprint=info.phys_footprint; resident=info.resident_size; memory_available=true;
    }
    size_t n=sizeof(hardware); sysctlbyname("hw.machine",hardware,&n,NULL,0);
    n=sizeof(os); sysctlbyname("kern.osrelease",os,&n,NULL,0);
    hardware[sizeof(hardware)-1]=0; os[sizeof(os)-1]=0;
    /* Export only the bounded platform identifier alphabet, never arbitrary system text. */
    for(char *p=hardware;*p;p++) if(!((*p>='A'&&*p<='Z')||(*p>='a'&&*p<='z')||(*p>='0'&&*p<='9')||*p==','||*p=='.')) *p='_';
    for(char *p=os;*p;p++) if(!((*p>='0'&&*p<='9')||*p=='.')) *p='_';
#endif
    if(footprint>peak_footprint) peak_footprint=footprint;
    hardware[sizeof(hardware)-1]=0; os[sizeof(os)-1]=0;
    bool positive=!SSN_NATIVE&&positive_control();
    if(positive) write_file(calibration_path,SSN_PROOF_ID,strlen(SSN_PROOF_ID));
    char data[16384]; size_t at=0;
#define ADD(...) do { int n=snprintf(data+at,sizeof(data)-at,__VA_ARGS__); if(n<0||(size_t)n>=sizeof(data)-at) { pthread_mutex_unlock(&report_lock); ssn_failure(10); return; } at+=(size_t)n; } while(0)
    ADD("{\"schema\":1,\"proof_id\":\"%s\",\"source_revision\":\"%s\",\"mode\":\"%s\",",SSN_PROOF_ID,SSN_REVISION,SSN_NATIVE?"native":"baseline");
    ADD("\"donor_sha256\":\"076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129\",\"twitch_version\":\"32.0\",\"twitch_build\":\"263110145453907615\",");
    ADD("\"armed_mask\":%u,\"failures\":%u,\"baseline_positive_control\":%s,\"baseline_calibrated\":%s,",atomic_load(&armed_mask),atomic_load(&failures),positive?"true":"false",baseline_verified?"true":"false");
    ADD("\"launch_sequence\":%llu,\"first_active_ms\":%llu,\"peak_observed_footprint_bytes\":%llu,",(unsigned long long)launch_sequence,(unsigned long long)first_active_ms,(unsigned long long)peak_footprint);
    ADD("\"uptime_ms\":%llu,\"diagnostic_scaffold_ready_ms\":%llu,\"foregrounds\":%u,\"backgrounds\":%u,",(unsigned long long)((clock_ns()-started_ns)/1000000),(unsigned long long)visible_ms,atomic_load(&foregrounds),atomic_load(&backgrounds));
    ADD("\"ui_root_owner\":%u,",atomic_load(&presentation_owner));
    ADD("\"navigation_guard_armed\":%u,\"navigation_events\":[",atomic_load(&navigation_armed));
    for(unsigned i=0;i<5;i++) ADD("%s%llu",i?",":"",(unsigned long long)atomic_load(&navigation_events[i]));
    ADD("],\"account_events\":[");
    for(unsigned i=0;i<5;i++) ADD("%s%llu",i?",":"",(unsigned long long)atomic_load(&account_events[i]));
    ADD("],\"account_updates_retained\":%llu,\"account_data_clears\":%llu,",(unsigned long long)atomic_load(&account_updates_retained),(unsigned long long)atomic_load(&account_data_clears));
    ADD("\"playback_phase\":%u,\"playback_error\":%u,\"playback_last_error\":%u,\"playback_events\":[",atomic_load(&playback_phase),atomic_load(&playback_error),atomic_load(&playback_last_error));
    for(unsigned i=0;i<9;i++) ADD("%s%llu",i?",":"",(unsigned long long)atomic_load(&playback_events[i]));
    ADD("],");
    ADD("\"account_list_state\":%u,\"returned_channel_count\":%u,\"memory_available\":%s,\"phys_footprint_bytes\":%llu,\"resident_bytes\":%llu,\"hardware\":\"%s\",\"os_kernel\":\"%s\",\"probes\":{",ssn_state(),atomic_load(&rows),memory_available?"true":"false",(unsigned long long)footprint,(unsigned long long)resident,hardware,os);
    for(unsigned i=0;i<SSN_PROBE_COUNT;i++) ADD("%s\"%s\":%llu",i?",":"",ssn_specs[i].name,(unsigned long long)ssn_count(i));
    ADD("}}\n");
    write_file(report_path,data,at);
#undef ADD
    pthread_mutex_unlock(&report_lock);
}
void ssn_probe_hit(unsigned i) {
    if(i>=SSN_PROBE_COUNT) { ssn_failure(0); return; }
    atomic_fetch_add(&counts[i],1);
    if(SSN_NATIVE && ssn_specs[i].guard) {
        ssn_failure(1); ssn_report();
        /* Returning NULL through an unknown Swift/C++ result ABI would corrupt
         * the caller. Stop before the donor entry, preserving numeric evidence. */
        _exit(86);
    }
}
void ssn_summary(char *buffer,size_t size) {
    const char *status=ssn_failed()?"FAILED — export evidence":!ssn_armed()?"INCOMPLETE — probes not armed":
        SSN_NATIVE?(baseline_verified?"Guarded; baseline observed — device sequence required":"UNVERIFIED — run baseline first"):
        positive_control()?"Baseline positive control observed":"Baseline incomplete — exercise RN screens";
    const char *failure=(atomic_load(&failures)&2)?"Blocked an unexpected RN/runtime attempt; export the report":
        (atomic_load(&failures)&1)?"Runtime probe identity or coverage failed":
        (atomic_load(&failures)&4)?"Native lifecycle/account integration check failed":
        (atomic_load(&failures)&8)?"Native service compatibility check failed":
        (atomic_load(&failures)&16)?"Native diagnostic window was unavailable":
        (atomic_load(&failures)&(1u<<11))?"Native navigation ownership failed":
        (atomic_load(&failures)&(1u<<9))?"Diagnostic file could not be saved":"";
    snprintf(buffer,size,"%s\n%s\n%s\nRN factory %llu · host %llu\nSurface entries %llu · bundle entries %llu\nHermes VM %llu · worklet VM %llu\nNavigation guard %u · root requests blocked %llu\nSign-in opened %llu · verified returns %llu · failures %llu · closes %llu\nAccount updates retained %llu · data clears %llu\nPlayback phase %u · error %u · last failure %u · players %llu · released %llu\nEntry counts; unknown coverage is never zero activity.",
        SSN_NATIVE?"Native frontend candidate":"Instrumented Twitch baseline",status,failure,
        (unsigned long long)ssn_count(4),(unsigned long long)ssn_count(6),(unsigned long long)(ssn_count(8)+ssn_count(9)),
        (unsigned long long)ssn_count(12),(unsigned long long)ssn_count(24),(unsigned long long)ssn_count(22),atomic_load(&navigation_armed),
        (unsigned long long)atomic_load(&navigation_events[0]),(unsigned long long)atomic_load(&navigation_events[1]),
        (unsigned long long)atomic_load(&navigation_events[2]),(unsigned long long)atomic_load(&navigation_events[3]),
        (unsigned long long)atomic_load(&navigation_events[4]),(unsigned long long)atomic_load(&account_updates_retained),(unsigned long long)atomic_load(&account_data_clears),
        atomic_load(&playback_phase),atomic_load(&playback_error),atomic_load(&playback_last_error),(unsigned long long)atomic_load(&playback_events[2]),(unsigned long long)atomic_load(&playback_events[5]));
}
