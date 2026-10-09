"""Execute the production annotation callback and every rejection counter.

Linux controls Objective-C/Foundation objects only. The same response-policy
matrix also runs with real Foundation objects in test_foundation_cache.py.
"""
from pathlib import Path
import unittest
import test_protocol as protocol_tests

MATRIX=Path(__file__).parent/'native/cache_annotation_cases.h'
MAIN=protocol_tests.MAIN[:protocol_tests.MAIN.index('int main(void)')]+r'''
static void header(id object,const char *key,const char *value) {
    if(value)vmsg2(object,"setObject:forKey:",nsstr(value),nsstr(key));
}
static time_t fixture_wall;
static const char *fixture_date(const char *value) {
    if(!value || *value!='@')return value;
    time_t now=fixture_wall+(!strcmp(value,"@now") ? -2:7200);
    struct tm date;gmtime_r(&now,&date);static char text[64];
    strftime(text,sizeof(text),"%a, %d %b %Y %H:%M:%S GMT",&date);return text;
}
static void check_proposal(id task,id proposed,unsigned expected) {
    uint64_t counts[IMAGE_CACHE_REJECTION_COUNT];memcpy(counts,image_cache_rejections,sizeof(counts));
    uint64_t proposals=image_cache_proposals,annotated=image_cache_annotations;
    id stored=nil;id *output=&stored;unsigned deliveries=0;unsigned *calls=&deliveries;
    image_cache_proposed(nil,nil,nil,task,proposed,(id)^(id result){*output=result;(*calls)++;});
    assert(deliveries==1 && image_cache_proposals==proposals+1);
    assert(image_cache_annotations==annotated+(expected==IMAGE_CACHE_ACCEPTED));
    for(unsigned i=0;i<IMAGE_CACHE_REJECTION_COUNT;i++)
        assert(image_cache_rejections[i]==counts[i]+(i==expected && expected!=IMAGE_CACHE_ACCEPTED));
    assert(proposed->info->entries==1); /* rejected/accepted originals never mutated */
    if(expected==IMAGE_CACHE_ACCEPTED) {
        assert(stored!=proposed && stored->data==proposed->data && stored->response==proposed->response && stored->cache_policy==proposed->cache_policy);
        assert(msg1(stored->info,"objectForKey:",nsstr("fixture-marker"))==msg1(proposed->info,"objectForKey:",nsstr("fixture-marker")));
        assert(bmsg1(msg1(stored->info,"objectForKey:",nsstr("TASCacheEpoch")),"isEqual:",image_cache_epoch));
        assert(image_cache_value(msg1(stored->info,"objectForKey:",nsstr("TASCacheTick")))>=0);
        assert(image_cache_value(msg1(stored->info,"objectForKey:",nsstr("TASCacheWall")))>0);
    } else assert(stored==proposed);
}
static id proposal(id task,const AnnotationCase *c) {
    fixture_wall=time(NULL);
    id response=fresh("response"),proposed=fresh("cached");response->url=task->request->url;
    proposed->response=response;proposed->data=fresh("GIF89a");proposed->cache_policy=1;
    proposed->info=fresh("original-info");header(proposed->info,"fixture-marker","retained");
    header(response,"Cache-Control",c->control);header(response,"Date",fixture_date(c->date));
    header(response,"Expires",fixture_date(c->expires));header(response,"Age",c->age);return proposed;
}
int main(void) {
    (void)complete_hls;
    id boot=protocol("https://cdn.7tv.app/emote/fixture/2x.gif");assert(protocol_can_init(nil,nil,boot->request));
    protocol_start_loading(boot,nil);id boot_task=task_for(boot);protocol_stop_loading(boot,nil);complete(boot_task,fresh("GIF89a"),fresh("response"),nil);
    assert(image_cache_epoch && !image_active);
    for(unsigned i=0;i<sizeof(annotation_cases)/sizeof(*annotation_cases);i++) {
        const AnnotationCase *c=&annotation_cases[i];id task=fresh("annotation-task");task->request=boot->request;image_cache_mark_task(task);
        check_proposal(task,proposal(task,c),c->rejection);
    }
    /* A long control field retains its own reason rather than unknown syntax. */
    char large[1026];memset(large,'x',1025);large[1025]=0;
    AnnotationCase c={"oversize",large,"@now",NULL,NULL,IMAGE_CACHE_CONTROL_SIZE};
    id task=fresh("annotation-task");task->request=boot->request;image_cache_mark_task(task);
    check_proposal(task,proposal(task,&c),c.rejection);
    c=annotation_cases[7];
    const unsigned gates[]={IMAGE_CACHE_START_MISSING,IMAGE_CACHE_START_INVALID,IMAGE_CACHE_START_FUTURE,
        IMAGE_CACHE_REQUEST_PRIVATE,IMAGE_CACHE_REQUEST_POLICY,IMAGE_CACHE_REQUEST_DIRECTIVES,IMAGE_CACHE_RESPONSE_STATUS,IMAGE_CACHE_CONSTRUCTION};
    for(unsigned i=0;i<sizeof(gates)/sizeof(*gates);i++) {
        task=fresh("annotation-task");task->request=msg0(boot->request,"mutableCopy");image_cache_mark_task(task);
        id proposed=proposal(task,&c);
        switch(gates[i]) {
            case IMAGE_CACHE_START_MISSING: task->cache_start=nil;break;
            case IMAGE_CACHE_START_INVALID: task->cache_start=nsstr("NaN");break;
            case IMAGE_CACHE_START_FUTURE: task->cache_start=image_cache_number(image_cache_clock(IMAGE_CACHE_AGE_CLOCK)+7200);break;
            case IMAGE_CACHE_REQUEST_PRIVATE: task->request->authorization=nsstr("fixture credential");break;
            case IMAGE_CACHE_REQUEST_POLICY: task->request->cache_policy=3;break;
            case IMAGE_CACHE_REQUEST_DIRECTIVES: header(task->request,"If-None-Match","fixture validator");break;
            case IMAGE_CACHE_RESPONSE_STATUS: proposed->response->status=206;break;
            case IMAGE_CACHE_CONSTRUCTION: fail_cached_response=true;break;
        }
        check_proposal(task,proposed,gates[i]);fail_cached_response=false;
    }
    uint64_t rejected=0;
    for(unsigned i=1;i<IMAGE_CACHE_REJECTION_COUNT;i++){assert(image_cache_rejections[i]);rejected+=image_cache_rejections[i];}
    assert(image_cache_annotations+rejected==image_cache_proposals && !image_cache_rejections[0]);
    char report[4096];tas_image_transport_status(report,sizeof(report));
    assert(strstr(report,"Annotation rejection task start missing/invalid/future: 1/1/1"));
    assert(strstr(report,"Annotation rejection request private/policy/directives; response status: 1/1/1; 1"));
    assert(strstr(report,"Annotation rejection Date missing/invalid/future; Age invalid: 1/4/1; 3"));
    assert(strstr(report,"Annotation rejection control size/max-age invalid/duplicate/no-cache/no-store: 1/2/3/2/1"));
    assert(strstr(report,"Annotation rejection extension value/unsupported directive/Expires missing/invalid/nonpositive lifetime/construction: 1/3/1/1/2/1"));
    assert(strstr(report,"annotated + rejections = proposals"));
    assert(!strstr(report,"fixture credential") && !strstr(report,"fixture validator") && !strstr(report,"cdn.7tv.app") && !strstr(report,"Cache-Control"));
    return 0;
}
'''
MAIN=MAIN.replace('static void header(', '#include "'+str(MATRIX.resolve())+'"\nstatic void header(',1)

class CacheAnnotationTests(unittest.TestCase):
    def test_actual_annotation_conditions_and_policy_matrix(self):
        protocol_tests.ProtocolTests().run_transport(False,MAIN)

    def test_actual_annotation_counters_with_demand_diagnostics(self):
        protocol_tests.ProtocolTests().run_transport(True,MAIN)
