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
    char report[24576],tiny[9];
    assert(!tas_emote_probe_set(NULL) && !tas_emote_probe_set(""));
    assert(!tas_emote_probe_set("two words") && !tas_emote_probe_set("line\nbreak"));
    char oversized[98];memset(oversized,'x',97);oversized[97]=0;
    assert(!tas_emote_probe_set(oversized));
    tas_emote_probe_status(report,sizeof(report));assert(strstr(report,"Select Inspect Emote"));
    assert(tas_emote_probe_set("MissingEmote"));
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
        harness = harness.replace('if(!strcmp(sel,"new"))', 'if(!strcmp(sel,"code"))result=(id)(intptr_t)o->number;\n    else if(!strcmp(sel,"new"))')
        harness = harness.replace('#include "TASEmotes.c"', '#include <objc/runtime.h>\nMethod *class_copyMethodList(Class,unsigned *);\nSEL method_getName(Method);\n' + source)
        composer.ComposerTests().compile_run(harness, [zig, "cc", "-fblocks", "-DTAS_EMOTE_DIAGNOSTIC=1", "-fsanitize=address,undefined"], runtime=True)


if __name__ == "__main__":
    unittest.main()
