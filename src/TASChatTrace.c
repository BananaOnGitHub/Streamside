#include "TASChatTrace.h"
#if TAS_CHAT_TRACE_DIAGNOSTIC
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>
#include <time.h>
#define EVENTS 2048U
#define PRIORITY 128U
typedef struct {double v[10],time;uint64_t sequence;} Packet;
static Packet events[EVENTS],priority[PRIORITY];
static unsigned event_at,event_count,priority_at,priority_count;
static uint64_t accepted,rejected,limited;
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static bool began;
static double started,rate_time,regular_tokens=64,priority_tokens=16;
#ifndef TAS_CHAT_TRACE_NOW
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (double)t.tv_sec+t.tv_nsec/1e9;}
#define TAS_CHAT_TRACE_NOW() now()
#endif
/* Numbers only, exact schema. Neither input text nor Objective-C strings are
 * retained. Validate syntax before strtod, including short/malformed packets. */
static bool parse(const char *p,double out[10]){
    if(!p || strnlen(p,321)>320 || *p++!='[')return false;
    for(unsigned i=0;i<10;i++){
        while(*p==' ' || *p=='\t')p++;
        const char *start=p;if(*p=='-')p++;
        if(*p=='0')p++;else{if(*p<'1'||*p>'9')return false;do{p++;}while(*p>='0'&&*p<='9');}
        if(*p=='.'){p++;if(*p<'0'||*p>'9')return false;do{p++;}while(*p>='0'&&*p<='9');}
        if(*p=='e'||*p=='E'){p++;if(*p=='+'||*p=='-')p++;if(*p<'0'||*p>'9')return false;do{p++;}while(*p>='0'&&*p<='9');}
        char *end;out[i]=strtod(start,&end);
        if(end!=p || !isfinite(out[i]) || fabs(out[i])>10000000)return false;
        while(*p==' '||*p=='\t')p++;
        if(*p!=(i==9?']':','))return false;
        p++;
    }return !*p;
}
bool tas_chat_trace_packet(const char *packet){
    double v[10];bool valid=parse(packet,v);
    if(valid)for(unsigned i=0;i<10;i++)if((i<4 || i>=8) && (v[i]<0 || floor(v[i])!=v[i]))valid=false;
    if(valid && (v[0]>16 || v[1]<1 || v[3]>63))valid=false;
    if(valid && v[0]==9 && (v[4]<1 || v[4]>3 || floor(v[4])!=v[4]))valid=false;
    if(valid && v[0]==3 && (v[4]<0 || v[4]>1 || floor(v[4])!=v[4] || v[5]<0 || v[5]>3 || floor(v[5])!=v[5]))valid=false;
    if(valid && v[0]==5 && v[4]!=1 && v[4]!=2)valid=false;
    if(valid && v[0]==12 && (v[4]<0 || v[4]>1 || v[5]<0 || v[5]>2 || floor(v[4])!=v[4] || floor(v[5])!=v[5]))valid=false;
    if(valid && (v[0]==13 || v[0]==15) && v[4]!=0 && v[4]!=1)valid=false;
    if(valid && v[0]==16)for(unsigned i=4;i<8;i++)if(v[i]<0 || floor(v[i])!=v[i])valid=false;
    pthread_mutex_lock(&lock);
    if(!valid){rejected++;pthread_mutex_unlock(&lock);return false;}
    double t=TAS_CHAT_TRACE_NOW();
    if(!began){started=t;rate_time=t;began=true;}
    double delta=fmax(0,t-rate_time);rate_time=t;
    regular_tokens=fmin(64,regular_tokens+delta*64);priority_tokens=fmin(16,priority_tokens+delta*16);
    unsigned e=(unsigned)v[0];bool urgent=e==0 || e==9 || e==11 || e==13 || (((unsigned)v[3]&1) && e<=3);
    double *tokens=urgent?&priority_tokens:&regular_tokens;
    if(*tokens<1){limited++;pthread_mutex_unlock(&lock);return false;}(*tokens)--;
    Packet p={.time=fmax(0,t-started),.sequence=++accepted};memcpy(p.v,v,sizeof(v));
    events[event_at]=p;event_at=(event_at+1)%EVENTS;if(event_count<EVENTS)event_count++;
    if(urgent){priority[priority_at]=p;priority_at=(priority_at+1)%PRIORITY;if(priority_count<PRIORITY)priority_count++;}
    pthread_mutex_unlock(&lock);return true;
}
typedef struct {unsigned id,mask,flags,list,error,emit_error,cycle,frame;double height,rect[4],time,window_time;bool window;} Row;
typedef struct {unsigned id,counts[17],state_flags,subscription,hooks,cycle,viewport_frame,viewport_cycle,sample_frame,nulls,null_own,rows;double lines,connected,viewport[4],state_time,viewport_time;bool viewport_known,state_known;Row row[256];} Session;
/* Scratch report state is fixed and protected by the same lock, not on the
 * limited RN stack. Rows are rebuilt from the retained window on every copy. */
