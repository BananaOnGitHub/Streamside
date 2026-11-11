"""Exact-donor static ABI admission, including the Objective-C logout adapter."""
import copy
import json
import os
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

    def test_wrong_objc_signature_or_address_or_prefix_rejected(self):
        for key,value in [('encoding','v24@0:8@16'),('address',0x103d078c4),('bytes','00'*16),('selector','loadInitialAccountData')]:
            plan=copy.deepcopy(self.plan);plan['objc_services']['logout'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_abi(self.images,plan)


if __name__=='__main__':unittest.main()
