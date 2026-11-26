"""Exact-donor static ABI admission, including the Objective-C logout adapter."""
import copy
import json
import os
import re
from pathlib import Path
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/native_frontend')]
from build import donor
from validate import validate_abi


class AccountAdapterAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((ROOT/'native/twitch32.json').read_text())
        cls.images=donor(Path(os.environ.get('SSN_DONOR',ROOT.parent/f'donors/tv.twitch-{cls.plan["twitch_version"]}.ipa')),cls.plan)

    def test_exact_native_and_objc_boundaries_admitted(self):
        validate_abi(self.images,self.plan)

    def test_all_runtime_probe_images_assemble_in_both_modes(self):
        from probes import patch
        from macho import inject_load_dylib, loaded_dylibs
        dependency='@rpath/StreamsideNativeProof.framework/StreamsideNativeProof'
        for name in self.plan['layout']:
            _,data=self.images[name]
            for native in (False,True):
                with self.subTest(image=name,native=native):
                    instrumented=patch(data,self.plan,name,'a'*64,native)
                    result,added=inject_load_dylib(instrumented,dependency)
                    self.assertTrue(added)
                    self.assertEqual(loaded_dylibs(result).count(dependency),1)

    def test_relocated_runtime_contract_rejects_wrong_entry(self):
        plan=copy.deepcopy(self.plan)
        plan['runtime_contract']['main_calls'][0]['entry']='warmup'
        with self.assertRaisesRegex(ValueError,'Changed call relationship'):
            validate_abi(self.images,plan)

    def test_quality_selectors_reject_changed_signature_and_prefix(self):
        for name in ['playback_IVSPlayer_qualities', 'playback_IVSPlayer_setQuality:', 'playback_IVSPlayer_setQuality:adaptive:', 'playback_IVSQuality_name','playback_IVSQuality_width','playback_IVSQuality_height']:
            for key, value in [('encoding', 'v16@0:8'), ('bytes', '00' * 16)]:
                plan=copy.deepcopy(self.plan);plan['objc_services'][name][key]=value
                with self.assertRaises(ValueError):validate_abi(self.images,plan)

    def test_latency_selectors_are_admitted_with_exact_bool_and_cmtime_abi(self):
        for selector,encoding in [('setLiveLowLatencyEnabled:','v20@0:8B16'),
                                  ('setRebufferToLive:','v20@0:8B16'),
                                  ('isLiveLowLatency','B16@0:8'),
                                  ('liveLatency','{?=qiIq}16@0:8'),
                                  ('buffered','{?=qiIq}16@0:8')]:
            name='playback_IVSPlayer_'+selector
            self.assertEqual(self.plan['objc_services'][name]['encoding'],encoding)
            with self.subTest(selector=selector):
                plan=copy.deepcopy(self.plan);plan['objc_services'][name]['encoding']='v16@0:8'
                with self.assertRaises(ValueError):validate_abi(self.images,plan)

    def test_all_native_adapter_literal_dependencies_are_admitted(self):
        names=set()
        for filename in ['SSNProfileRequest.c','SSNContentLabels.c','SSNAccount.c','SSNFeed.c','SSNPlaybackRequest.c','SSNIntegration.c']:
            source=(ROOT/'native'/filename).read_text()
            names.update(re.findall(r'ssn_resolve\("([^"\n]+)"\)',source))
            names.update(re.findall(r'metadata\("([^"\n]+)"\)',source))
            # Feed also resolves public system types; only donor metadata uses
            # no system argument or the explicit false argument.
            names.update(re.findall(r'meta\("([^"\n]+)"(?:,false)?\)',source))
            if filename == 'SSNProfileRequest.c':
                names.update(name for name in re.findall(r'"(\$s[^"\n]+)"', source) if name.startswith(("$s16TwitchGraphQLAPI", "$s9ApolloAPI", "$s12TwitchApollo", "$s12Tomorrowland", "$s9TwitchKit")))
        for accessor in [
            '$s16TwitchGraphQLAPI22StreamAccessTokenQueryC4DataVMa',
            '$s16TwitchGraphQLAPI22StreamAccessTokenQueryC4DataV0d8PlaybackeF0VMa',
            '$s16TwitchGraphQLAPI22StreamAccessTokenQueryCMa',
            '$s16TwitchGraphQLAPI25PlaybackAccessTokenParamsVMa',
        ]:self.assertIn(accessor,names)
        self.assertEqual(sorted('_'+name for name in names if '_'+name not in self.plan['abi']),[])

    def test_player_mute_boundary_is_exact(self):
        spec=self.plan['objc_services']['playback_IVSPlayer_setMuted:']
        self.assertEqual(spec['encoding'],'v20@0:8B16')
        for key,value in [('encoding','v24@0:8q16'),('bytes','00'*16)]:
            plan=copy.deepcopy(self.plan);plan['objc_services']['playback_IVSPlayer_setMuted:'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_abi(self.images,plan)

    def test_wrong_objc_signature_or_address_or_prefix_rejected(self):
        for key,value in [('encoding','v24@0:8@16'),('address',0x103d078c4),('bytes','00'*16),('selector','loadInitialAccountData')]:
            plan=copy.deepcopy(self.plan);plan['objc_services']['logout'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_abi(self.images,plan)


if __name__=='__main__':unittest.main()
