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
static bool image_cache_lifetime(const char *control,const char *date,const char *expires,double *lifetime,double *stamp) {
    if(!image_cache_date(date,stamp))return false;
    bool max_found=false;double max_age=0;
    if(control && *control) {
        if(strlen(control)>1024)return false;
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
                if(max_found || !image_cache_seconds(value,&max_age))return false;max_found=true;
            } else if(!strcasecmp(cursor,"no-cache") || !strcasecmp(cursor,"no-store"))return false;
            else if(!strcasecmp(cursor,"s-maxage") || !strcasecmp(cursor,"stale-while-revalidate") || !strcasecmp(cursor,"stale-if-error")) {
                double ignored;if(!image_cache_seconds(value,&ignored))return false;
            } else if(strcasecmp(cursor,"public") && strcasecmp(cursor,"private") && strcasecmp(cursor,"must-revalidate") &&
                      strcasecmp(cursor,"proxy-revalidate") && strcasecmp(cursor,"immutable") && strcasecmp(cursor,"no-transform"))return false;
            else if(value)return false; /* field-qualified private is uncertain */
            cursor=next;
        }
    }
    if(max_found)*lifetime=max_age;
    else {double expiry;if(!image_cache_date(expires,&expiry))return false;*lifetime=expiry-*stamp;}
    return *lifetime>0 && isfinite(*lifetime);
}
#endif
