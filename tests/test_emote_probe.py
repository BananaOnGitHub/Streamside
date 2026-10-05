"""Opt-in missing-emote tracing observes production paths without rewriting them."""
import os
import shutil
import unittest
import test_composer as composer
from test_composer_library import replace_body
from test_emote_picker import HARNESS

MAIN = r'''
int main(void) {
    (void)expect; (void)expire_locked; (void)fetch_provider;
    g_enabled=true;
    Room *room=room_locked("123",time(NULL));
    snprintf(room->login,sizeof(room->login),"privateChannel");
    room->loaded[0]=true;room->pending[1]=true;room->failures[2]=2;
    add(room,"MissingEmote",0,false);
    uint64_t number=find_word(room,"MissingEmote")->fake_id;
    char report[196608],tiny[9];
    const char *early_url=find_word(room,"MissingEmote")->url;
    tas_emotes_image_protocol_request(early_url);
    tas_emotes_image_result_for_url(early_url,nil,nil,nil);
    tas_emote_probe_image(number,7,"assign-animation-before","early-decoded frames=4");
    tas_emote_probe_record(number,7,"decode-result","decoder=GIF frames=4",false);
    tas_emote_probe_record(number,7,"decode-handoff","decision=chat-task-animated-result",false);
    tas_emote_probe_record(number,7,"result-origin","object=1 creator=native-static-imageio",false);
    tas_emote_probe_record(number,0,"decision-request-entry","entry=animated key=1",false);
    tas_emote_probe_record(number,0,"decision-cache-lookup","native-slot=animated raw=empty",false);
    tas_emote_probe_record(number,1,"sample","before-selection ticks=100 advances=99",true);
    tas_emote_probe_record(25,1,"sample","native-emote-must-not-record",true);
    assert(!tas_emote_probe_set(NULL) && !tas_emote_probe_set(""));
    assert(!tas_emote_probe_set("two words") && !tas_emote_probe_set("line\nbreak"));
    char oversized[98];memset(oversized,'x',97);oversized[97]=0;
    assert(!tas_emote_probe_set(oversized));
    tas_emote_probe_status(report,sizeof(report));assert(strstr(report,"Select Inspect Emote"));
    assert(tas_emote_probe_set("MissingEmote"));
    tas_emote_probe_status(report,sizeof(report));assert(strstr(report,"before-selection ticks=100"));
    assert(strstr(report,"Image history") && strstr(report,"image-protocol-start") && strstr(report,"image-response"));
    assert(strstr(report,"Assignment") && strstr(report,"early-decoded frames=4"));
    assert(strstr(report,"Decode age=") && strstr(report,"Handoff age="));
    assert(strstr(report,"Result origin age=") && strstr(report,"creator=native-static-imageio"));
    assert(strstr(report,"Request entry age=") && strstr(report,"entry=animated key=1"));
    assert(strstr(report,"Cache decision age=") && strstr(report,"native-slot=animated raw=empty"));
    assert(!strstr(report,"native-emote-must-not-record"));
    const char *line="@room-id=123;emotes= :privateSender!x@y PRIVMSG #privateChannel :SecretRawChatword MissingEmote";
    char *rewritten=rewrite_line(line,strlen(line));assert(rewritten);
    assert(strstr(rewritten,"SecretRawChatword MissingEmote"));
    char expected[96];snprintf(expected,sizeof(expected),"%llu:18-29",(unsigned long long)number);
    assert(strstr(rewritten,expected));free(rewritten);
    tas_emote_probe_text("native-delivery","SecretRawChatword MissingEmote","123","literal-text-token");
    tas_emote_probe_stage(number,"chat-token-sizing");
    tas_emote_probe_stage(number,"chat-image-layer-layout");
    tas_emote_probe_status(report,sizeof(report));
    assert(strstr(report,"Exact catalog hit channel/global: yes/no"));
    assert(strstr(report,"Stage incoming tag-appended: 1"));
    assert(strstr(report,"Stage native-delivery literal-text-token: 1"));
    assert(strstr(report,"Stage chat-token-sizing reached: 1"));
    assert(strstr(report,"pending: 0/1/0; failures: 0/0/2"));
    assert(!strstr(report,"privateChannel") && !strstr(report,"privateSender") && !strstr(report,"SecretRawChatword"));
    assert(!strstr(report,"https://") && !strstr(report,"room-id="));
    /* A native tag occupying the code remains unchanged, with an explicit reason. */
    const char *overlap="@room-id=123;emotes=25:0-11 :x!y@z PRIVMSG #privateChannel :MissingEmote";
    assert(!rewrite_line(overlap,strlen(overlap)));
    tas_emote_probe_status(report,sizeof(report));assert(strstr(report,"Stage incoming native-overlap: 1"));
    assert(tas_emote_probe_set("missingemote"));
    line="@room-id=123;emotes= :x!y@z PRIVMSG #privateChannel :missingemote";
    assert(!rewrite_line(line,strlen(line)));
    tas_emote_probe_status(report,sizeof(report));
    assert(strstr(report,"Exact catalog hit channel/global: no/no"));
    assert(strstr(report,"case variants in current scope: 1"));
    assert(strstr(report,"Stage incoming catalog-miss: 1"));
    assert(!strstr(report,"tag-appended")); /* New target resets prior observations. */
    /* Resolve the actual supplied scope; a missing identity cannot fall back
     * silently to the most recently visited channel in the probe snapshot. */
    tas_emote_probe_observe("composer","missingemote","999","literal-text");
    tas_emote_probe_status(report,sizeof(report));assert(strstr(report,"context: missing"));
    assert(tas_emote_probe_set("MissingEmote"));
    line="@emotes= :x!y@z PRIVMSG #privateChannel :MissingEmote";
    assert(!rewrite_line(line,strlen(line)));
    tas_emote_probe_status(report,sizeof(report));assert(strstr(report,"room-id-missing-or-invalid"));
    line=":x!y@z PRIVMSG #privateChannel :MissingEmote";
    assert(!rewrite_line(line,strlen(line)));
    tas_emote_probe_status(report,sizeof(report));assert(strstr(report,"untagged-line"));
    /* Repeated refreshes are counted but coalesced in the bounded timeline. */
    assert(tas_emote_probe_set("MissingEmote"));
    for (int i=0;i<100;i++) tas_emote_probe_observe("named-lookup","MissingEmote","123","catalog-hit");
    tas_emote_probe_status(report,sizeof(report));
    assert(strstr(report,"Target events: 100; retained: 1"));
    assert(strstr(report,"Stage named-lookup catalog-hit: 100"));
    for (int i=0;i<100;i++) tas_emote_probe_observe("composer","MissingEmote","123",i%2 ? "provider-preview" : "literal-text");
    tas_emote_probe_status(report,sizeof(report));assert(strstr(report,"retained: 48"));
    memset(tiny,0xff,sizeof(tiny));tas_emote_probe_status(tiny,sizeof(tiny));assert(tiny[8]==0);
    /* Attribute starts, cancellation and URL-less failures by the request,
     * without publishing the asset URL or NSError's private descriptions. */
    assert(tas_emote_probe_set("MissingEmote"));
    const char *url=find_word(room,"MissingEmote")->url;
    tas_emotes_image_protocol_request(url);
    tas_emotes_image_protocol_cancel(url);
    id error=fresh("NSError");error->number=(uint64_t)(int64_t)-1001;
    tas_emotes_image_result_for_url(url,nil,nil,error);
    tas_emote_probe_status(report,sizeof(report));
    assert(strstr(report,"Stage image-protocol-start reached: 1"));
    assert(strstr(report,"Stage image-protocol-cancel cancelled-before-completion: 1"));
    assert(strstr(report,"http=0 error=-1001 body=0 type=other"));
    assert(!strstr(report,"https://") && !strstr(report,"privateChannel"));
    image_probe_url("https://cdn.7tv.app/emote/unrelated/2x","image-response","unrelated");
    tas_emote_probe_status(report,sizeof(report));assert(!strstr(report,"unrelated"));
    /* Playback precedes selection; visible samples and cleanup are separate. */
    uint64_t generation=tas_emote_probe_generation(number); assert(generation);
    assert(!tas_emote_probe_generation(25));
    tas_emote_probe_playback(generation,25,"unrelated-playback");
    uint64_t playback_start=g_playback_sequence;
    for (int i=0;i<80;i++) tas_emote_probe_playback(generation,number,"ticks=80 advances=4 link=running");
    for (int i=0;i<100;i++) tas_emote_probe_stage(number,i%2 ? "chat-token-sizing" : "chat-image-layer-layout");
    tas_emote_probe_status(report,sizeof(report));
    assert(strstr(report,"16 visible samples + 16 transitions + 4 last-visible layers"));
    assert(!strstr(report,"unrelated-playback"));
    char boundary[80];snprintf(boundary,sizeof(boundary),"Playback #%llu ",(unsigned long long)(playback_start+65));assert(strstr(report,boundary));
    snprintf(boundary,sizeof(boundary),"Playback #%llu ",(unsigned long long)(playback_start+80));assert(strstr(report,boundary));
    snprintf(boundary,sizeof(boundary),"Playback #%llu ",(unsigned long long)(playback_start+64));assert(!strstr(report,boundary));
    assert(strstr(report,"ticks=80 advances=4 link=running"));
    memset(tiny,0xff,sizeof(tiny));tas_emote_probe_status(tiny,sizeof(tiny));assert(tiny[8]==0);
    assert(tas_emote_probe_set("MissingEmote"));
    tas_emote_probe_playback(generation,number,"stale-sample");
    tas_emote_probe_status(report,sizeof(report));
    assert(strstr(report,"ticks=80 advances=4") && !strstr(report,"stale-sample"));
    assert(tas_emote_probe_generation(number)!=generation);
    tas_emote_probe_record(number,7,"sample","visible-before-cleanup animation=1",true);
    tas_emote_probe_record(number,7,"last-frame-progress","healthy-before-clear ticks=20 advances=20",false);
    for (unsigned i=0;i<100;i++) tas_emote_probe_record(number,7,"state-change","visibility=hidden animation=0",false);
    tas_emote_probe_record(number,7,"row-released","weak-row=gone",false);
    tas_emote_probe_status(report,sizeof(report));
    assert(strstr(report,"Last-visible") && strstr(report,"visible-before-cleanup animation=1"));
    assert(strstr(report,"Last-progress") && strstr(report,"healthy-before-clear"));
    for (unsigned i=0;i<100;i++) tas_emote_probe_image(number,7,"assign-static-after","assignment-churn");
    tas_emote_probe_status(report,sizeof(report));
    assert(strstr(report,"image-response") && strstr(report,"healthy-before-clear"));
    assert(strstr(report,"native-slot=animated raw=empty") && strstr(report,"entry=animated key=1"));
    assert(strstr(report,"row-released") && strstr(report,"weak-row=gone"));
    assert(tas_emote_probe_set("UnrelatedCode"));
    tas_emote_probe_status(report,sizeof(report));assert(!strstr(report,"visible-before-cleanup"));
    assert(tas_emote_probe_set("MissingEmote"));
    tas_emote_probe_status(report,sizeof(report));assert(strstr(report,"visible-before-cleanup"));
    /* Independent decision/request budgets retain their newest rows in order. */
    for (unsigned i=0;i<40;i++) {
        char state[48];snprintf(state,sizeof(state),"cache-marker-%02u",i);
        tas_emote_probe_record(number,0,"decision-cache-lookup",state,false);
        snprintf(state,sizeof(state),"request-marker-%02u",i);
        tas_emote_probe_record(number,0,"decision-request-entry",state,false);
    }
    tas_emote_probe_status(report,sizeof(report));
    assert(strstr(report,"decisions=32 requests=16"));
    assert(!strstr(report,"cache-marker-07") && strstr(report,"cache-marker-08")<strstr(report,"cache-marker-39"));
    assert(!strstr(report,"request-marker-23") && strstr(report,"request-marker-24")<strstr(report,"request-marker-39"));
    for (unsigned i=0;i<PLAYBACK_EMOTES;i++) if (g_playback[i].number==number) {
        for (unsigned j=0;j<32;j++) g_playback[i].decisions[j].time-=PLAYBACK_SECONDS;
        for (unsigned j=0;j<PLAYBACK_ROWS;j++) g_playback[i].requests[j].time-=PLAYBACK_SECONDS;
    }
    tas_emote_probe_status(report,sizeof(report));
    assert(!strstr(report,"cache-marker-") && !strstr(report,"request-marker-"));
    /* Capacity pressure is per ID; another emote cannot consume its rows. */
    tas_emote_probe_record(number+1,1,"sample","other-provider",true);
    tas_emote_probe_status(report,sizeof(report));assert(!strstr(report,"other-provider"));
    for (unsigned i=0;i<PLAYBACK_EMOTES;i++) if (g_playback[i].number==number) {
        for (unsigned j=0;j<PLAYBACK_VISIBLE;j++) g_playback[i].visible[j].time-=PLAYBACK_SECONDS;
        for (unsigned j=0;j<PLAYBACK_ROWS;j++) {
            g_playback[i].samples_ring[j].time-=PLAYBACK_SECONDS;
            g_playback[i].events_ring[j].time-=PLAYBACK_SECONDS;
        }
    }
    tas_emote_probe_status(report,sizeof(report));assert(!strstr(report,"visible-before-cleanup"));
    tas_emote_probe_record(number,7,"sample","fresh-after-expiry",true);
    for (unsigned i=0;i<PLAYBACK_EMOTES;i++) if (g_playback[i].number==number) g_playback[i].touched-=PLAYBACK_SECONDS;
    tas_emote_probe_status(report,sizeof(report));assert(!strstr(report,"fresh-after-expiry"));
    for (unsigned i=0;i<PLAYBACK_EMOTES+5;i++) tas_emote_probe_record(number+10+i,1,"sample","bounded-pressure",true);
    unsigned occupied=0;for (unsigned i=0;i<PLAYBACK_EMOTES;i++) occupied+=g_playback[i].number!=0;
    assert(occupied==PLAYBACK_EMOTES);
    tas_emote_probe_observe("named-lookup","MissingEmote","123","catalog-hit");
    /* Recovery/eviction evidence does not keep metadata or a channel alive. */
    reset_room_locked(room,true,time(NULL));
    tas_emote_probe_stage(number,"image-request-missing");
    tas_emote_probe_status(report,sizeof(report));assert(strstr(report,"target-no-longer-in-catalog"));
    return 0;
}
'''


class EmoteProbeTests(unittest.TestCase):
    def test_targeted_trace_catalog_misses_native_overlap_privacy_and_bounds(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        source = (composer.ROOT / "src" / "TASEmotes.c").read_text()
        # Replace only the HTTP launch boundary; keep matching and IRC output real.
        source = replace_body(source, "static void ensure_loaded(const char *room_id, bool force)", "    (void)room_id; (void)force;\n")
        harness = HARNESS[:HARNESS.index("int main(void) {")] + MAIN
        harness += '\nvoid tas_image_probe_response(uint64_t number,id data) { (void)number;(void)data; }\n'
        harness = harness.replace('if(!strcmp(sel,"new"))', 'if(!strcmp(sel,"code"))result=(id)(intptr_t)o->number;\n    else if(!strcmp(sel,"new"))')
        harness = harness.replace('#include "TASEmotes.c"', '#include <objc/runtime.h>\nMethod *class_copyMethodList(Class,unsigned *);\nSEL method_getName(Method);\n' + source)
        composer.ComposerTests().compile_run(harness, [zig, "cc", "-fblocks", "-DTAS_EMOTE_DIAGNOSTIC=1", "-fsanitize=address,undefined"], runtime=True)


if __name__ == "__main__":
    unittest.main()
