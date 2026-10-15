#include "TASDiagnosticPolicy.h"
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
enum { SLOTS=48, LINE=384 };
typedef struct {char lines[SLOTS][LINE];unsigned next,count;uint64_t accepted,overwritten,shortened;} Ring;
static Ring rings[TAS_DIAG_CATEGORIES];
static pthread_mutex_t policy_lock=PTHREAD_MUTEX_INITIALIZER;
static unsigned active=1;
unsigned tas_diag_config_normalize(unsigned w){return w&~831U ? 1U : w;}
unsigned tas_diag_policy_word(void){return __atomic_load_n(&active,__ATOMIC_ACQUIRE);}
void tas_diag_policy_initialize(unsigned saved){__atomic_store_n(&active,tas_diag_config_normalize(saved),__ATOMIC_RELEASE);}
unsigned tas_diag_preset_word(unsigned p){
    static const unsigned words[]={1,259,285,289,513};
    return p<5?words[p]:1;
}
unsigned tas_diag_preset_for(unsigned w){if(w&TAS_DIAG_CUSTOM_BIT)return TAS_DIAG_CUSTOM;for(unsigned i=0;i<4;i++)if(w==tas_diag_preset_word(i))return i;return TAS_DIAG_CUSTOM;}
const char *tas_diag_preset_name(unsigned p){static const char *n[]={"Minimal","Ad Blocking","Emotes","Chat","Custom"};return p<5?n[p]:"Custom";}
const char *tas_diag_category_name(unsigned c){static const char *n[]={"General","Playback / Ad Blocking","Emote Rendering","Image Transport","Composer / Picker","Chat / Redemptions"};return c<6?n[c]:"Unknown";}
void tas_diag_classify(const char *e,unsigned *c,unsigned *l){
    e=e?e:"EVENT";*c=TAS_DIAG_GENERAL;*l=TAS_DIAG_DETAILED;
    if(!strncmp(e,"HLS_",4)||!strncmp(e,"VAFT_",5)||!strncmp(e,"VARIANT_",8)||!strncmp(e,"TOKEN_",6)||
       !strncmp(e,"BACKUP_",7)||!strcmp(e,"GQL_REWRITE")||!strcmp(e,"MASTER_MANIFEST")||
       !strcmp(e,"SEGMENTS_SUPPRESSED")||!strcmp(e,"SYNTHETIC_SEGMENT")||!strcmp(e,"ASSET_INTERCEPT"))*c=TAS_DIAG_PLAYBACK;
    else if(!strncmp(e,"EMOTE_",6)||!strncmp(e,"RN_WIDTH",8))*c=TAS_DIAG_RENDERING;
    else if(!strncmp(e,"RN_LOCAL",8)||!strncmp(e,"RN_CHAT",7))*c=TAS_DIAG_CHAT;
    else if(!strncmp(e,"RN_",3))*c=TAS_DIAG_COMPOSER;
    if(*c==TAS_DIAG_GENERAL||strstr(e,"FAILURE")||strstr(e,"REFUSED")||strstr(e,"UNAVAILABLE"))*l=TAS_DIAG_SUMMARY;
}
void tas_diag_event_store(unsigned c,unsigned l,const char *e,const char *d){
    if(!tas_diag_wants(c,l))return;
    pthread_mutex_lock(&policy_lock);Ring *r=&rings[c];
    int n=snprintf(r->lines[r->next],LINE,"[%lld] %s%s%s\n",(long long)time(NULL),e?e:"EVENT",d&&*d?" ":"",d?d:"");
    if(n>=(int)LINE){r->shortened++;r->lines[r->next][LINE-2]='\n';r->lines[r->next][LINE-1]=0;}
    r->next=(r->next+1)%SLOTS;r->accepted++;if(r->count<SLOTS)r->count++;else r->overwritten++;
    pthread_mutex_unlock(&policy_lock);
}
void tas_diag_events_clear(void){pthread_mutex_lock(&policy_lock);memset(rings,0,sizeof(rings));pthread_mutex_unlock(&policy_lock);}
void tas_diag_events_report(unsigned c,char *b,size_t cap){
    if(!cap)return;b[0]=0;if(c>=TAS_DIAG_CATEGORIES)return;
    if(!tas_diag_wants(c,TAS_DIAG_SUMMARY)){snprintf(b,cap,"Collection disabled this launch.\n");return;}
    pthread_mutex_lock(&policy_lock);Ring *r=&rings[c];unsigned limit=tas_diag_wants(c,TAS_DIAG_DETAILED)?12:4,n=r->count<limit?r->count:limit;
    size_t used=0;
#define ADD(...) do{if(used<cap){int k=snprintf(b+used,cap-used,__VA_ARGS__);if(k>0)used+=(size_t)k;}}while(0)
    ADD("Events accepted=%llu retained=%u/48 overwritten=%llu shortened=%llu export-omitted=%u; collection=%s\n",(unsigned long long)r->accepted,r->count,(unsigned long long)r->overwritten,(unsigned long long)r->shortened,r->count-n,tas_diag_wants(c,TAS_DIAG_DETAILED)?"detailed":"failures/essential only");
    for(unsigned i=r->count-n;i<r->count;i++)ADD("%s",r->lines[(r->next+SLOTS-r->count+i)%SLOTS]);
    if(used>=cap && cap>40){const char *note="\n[event export truncated: bounded buffer]\n";size_t length=strlen(note);if(length<cap)memcpy(b+cap-length-1,note,length+1);}
#undef ADD
    pthread_mutex_unlock(&policy_lock);
}
void tas_diag_configuration_report(unsigned saved,char *b,size_t cap){
    unsigned w=tas_diag_policy_word();size_t used=0;
#define ADD(...) do{if(used<cap){int k=snprintf(b+used,cap-used,__VA_ARGS__);if(k>0)used+=(size_t)k;}}while(0)
    ADD("Diagnostics: %s / %s; active mask=%u\nSaved: %s / %s; mask=%u; %s\n",tas_diag_preset_name(tas_diag_preset_for(w)),w&TAS_DIAG_DETAIL_BIT?"Detailed":"Summary",w&63,tas_diag_preset_name(tas_diag_preset_for(saved)),saved&TAS_DIAG_DETAIL_BIT?"Detailed":"Summary",saved&63,saved==w?"no pending change":"RELAUNCH REQUIRED; capture still uses active configuration");
    for(unsigned c=0;c<TAS_DIAG_CATEGORIES;c++)ADD("%s: %s\n",tas_diag_category_name(c),w&(1U<<c)?"enabled":"collection disabled; section omitted");
    ADD("Retention: per-category 48 x 384-byte session ring; export latest 4 Summary or 12 Detailed events/category. Operational counters may span disabled collection. No prior-launch event files exported.\n");
#undef ADD
    if(cap)b[cap-1]=0;
}
