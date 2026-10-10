"""Run the passive production header comparison and annotation callback.
Foundation objects are controlled here; Apple CI also exercises real objects.
"""
import unittest
import test_protocol as protocol_tests

MAIN=protocol_tests.MAIN[:protocol_tests.MAIN.index('int main(void)')]+r'''
static id response(void) {
    id r=fresh("response");r->probe_kind=1;r->probe_headers=fresh("headers");r->probe_headers->probe_kind=2;return r;
}
static void set(id dictionary,const char *key,id value) {vmsg2(dictionary,"setObject:forKey:",value,nsstr(key));}
static void inspect(id r,unsigned expected) {
    unsigned outcomes[IMAGE_HEADER_FIELDS];image_header_inspect(r,outcomes);
    assert(outcomes[0]==expected);
    for(unsigned i=1;i<IMAGE_HEADER_FIELDS;i++)assert(outcomes[i]==IMAGE_HEADER_NEITHER);
}
static unsigned callbacks;
static void propose(id r,id task_response) {
    id task=fresh("task");task->request=protocol("https://cdn.7tv.app/emote/PRIVATE-SENTINEL/2x.gif")->request;
    task->response=task_response;image_cache_mark_task(task);
    id proposed=fresh("cached");proposed->response=r;proposed->info=fresh("original-info");
    proposed->data=fresh("PRIVATE-BODY");proposed->cache_policy=1;
    unsigned entries=r->probe_headers->entries;uint64_t rejected=image_cache_rejections[IMAGE_CACHE_DATE_MISSING];
    image_cache_proposed(nil,nil,nil,task,proposed,(id)^(id result){assert(result==proposed);callbacks++;});
    /* Observation must not repair a missing accessor or alter the proposal. */
    assert(image_cache_rejections[IMAGE_CACHE_DATE_MISSING]==rejected+1);
    assert(!proposed->info->entries && r->probe_headers->entries==entries);
}
int main(void) {
    (void)complete_hls;
    id boot=protocol("https://cdn.7tv.app/emote/boot/2x.gif");assert(protocol_can_init(nil,nil,boot->request));
    protocol_start_loading(boot,nil);id boot_task=task_for(boot);protocol_stop_loading(boot,nil);
    complete(boot_task,fresh("GIF89a"),fresh("response"),nil);
    id value=nsstr("PRIVATE-DATE-VALUE"),r=response();inspect(r,IMAGE_HEADER_NEITHER);
    set(r,"Date",value);inspect(r,IMAGE_HEADER_ACCESSOR_ONLY);
    r=response();set(r->probe_headers,"dAtE",value);inspect(r,IMAGE_HEADER_DICTIONARY_ONLY);
    propose(r,r); /* same response, dictionary-only stays rejected */
    id different=response();set(different,"DATE",value);set(different->probe_headers,"date",value);
    propose(r,different);propose(r,nil);
    assert(image_header_observations==3 && image_cache_proposals==3 && callbacks==3);
    assert(image_header_response_identity[0]==1 && image_header_response_identity[1]==1 && image_header_response_identity[2]==1);
    assert(image_header_counts[0][0][IMAGE_HEADER_DICTIONARY_ONLY]==3);
    assert(image_header_counts[1][0][IMAGE_HEADER_DICTIONARY_ONLY]==1 && image_header_counts[1][0][IMAGE_HEADER_EQUAL]==1 &&
           image_header_counts[1][0][IMAGE_HEADER_UNINSPECTABLE]==1);
    set(r,"date",value);inspect(r,IMAGE_HEADER_EQUAL);
    set(r,"date",nsstr("PRIVATE-OTHER-VALUE"));inspect(r,IMAGE_HEADER_DIFFERENT);
    set(r->probe_headers,"DATE",value);inspect(r,IMAGE_HEADER_AMBIGUOUS);
    r=response();set(r->probe_headers,"Date",value);r->probe_headers->probe_repeat=129;
    unsigned outcomes[IMAGE_HEADER_FIELDS];image_header_inspect(r,outcomes);
    for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++)assert(outcomes[i]==IMAGE_HEADER_UNINSPECTABLE);
    r=response();set(r->probe_headers,"Date",value);r->probe_headers->probe_repeat=128;
    image_header_inspect(r,outcomes);assert(outcomes[0]==IMAGE_HEADER_AMBIGUOUS); /* exact limit can finish */
    id invalid=nsstr("non-string");invalid->probe_kind=3;
    r=response();set(r->probe_headers,"Date",invalid);image_header_inspect(r,outcomes);assert(outcomes[0]==IMAGE_HEADER_UNINSPECTABLE);
    r=response();set(r,"Date",invalid);image_header_inspect(r,outcomes);assert(outcomes[0]==IMAGE_HEADER_UNINSPECTABLE);
    r=response();r->probe_headers->entries=1;r->probe_headers->keys[0]=invalid;r->probe_headers->values[0]=value;
    image_header_inspect(r,outcomes);for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++)assert(outcomes[i]==IMAGE_HEADER_UNINSPECTABLE);
    r=response();r->probe_headers=nil;image_header_inspect(r,outcomes);assert(outcomes[0]==IMAGE_HEADER_UNINSPECTABLE);
    r=response();r->probe_headers->probe_kind=3;image_header_inspect(r,outcomes);assert(outcomes[0]==IMAGE_HEADER_UNINSPECTABLE);
    image_header_inspect(nil,outcomes);assert(outcomes[0]==IMAGE_HEADER_UNINSPECTABLE);
    image_header_inspect(invalid,outcomes);assert(outcomes[0]==IMAGE_HEADER_UNINSPECTABLE);
    r=response();
    static const char *names[]={"dAtE","cache-control","AGE","eXpIrEs"};
    for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++){set(r,names[i],value);set(r->probe_headers,names[i],value);}
    image_header_inspect(r,outcomes);for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++)assert(outcomes[i]==IMAGE_HEADER_EQUAL);
    for(unsigned scope=0;scope<2;scope++)for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++) {
        uint64_t total=0;for(unsigned j=0;j<IMAGE_HEADER_OUTCOMES;j++)total+=image_header_counts[scope][i][j];
        assert(total==image_header_observations);
    }
    char report[8192];tas_image_transport_status(report,sizeof(report));
    assert(strstr(report,"Header probe proposed Date: 0/0/3/0/0/0/0"));
    assert(strstr(report,"Header probe task Date: 0/0/1/1/0/0/1"));
    assert(strstr(report,"Header probe task Expires:")); /* complete report fits */
    assert(!strstr(report,"PRIVATE-") && !strstr(report,"cdn.7tv.app") && !strstr(report,"non-string"));
    char small[48];memset(small,'Z',sizeof(small));small[0]=0;image_header_status(small,32);
    assert(small[31]==0 && small[32]=='Z');
    return 0;
}
'''

class CacheHeaderProbeTests(unittest.TestCase):
    def test_comparison_accounting_bounds_and_unchanged_annotation(self):
        protocol_tests.ProtocolTests().run_transport(True,MAIN)