static Session report_sessions[4];
static const Packet *at(unsigned i){return &events[(event_at+EVENTS-event_count+i)%EVENTS];}
static Session *find(unsigned id){for(unsigned i=0;i<4;i++)if(report_sessions[i].id==id)return &report_sessions[i];return NULL;}
static Row *row(Session *s,unsigned id,unsigned cycle){for(unsigned i=0;i<s->rows;i++)if(s->row[i].id==id && s->row[i].cycle==cycle)return &s->row[i];return NULL;}
void tas_chat_trace_status(char *buffer,size_t capacity){
    if(!buffer||!capacity)return;
    pthread_mutex_lock(&lock);size_t used=0;memset(report_sessions,0,sizeof(report_sessions));
    unsigned count=0;
    for(unsigned i=event_count;i>0;i--){
        const Packet *p=at(i-1);unsigned sid=(unsigned)p->v[1],id=(unsigned)p->v[2];Session *s=find(sid);
        if(!s && count<4){s=&report_sessions[count++];s->id=sid;}
        if(s && id && !row(s,id,(unsigned)p->v[8]) && s->rows<256){Row *r=&s->row[s->rows++];r->id=id;r->cycle=(unsigned)p->v[8];}
    }
    for(unsigned i=0;i<event_count;i++){
        const Packet *p=at(i);const double *v=p->v;unsigned e=(unsigned)v[0];Session *s=find((unsigned)v[1]);if(!s)continue;
        s->counts[e]++;s->cycle=(unsigned)v[8];
        if(e==1 && !v[4]){s->nulls++;if((unsigned)v[3]&1)s->null_own++;}
        if(e==10){s->state_flags=(unsigned)v[3];s->lines=v[4];s->connected=v[5];s->state_time=p->time;s->state_known=true;}
        if(e==12){s->subscription=(unsigned)v[4];s->hooks=(unsigned)v[5];}
        if(e==14)s->sample_frame=(unsigned)v[9];
        if(e==8){memcpy(s->viewport,v+4,sizeof(s->viewport));s->viewport_frame=(unsigned)v[9];s->viewport_cycle=(unsigned)v[8];s->viewport_time=p->time;s->viewport_known=v[6]>0&&v[7]>0;}
        Row *r=row(s,(unsigned)v[2],(unsigned)v[8]);if(!r)continue;
        r->mask|=1U<<e;r->flags|=(unsigned)v[3];r->time=p->time;r->cycle=(unsigned)v[8];
        if(e==5)r->list|=1U<<((unsigned)v[4]-1);
        if(e==6)r->height=v[4];
        if(e==7){memcpy(r->rect,v+4,sizeof(r->rect));r->frame=(unsigned)v[9];r->window_time=p->time;r->window=v[6]>0&&v[7]>0;}
        if(e==9)r->error=(unsigned)v[4];
        if(e==3 && !v[4])r->emit_error=(unsigned)v[5];
    }
#define APPEND(...) do{if(used<capacity){int n=snprintf(buffer+used,capacity-used,__VA_ARGS__);if(n>0)used+=(size_t)n;}}while(0)
    double age=began?fmax(0,TAS_CHAT_TRACE_NOW()-started):0;
    APPEND("\nRN chat trace (rolling; content-free)\nRunning elapsed: %.1fs; lifetime accepted/schema-refused/rate-limited: %llu/%llu/%llu\n",age,(unsigned long long)accepted,(unsigned long long)rejected,(unsigned long long)limited);
    APPEND("Retained: %u/2048 events; priority tail: %u/128; overwrites=%llu; event window %.1f..%.1fs\n",event_count,priority_count,(unsigned long long)(accepted-event_count),event_count?at(0)->time:0,event_count?at(event_count-1)->time:0);
    APPEND("Continuous until app exit; four-store JS LRU, rotating aliases/labels; native rate limits 64 regular + 16 priority events/s. Missing stages are unobserved, not dropped.\n");
    APPEND("Stages: translate=1 emit-enter=2 emit-return=3 store=4 list=5 local-layout=6 window=7 viewport=8 error=9 state=10 retire=11 admission=12 list-life=13 sample-frame=14 row-ref=15 coverage-loss=16\n");
    APPEND("Flags own/provider/native/paused/hidden/suspended=1/2/4/8/16/32; list data/render=1/2; error TypeError/RangeError/other=1/2/3. Stage masks and counters cover retained events only.\n");
    for(unsigned i=0;i<count;i++){
        Session *s=&report_sessions[i];
        APPEND("Session %u cycle=%u retained translate/emit/store/list/layout/window/error/state=%u/%u/%u/%u/%u/%u/%u/%u; null all/own=%u/%u\n",s->id,s->cycle,s->counts[1],s->counts[2],s->counts[4],s->counts[5],s->counts[6],s->counts[7],s->counts[9],s->counts[10],s->nulls,s->null_own);
        APPEND("Admission observed=%s subscription=%u hooks=%u/2; state observed=%s age=%.1fs flags=%u lines=%.0f connected=%.0f; viewport=%s age=%.1fs frame=%u latest-sample=%u\n",s->counts[12]?"yes":"no",s->subscription,s->hooks,s->state_known?"yes":"no",s->state_known?age-s->state_time:0,s->state_flags,s->lines,s->connected,s->viewport_known?"measured":"unknown",s->viewport_known?age-s->viewport_time:0,s->viewport_frame,s->sample_frame);
        unsigned printed=0;
        for(unsigned pass=0;pass<2;pass++)for(unsigned j=0;j<s->rows && printed<28;j++){
            Row *r=&s->row[j];bool important=(r->flags&1)||r->error||r->emit_error;if(important!=(pass==0))continue;
            const char *visible="unknown";
            if(r->window && s->viewport_known && r->frame==s->sample_frame && r->frame==s->viewport_frame && r->cycle==s->viewport_cycle && r->cycle==s->cycle)
                visible=r->rect[1]+r->rect[3]>s->viewport[1]&&r->rect[1]<s->viewport[1]+s->viewport[3]?"vertical-overlap":"outside";
            APPEND("s%u m%u cycle=%u age=%.1f flags=%u stages=%u list=%u error=%u emit-error=%u local=%s height=%.2f frame=%u window-age=%.1f y/h=%.2f/%.2f visibility=%s\n",s->id,r->id,r->cycle,age-r->time,r->flags,r->mask,r->list,r->error,r->emit_error,(r->mask&(1U<<6))?"observed":"unobserved",r->height,r->frame,r->window?age-r->window_time:0,r->rect[1],r->rect[3],visible);printed++;
        }
        APPEND("Rows shown/retained-labels=%u/%u (latest 256 labels maximum).\n",printed,s->rows);
    }
    APPEND("Priority/lifecycle tail (latest 32; may predate event window):\n");
    unsigned begin=priority_count>32?priority_count-32:0;
    for(unsigned i=begin;i<priority_count;i++){
        const Packet *p=&priority[(priority_at+PRIORITY-priority_count+i)%PRIORITY];
        APPEND("t=%.1f seq=%llu e=%.0f s=%.0f m=%.0f flags=%.0f cycle=%.0f a/b=%.0f/%.0f\n",p->time,(unsigned long long)p->sequence,p->v[0],p->v[1],p->v[2],p->v[3],p->v[8],p->v[4],p->v[5]);
    }
    APPEND("Geometry/coverage tail (latest 48; frames align rows and viewport; cycle must also match):\n");
    unsigned selected[48],size=0;
    for(unsigned i=event_count;i>0 && size<48;i--){unsigned e=(unsigned)at(i-1)->v[0];if(e==7||e==8||e==14||e==16)selected[size++]=i-1;}
    for(unsigned i=size;i>0;i--){
        const Packet *p=at(selected[i-1]);
        APPEND("t=%.1f e=%.0f s=%.0f m=%.0f cycle=%.0f frame=%.0f a/b/c/d=%.2f/%.2f/%.2f/%.2f\n",p->time,p->v[0],p->v[1],p->v[2],p->v[8],p->v[9],p->v[4],p->v[5],p->v[6],p->v[7]);
    }
    APPEND("Coverage-loss a/b/c/d: regular-or-geometry suppressed / priority suppressed / probe eviction-or-measurement-busy / alias-or-stage-cache eviction. Native rate refusals above are separate.\nSample-frame a/b/c: registered probes / selected probes / global pending measurements (max 32). Geometry is sampled, not proof of painted pixels; same frame/cycle required for spatial comparisons. Snapshot scans sample 32 entries per store every 2s, within first 2000.\n");
    if(used>=capacity && capacity>60){const char *note="\n[chat trace report truncated: bounded display]\n";size_t n=strlen(note);memcpy(buffer+capacity-n-1,note,n+1);}
#undef APPEND
    pthread_mutex_unlock(&lock);
}
#endif
