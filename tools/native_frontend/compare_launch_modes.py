#!/usr/bin/env python3
"""Compare original-startup observations. Missing evidence fails, never becomes zero."""
import argparse
import hashlib
import json
from pathlib import Path
PLAN=json.loads((Path(__file__).resolve().parents[2]/'native/twitch32.json').read_text())
CONTRACT=hashlib.sha256(json.dumps({k:PLAN[k] for k in ['probes','layout','gate','required_baseline']},sort_keys=True,separators=(',',':')).encode()).hexdigest()

def compare(control,one_shot):
    failures=[]
    for label,report,origin,packaged in [('independent',control,0,False),('one_shot',one_shot,2,True)]:
        def require(condition,message):
            if not condition:failures.append(label+': '+message)
        require(report.get('schema')==1 and report.get('mode')=='baseline','wrong schema or mode')
        require(report.get('launch_origin')==origin and report.get('packaged_native') is packaged,'wrong launch origin')
        require(report.get('development_launch_selector') is packaged,'wrong selector configuration')
        require(report.get('launch_selection_error')==0 and report.get('original_launch_pending') is False,'selection/deletion not confirmed')
        require(report.get('probe_contract')==CONTRACT,'missing or different instrumentation contract')
        require(report.get('donor_sha256')==PLAN['donor_sha256'],'wrong donor')
        require(report.get('armed_mask')==15 and report.get('failures')==0,'incomplete probes or recorded failure')
        probes=report.get('probes',{})
        require(set(probes)=={p['name'] for p in PLAN['probes']} and all(type(v)==int and v>=0 for v in probes.values()),'incomplete probe counts')
        require(report.get('baseline_positive_control') is True,'runtime positive control incomplete')
        for name in PLAN['required_baseline']:require(type(probes.get(name))==int and probes[name]>0,'no positive observation: '+name)
        require(report.get('native_frontend_events')==[0]*4,'native frontend hooks/services not proven absent')
        require(report.get('ui_root_owner')==2 and report.get('navigation_guard_armed')==0,'original navigation ownership not established')
        require(report.get('navigation_events')==[0]*5,'native navigation activity or missing observation')
        require(report.get('account_events')==[0]*5 and report.get('returned_channel_count')==0,'native account activity or missing observation')
        require(report.get('playback_events')==[0]*9,'native playback activity or missing observation')
        require(bool(report.get('source_revision')) and bool(report.get('proof_id')),'missing source identity')
        require(report.get('hardware') not in [None,'unavailable'] and bool(report.get('os_kernel')),'device identity unavailable')
    for key in ['hardware','os_kernel','donor_sha256','probe_contract']:
        if control.get(key)!=one_shot.get(key):failures.append('Mismatched '+key)
    return dict(status='incomplete_or_failed' if failures else 'original_startup_reports_consistent_pending_device_routing_review',failures=failures,
        limits=['Observe actual original routing on device. Positive counts need not be identical across workloads.',
                'The native package retains its modern UIKit styling preference and selector shim. This is not binary, pixel, memory, or timing identity.',
                'A report from an older control without hook evidence or probe contract cannot establish their absence.'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('independent',type=Path);p.add_argument('one_shot',type=Path);a=p.parse_args()
    result=compare(json.loads(a.independent.read_text()),json.loads(a.one_shot.read_text()))
    print(json.dumps(result,indent=2));raise SystemExit(bool(result['failures']))
if __name__=='__main__':main()
