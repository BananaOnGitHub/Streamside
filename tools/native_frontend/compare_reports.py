#!/usr/bin/env python3
"""Evaluate device reports; missing observations, relaunches and baselines fail closed."""
import argparse
import json
from pathlib import Path

PLAN=json.loads((Path(__file__).resolve().parents[2]/'native/twitch32.json').read_text())


def compare(baseline,native,previous=None):
    failures=[]
    observations=[('baseline',baseline,'baseline'),('native',native,'native')]
    if previous is None:failures.append('Previous native launch report missing; reopening unverified')
    else:observations.append(('native_previous',previous,'native'))
    for label,report,mode in observations:
        if report.get('schema')!=1 or report.get('mode')!=mode:failures.append(label+': wrong schema/mode')
        if report.get('donor_sha256')!=PLAN['donor_sha256']:failures.append(label+': wrong donor')
        if report.get('armed_mask')!=15 or report.get('failures')!=0:failures.append(label+': incomplete instrumentation or recorded failure')
        if report.get('hardware') in [None,'unavailable'] or not report.get('memory_available'):failures.append(label+': device/memory observation unavailable')
        probes=report.get('probes',{})
        if set(probes)!={p['name'] for p in PLAN['probes']} or any(type(v)!=int or v<0 for v in probes.values()):failures.append(label+': incomplete/invalid probe observations')
        if not baseline.get('proof_id') or report.get('proof_id')!=baseline.get('proof_id'):failures.append(label+': mismatched source/probe identity')
        if report.get('hardware')!=baseline.get('hardware') or report.get('os_kernel')!=baseline.get('os_kernel'):failures.append(label+': different device or OS')
        if mode=='native':
            for probe in PLAN['probes']:
                if probe['guard'] and probes.get(probe['name'])!=0:failures.append(label+': runtime attempt or unknown count: '+probe['name'])
            if report.get('account_list_state') not in [4,5]:failures.append(label+': authenticated account/list result not successful')
    for name in PLAN['required_baseline']:
        if not baseline.get('probes',{}).get(name,0)>0:failures.append('Baseline did not observe '+name)
    if not baseline.get('baseline_positive_control'):failures.append('Baseline positive control not complete')
    if previous is not None:
        if not 0<previous.get('launch_sequence',0)<native.get('launch_sequence',0):failures.append('Distinct native process launches not established')
        if previous.get('foregrounds',0)<2 or previous.get('backgrounds',0)<1 or native.get('foregrounds',0)<1:failures.append('Foreground/background/reopen sequence incomplete')
    return dict(status='evidence_incomplete_or_failed' if failures else 'reported_sequence_passed_pending_device_observation_review',
                failures=failures,
                limits=['Reports check consistency. Screen appearance, actual account/channel identity, signing/keychain continuity and untested donor paths still require the device checklist. Startup time begins at the diagnostic constructor, excluding dyld and earlier work.'],
                memory_difference_bytes=native.get('phys_footprint_bytes',0)-baseline.get('phys_footprint_bytes',0),
                constructor_to_active_difference_ms=native.get('first_active_ms',0)-baseline.get('first_active_ms',0))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('baseline',type=Path);p.add_argument('native',type=Path)
    p.add_argument('--previous-native',type=Path);args=p.parse_args()
    result=compare(json.loads(args.baseline.read_text()),json.loads(args.native.read_text()),
                   json.loads(args.previous_native.read_text()) if args.previous_native else None)
    print(json.dumps(result,indent=2));raise SystemExit(1 if result['failures'] else 0)


if __name__=='__main__':main()
