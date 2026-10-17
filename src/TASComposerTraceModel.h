#ifndef TAS_COMPOSER_TRACE_MODEL_H
#define TAS_COMPOSER_TRACE_MODEL_H
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
/* Numeric packets only: no text, names, URLs, object pointers or unbounded data. */
#define TAS_CT_SLOTS 128U
#define TAS_CT_EXPORT 64U
typedef struct {
    uint64_t ms;
    unsigned event,owner,editor,session,flags,depth,hidden_depth;
    int rect[4],ancestor[4],window[2],keyboard[4];
    unsigned length,selection,selection_length,adjacent;
    int font,base_font,resolved_font,run_before_font,run_after_font;
    uint32_t color,base_color,resolved_color,run_before_color,run_after_color;
} TASComposerSample;
typedef struct {
    TASComposerSample samples[TAS_CT_SLOTS];
    unsigned next,count,budget_count;
    uint64_t accepted,overwritten,rate_dropped,coalesced,budget_second;
} TASComposerRing;
static inline int tas_ct_number(double x){return !isfinite(x)?-100001:(int)round(fmax(-100000,fmin(100000,x)));}
static inline int tas_ct_point_size(double x){return !isfinite(x)||x<0||x>1000?-1:(int)round(x*10);}
static inline int tas_ct_budget(TASComposerRing *r,uint64_t ms){
    uint64_t second=ms/1000;
    if(r->budget_second!=second){r->budget_second=second;r->budget_count=0;}
    if(r->budget_count>=120){r->rate_dropped++;return 0;}r->budget_count++;return 1;
}
static inline void tas_ct_store(TASComposerRing *r,const TASComposerSample *s){
    if((s->event==1||s->event==12)&&r->count){
        for(unsigned i=0;i<r->count;i++){
            TASComposerSample old=r->samples[(r->next+TAS_CT_SLOTS-1-i)%TAS_CT_SLOTS],copy=*s;
            if(old.owner!=s->owner)continue;
            old.ms=copy.ms=0;
            if(!memcmp(&old,&copy,sizeof(old))){r->coalesced++;return;}
            break;
        }
    }
    r->samples[r->next]=*s;r->next=(r->next+1)%TAS_CT_SLOTS;
    if(r->count<TAS_CT_SLOTS)r->count++;else r->overwritten++;
    r->accepted++;
}
static inline void tas_ct_report(const TASComposerRing *r,char *b,size_t cap){
    if(!b||!cap)return;
    unsigned n=r->count<TAS_CT_EXPORT?r->count:TAS_CT_EXPORT;
    int h=snprintf(b,cap,"RN composer trace: retained=%u/%u accepted=%llu overwritten=%llu rate-dropped=%llu coalesced=%llu export-omitted=%u\n"
        "Latest %u numeric samples, oldest first; ms=monotonic. Font sizes are tenths of a point; color=RGBA hex (0=unavailable or transparent black). No draft contents.\n",
        r->count,TAS_CT_SLOTS,(unsigned long long)r->accepted,(unsigned long long)r->overwritten,
        (unsigned long long)r->rate_dropped,(unsigned long long)r->coalesced,r->count-n,n);
    if(h<0)return;size_t used=(size_t)h<cap?(size_t)h:cap-1;
    for(unsigned i=0;i<n;i++){
        const TASComposerSample *s=&r->samples[(r->next+TAS_CT_SLOTS-n+i)%TAS_CT_SLOTS];
        char line[768];
        int len=snprintf(line,sizeof(line),"%llu e%u o%u i%u j%u f%x d%u hidden%u r[%d,%d,%d,%d] clip[%d,%d,%d,%d] win[%d,%d] kb[%d,%d,%d,%d] len%u sel[%u,%u] adj%x\n"
            " font[t,b,r,prev,next]=%d,%d,%d,%d,%d color=%08x,%08x,%08x,%08x,%08x\n",
            (unsigned long long)s->ms,s->event,s->owner,s->editor,s->session,s->flags,s->depth,s->hidden_depth,
            s->rect[0],s->rect[1],s->rect[2],s->rect[3],s->ancestor[0],s->ancestor[1],s->ancestor[2],s->ancestor[3],
            s->window[0],s->window[1],s->keyboard[0],s->keyboard[1],s->keyboard[2],s->keyboard[3],
            s->length,s->selection,s->selection_length,s->adjacent,s->font,s->base_font,s->resolved_font,s->run_before_font,s->run_after_font,
            s->color,s->base_color,s->resolved_color,s->run_before_color,s->run_after_color);
        if(len<0)break;
        if(used+(size_t)len+96>=cap){snprintf(b+used,cap-used,"[composer export truncated: %u samples omitted by output capacity]\n",n-i);return;}
        memcpy(b+used,line,(size_t)len);used+=(size_t)len;b[used]=0;
    }
}
#endif
