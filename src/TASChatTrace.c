#include "TASChatTrace.h"
#if TAS_CHAT_TRACE_DIAGNOSTIC
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>
#include <time.h>
typedef struct {unsigned mask,flags,error,emit_error,list;double height,y,window_height;bool window;} Row;
typedef struct {Row rows[256];double viewport[4];bool viewport_known;unsigned events[13],stop,subscription,hooks,null_translation,null_own,state_flags;double line_count,connected;} Session;
static Session sessions[2];
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static unsigned accepted,rejected;
static double started;
static bool began;
#ifndef TAS_CHAT_TRACE_NOW
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (double)t.tv_sec+t.tv_nsec/1e9;}
#define TAS_CHAT_TRACE_NOW() now()
#endif
/* Only eight JSON numbers, never JSON strings/objects or arbitrary text.
 * Enforce JSON number syntax before strtod; the native report stores numbers only. */
static bool parse(const char *p,double out[8]) {
    if(!p || strnlen(p,257)>256 || *p++!='[')return false;
    for(unsigned i=0;i<8;i++) {
        while(*p==' ' || *p=='\t')p++;
        const char *start=p;if(*p=='-')p++;
        if(*p=='0')p++;else {if(*p<'1' || *p>'9')return false;do {p++;}while(*p>='0'&&*p<='9');}
        if(*p=='.'){p++;if(*p<'0'||*p>'9')return false;do {p++;}while(*p>='0'&&*p<='9');}
        if(*p=='e'||*p=='E'){p++;if(*p=='+'||*p=='-')p++;if(*p<'0'||*p>'9')return false;do {p++;}while(*p>='0'&&*p<='9');}
        char *end;out[i]=strtod(start,&end);
        if(end!=p || !isfinite(out[i]) || fabs(out[i])>10000000)return false;
        while(*p==' ' || *p=='\t')p++;
        if(*p!=(i==7?']':','))return false;
        p++;
    }
    return !*p;
}
bool tas_chat_trace_packet(const char *packet) {
    double v[8];bool valid=parse(packet,v);
    if(valid)for(unsigned i=0;i<4;i++)if(v[i]<0 || floor(v[i])!=v[i])valid=false;
    if(valid && (v[0]>12 || v[1]<1 || v[1]>2 || v[2]>256 || v[3]>255))valid=false;
    if(valid && (v[0]==9 || v[0]==11) && (v[4]<1 || v[4]>3 || floor(v[4])!=v[4]))valid=false;
    if(valid && v[0]==3 && (v[4]<0 || v[4]>1 || floor(v[4])!=v[4] || v[5]<0 || v[5]>3 || floor(v[5])!=v[5]))valid=false;
    if(valid && v[0]==5 && v[4]!=1 && v[4]!=2)valid=false;
    if(valid && v[0]==12 && (v[4]<0 || v[4]>1 || v[5]<0 || v[5]>2 || floor(v[4])!=v[4] || floor(v[5])!=v[5]))valid=false;
    pthread_mutex_lock(&lock);
    double t=TAS_CHAT_TRACE_NOW();
    if(!valid || accepted>=1536 || (began && t-started>130)) {if(rejected<1000000)rejected++;pthread_mutex_unlock(&lock);return false;}
    if(!began){started=t;began=true;}
    unsigned e=(unsigned)v[0],s=(unsigned)v[1]-1,line=(unsigned)v[2];Session *session=&sessions[s];
    if(session->stop && e!=11){pthread_mutex_unlock(&lock);return false;}
    accepted++;session->events[e]++;
    if(e==1 && !v[4]){session->null_translation++;if((unsigned)v[3]&1)session->null_own++;}
    if(e==10){session->state_flags=(unsigned)v[3];session->line_count=v[4];session->connected=v[5];}
    if(e==8){memcpy(session->viewport,v+4,sizeof(session->viewport));session->viewport_known=v[6]>0&&v[7]>0;}
    if(e==11)session->stop=(unsigned)v[4];
    if(e==12){session->subscription=(unsigned)v[4];session->hooks=(unsigned)v[5];}
    if(line) {
        Row *r=&session->rows[line-1];r->mask|=1U<<e;r->flags|=(unsigned)v[3];
        if(e==6)r->height=v[4];
        if(e==7){r->y=v[5];r->window_height=v[7];r->window=v[6]>0&&v[7]>0;}
        if(e==9)r->error=(unsigned)v[4];
        if(e==3 && !v[4])r->emit_error=(unsigned)v[5];
        if(e==5)r->list|=1U<<((unsigned)v[4]-1);
    }
    pthread_mutex_unlock(&lock);return true;
}
void tas_chat_trace_status(char *buffer,size_t capacity) {
    if(!buffer||!capacity)return;
    pthread_mutex_lock(&lock);size_t used=0;
#define APPEND(...) do {if(used<capacity){int n=snprintf(buffer+used,capacity-used,__VA_ARGS__);if(n>0)used+=(size_t)n;}} while(0)
    APPEND("\nRN chat trace (bounded; content-free)\nPackets accepted/refused: %u/%u; limits: 2 sessions, 256 labels/session, 1536 packets, 120 seconds JS\n",accepted,rejected);
    APPEND("Stages: translate=1 emit-enter=2 emit-return=3 store-seen=4 list-data=5 row-layout=6 window=7 viewport=8 row-error=9 state=10 stop=11 admission=12\nFlags: own=1 provider=2 native=4 paused=8 hidden=16 suspended=32\n");
    APPEND("List bits: data=1 render-callback=2; error codes: TypeError=1 RangeError=2 other=3; stop: active=0 timer=1 budget=2\n");
    for(unsigned s=0;s<2;s++) {
        Session *q=&sessions[s];if(!q->events[0])continue;
        APPEND("Session %u events translate/emit/store/list/layout/window/error/state: %u/%u/%u/%u/%u/%u/%u/%u; stop=%u viewport=%s subscription=%u hooks=%u/2\n",s+1,q->events[1],q->events[2],q->events[4],q->events[5],q->events[6],q->events[7],q->events[9],q->events[10],q->stop,q->viewport_known?"measured":"unknown",q->subscription,q->hooks);
        APPEND("Null translations/all-own: %u/%u; last state flags=%u lines=%.0f connected=%.0f\n",q->null_translation,q->null_own,q->state_flags,q->line_count,q->connected);
        unsigned printed=0;
        /* Prioritize own/error/incomplete rows, then ordinary observations. */
        for(unsigned pass=0;pass<2;pass++)for(unsigned i=0;i<256&&printed<48;i++) {
            Row *r=&q->rows[i];if(!r->mask)continue;
            bool priority=(r->flags&1) || r->error || ((r->mask&(1U<<2))&&!(r->mask&(1U<<4)));
            if(priority!=(pass==0))continue;
            const char *visible="unknown";
            if(r->window&&q->viewport_known)visible=(r->y+r->window_height>q->viewport[1]&&r->y<q->viewport[1]+q->viewport[3])?"vertical-overlap":"outside";
            APPEND("s%u m%u flags=%u stages=%u list=%u error=%u emit-error=%u row-height=%.2f window-y/h=%.2f/%.2f visibility=%s\n",s+1,i+1,r->flags,r->mask,r->list,r->error,r->emit_error,r->height,r->y,r->window_height,visible);printed++;
        }
    }
    APPEND("Absence of an observed stage is not proof of a drop. Geometry is a sampled snapshot, not pixel visibility.\n");
#undef APPEND
    pthread_mutex_unlock(&lock);
}
#endif
