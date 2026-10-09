"""Build the snapshot runner in an existing, pinned public Hermes source checkout.
Does not download dependencies or modify the app repository's build toolchain.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent.parent
COMMIT='40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c'
def build(a):
    source=a.source.resolve();folder=a.build.resolve()
    assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==COMMIT,'Wrong Hermes source revision'
    changed=subprocess.check_output(['git','-C',str(source),'diff','--name-only','HEAD'],text=True).splitlines()
    assert all(x=='tools/jsi/CMakeLists.txt' for x in changed),'Hermes implementation differs from pinned revision'
    path=source/'tools/jsi/CMakeLists.txt'
    base=subprocess.check_output(['git','-C',str(source),'show','HEAD:tools/jsi/CMakeLists.txt'],text=True)
    runner=ROOT/'tests/native/hermes_snapshot_runner.cpp'
    path.write_text(base+'\nadd_hermes_tool(streamside-snapshot-runner\n "'+str(runner)+'"\n LINK_OBJLIBS hermesvm_a timerStats)\ntarget_link_libraries(streamside-snapshot-runner ${CMAKE_DL_LIBS})\n')
    subprocess.run([str(a.cmake),'-S',str(source),'-B',str(folder),'-G','Ninja',
        '-DCMAKE_MAKE_PROGRAM='+str(a.ninja.resolve()),'-DCMAKE_BUILD_TYPE=Release',
        '-DHERMES_ENABLE_TEST_SUITE=OFF','-DHERMES_UNICODE_LITE=ON','-DHERMES_ENABLE_INTL=OFF',
        '-DHERMES_ENABLE_UNICODE_REGEXP_PROPERTY_ESCAPES=OFF','-DHERMES_ALLOW_BOOST_CONTEXT=0','-DHERMES_ENABLE_WERROR=OFF'],check=True)
    subprocess.run([str(a.cmake),'--build',str(folder),'--target','streamside-snapshot-runner','-j',str(a.jobs)],check=True)
    binary=folder/'bin/streamside-snapshot-runner'
    binary.with_suffix('.build.json').write_text(json.dumps({'runtime_commit':COMMIT,
        'runner_source_sha256':hashlib.sha256(runner.read_bytes()).hexdigest(),
        'runner_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
        'unicode':'lite','intl':False},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--cmake',type=Path,required=True);p.add_argument('--ninja',type=Path,required=True);p.add_argument('--jobs',type=int,default=4);build(p.parse_args())
