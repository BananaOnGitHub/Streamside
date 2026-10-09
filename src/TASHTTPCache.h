/* Conservative private-cache freshness. Unsupported syntax is a miss, never
 * permission to serve stale content. Foundation remains the validator. */
#ifndef TAS_HTTP_CACHE_H
#define TAS_HTTP_CACHE_H
#include <ctype.h>
#include <math.h>
#include <string.h>
#include <strings.h>
#include <stdlib.h>
#include <stdint.h>
/* Exactly one first rejection per proposal. No header values are reported. */
typedef enum {
    IMAGE_CACHE_ACCEPTED,
    IMAGE_CACHE_START_MISSING, IMAGE_CACHE_START_INVALID, IMAGE_CACHE_START_FUTURE,
    IMAGE_CACHE_REQUEST_PRIVATE, IMAGE_CACHE_REQUEST_POLICY, IMAGE_CACHE_REQUEST_DIRECTIVES,
    IMAGE_CACHE_RESPONSE_STATUS,
    IMAGE_CACHE_DATE_MISSING, IMAGE_CACHE_DATE_INVALID, IMAGE_CACHE_DATE_FUTURE, IMAGE_CACHE_AGE_INVALID,
    IMAGE_CACHE_CONTROL_SIZE, IMAGE_CACHE_MAX_AGE_INVALID, IMAGE_CACHE_MAX_AGE_DUPLICATE,
    IMAGE_CACHE_NO_CACHE, IMAGE_CACHE_NO_STORE, IMAGE_CACHE_EXTENSION_INVALID, IMAGE_CACHE_DIRECTIVE_UNSUPPORTED,
    IMAGE_CACHE_EXPIRES_MISSING, IMAGE_CACHE_EXPIRES_INVALID, IMAGE_CACHE_LIFETIME_INVALID,
    IMAGE_CACHE_CONSTRUCTION, IMAGE_CACHE_REJECTION_COUNT
} ImageCacheRejection;
static bool image_cache_fail(unsigned *reason,ImageCacheRejection rejection) {*reason=rejection;return false;}
static bool image_cache_space(unsigned char c) {return c==' ' || c=='\t';}

static bool image_cache_seconds(const char *s, double *out) {
    if (!s || !*s || strnlen(s,33)>32) return false;
    double n=0;
    for (;*s;s++) { if (*s<'0' || *s>'9' || n>214748364) return false; n=n*10+(*s-'0'); }
    *out=n;return n<=2147483647;
}
/* IMF-fixdate only; obsolete/invalid dates are delegated to Foundation. */
static bool image_cache_date(const char *s, double *out) {
    char weekday[4],month[4],zone[4],tail;int d,y,h,m,sec;
    if (!s || strlen(s)!=29 || sscanf(s,"%3[^,], %d %3s %d %d:%d:%d %3s%c",
        weekday,&d,month,&y,&h,&m,&sec,zone,&tail)!=8 || weekday[3]!='\0' ||
        s[3]!=',' || strcmp(zone,"GMT") || y<1970 || y>9999 || h<0 || h>23 || m<0 || m>59 || sec<0 || sec>59) return false;
    const char *months="JanFebMarAprMayJunJulAugSepOctNovDec";int mon=0;
    for(int i=0;i<12;i++)if(!strncmp(month,months+i*3,3))mon=i+1;
    bool leap=y%4==0 && (y%100!=0 || y%400==0);
    static const int days[]={31,28,31,30,31,30,31,31,30,31,30,31};
    if(!mon || d<1 || d>days[mon-1]+(mon==2 && leap))return false;
    int64_t total=0;
    for(int year=1970;year<y;year++)total+=365+(year%4==0 && (year%100!=0 || year%400==0));
    for(int i=1;i<mon;i++)total+=days[i-1]+(i==2 && leap);
    const char *weekdays="SunMonTueWedThuFriSat";
    if(strncmp(weekday,weekdays+((total+d-1+4)%7)*3,3))return false;
    *out=(double)((total+d-1)*86400+h*3600+m*60+sec);return true;
}
static bool image_cache_lifetime_reason(const char *control,const char *date,const char *expires,double *lifetime,double *stamp,unsigned *reason) {
    *reason=IMAGE_CACHE_ACCEPTED;
    if(!date)return image_cache_fail(reason,IMAGE_CACHE_DATE_MISSING);
    if(!image_cache_date(date,stamp))return image_cache_fail(reason,IMAGE_CACHE_DATE_INVALID);
    bool max_found=false;double max_age=0;
    if(control && *control) {
        if(strlen(control)>1024)return image_cache_fail(reason,IMAGE_CACHE_CONTROL_SIZE);
        char copy[1025];strcpy(copy,control);char *cursor=copy;
        while(cursor) {
            char *next=strchr(cursor,',');if(next)*next++=0;
            while(image_cache_space((unsigned char)*cursor))cursor++;
            char *end=cursor+strlen(cursor);while(end>cursor && image_cache_space((unsigned char)end[-1]))*--end=0;
            char *value=strchr(cursor,'=');if(value) {
                *value++=0;while(image_cache_space((unsigned char)*value))value++;
                end=cursor+strlen(cursor);while(end>cursor && image_cache_space((unsigned char)end[-1]))*--end=0;
                end=value+strlen(value);if(end>value+1 && *value=='"' && end[-1]=='"'){value++;*--end=0;}
            }
            if(!strcasecmp(cursor,"max-age")) {
                if(max_found)return image_cache_fail(reason,IMAGE_CACHE_MAX_AGE_DUPLICATE);
                if(!image_cache_seconds(value,&max_age))return image_cache_fail(reason,IMAGE_CACHE_MAX_AGE_INVALID);max_found=true;
            } else if(!strcasecmp(cursor,"no-cache"))return image_cache_fail(reason,IMAGE_CACHE_NO_CACHE);
            else if(!strcasecmp(cursor,"no-store"))return image_cache_fail(reason,IMAGE_CACHE_NO_STORE);
            else if(!strcasecmp(cursor,"s-maxage") || !strcasecmp(cursor,"stale-while-revalidate") || !strcasecmp(cursor,"stale-if-error")) {
                double ignored;if(!image_cache_seconds(value,&ignored))return image_cache_fail(reason,IMAGE_CACHE_EXTENSION_INVALID);
            } else if(strcasecmp(cursor,"public") && strcasecmp(cursor,"private") && strcasecmp(cursor,"must-revalidate") &&
                      strcasecmp(cursor,"proxy-revalidate") && strcasecmp(cursor,"immutable") && strcasecmp(cursor,"no-transform"))return image_cache_fail(reason,IMAGE_CACHE_DIRECTIVE_UNSUPPORTED);
            else if(value)return image_cache_fail(reason,IMAGE_CACHE_DIRECTIVE_UNSUPPORTED); /* field-qualified private is uncertain */
            cursor=next;
        }
    }
    if(max_found)*lifetime=max_age;
    else {double expiry;
        if(!expires)return image_cache_fail(reason,IMAGE_CACHE_EXPIRES_MISSING);
        if(!image_cache_date(expires,&expiry))return image_cache_fail(reason,IMAGE_CACHE_EXPIRES_INVALID);*lifetime=expiry-*stamp;}
    return (*lifetime>0 && isfinite(*lifetime)) || image_cache_fail(reason,IMAGE_CACHE_LIFETIME_INVALID);
}
static bool image_cache_lifetime(const char *control,const char *date,const char *expires,double *lifetime,double *stamp) {
    unsigned reason;return image_cache_lifetime_reason(control,date,expires,lifetime,stamp,&reason);
}
#endif
