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
        cls.images=donor(Path(os.environ.get('SSN_DONOR',ROOT.parent/'donors/tv.twitch-32.0.ipa')),cls.plan)

    def test_exact_native_and_objc_boundaries_admitted(self):
        validate_abi(self.images,self.plan)

    def test_all_native_adapter_literal_dependencies_are_admitted(self):
        names=set()
        for filename in ['SSNAccount.c','SSNFeed.c','SSNPlaybackRequest.c','SSNIntegration.c']:
            source=(ROOT/'native'/filename).read_text()
            names.update(re.findall(r'ssn_resolve\("([^"\n]+)"\)',source))
            names.update(re.findall(r'metadata\("([^"\n]+)"\)',source))
            # Feed also resolves public system types; only donor metadata uses
            # no system argument or the explicit false argument.
            names.update(re.findall(r'meta\("([^"\n]+)"(?:,false)?\)',source))
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
