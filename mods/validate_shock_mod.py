import hashlib, importlib.util, json, subprocess, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import argparse
parser=argparse.ArgumentParser(description="Validate the mod against a disposable extracted server fixture.")
parser.add_argument("--fixture-dir", type=Path, required=True)
args=parser.parse_args()
work=args.fixture_dir.resolve()
assert (work/'SHOCK_MOD_TEST_FIXTURE').read_text().strip()=='disposable-shock-mod-test', 'Refusing a non-test server fixture'

server=work/'Server'
spec=importlib.util.spec_from_file_location('eml',ROOT/'enshrouded_manager/eml_support.py')
eml=importlib.util.module_from_spec(spec);spec.loader.exec_module(eml)
mod=eml.EML(server,work/'state',ROOT/'enshrouded_manager/vendor/eml-v0.2.0/emm.exe')
package=ROOT/'dist/mods/Zat-Shock-Tuning-v0.1.0.zip'
mid='zat-shock-tuning'
original=eml.digest(server/'enshrouded_server.kfc')
defaults=(ROOT/'mods/zat-shock-tuning/src/config.lua').read_text()
results=[]

def last_run_log():
    return mod.log().rsplit('ESM-Z: emm run', 1)[-1]
def record(test,**fields):
    results.append(dict(test=test,passed=True,**fields))
    (work/'results.json').write_text(json.dumps(results,indent=2))
    print('PASS',test,fields,flush=True)
try:
    mod.enable(True)
    if mid in mod.state()['mods']:mod.change_mod(mid,'remove')
    mod.import_zip(package.read_bytes());mod.change_mod(mid,'enable')
    assert 'src/config.lua' in mod.config_file(mid)['files']
    mod.apply()
    assert 'Applied 0 setting changes' in last_run_log(),last_run_log()
    # A vanilla preset should not cause any modified resource writes.
    assert 'Applied 0 patches' in last_run_log()
    record('ESM import and vanilla config no resource patches',index_sha256=original)
    tuned=defaults.replace('spread_radius = 7.0','spread_radius = 10.0').replace('targeting_range = 24.0','targeting_range = 30.0')
    tuned=tuned.replace('damage = 1.12, mana = 70','damage = 1.68, mana = 50').replace('eternal_20_damage = 0.5','eternal_20_damage = 0.75')
    tuned=tuned.replace('radius = 15,','radius = 20,').replace('damage_per_intelligence = 2','damage_per_intelligence = 3')
    mod.config_file(mid,'src/config.lua',tuned);mod.apply()
    assert 'Applied 13 setting changes' in last_run_log(),last_run_log()
    patched=eml.digest(server/'enshrouded_server.kfc');assert patched!=original
    record('Changed configuration applies',index_sha256=patched)
    targets=[]
    for kind,guids in {
        'ItemInfo':['3cb0ef06','4c425eba','4d0bab0f','d033d5d2','fcf60ecf','bf55416d','5c93fd11','a3ef08e9'],
        'ActorSequenceResource':['12f3cda4'], 'SkillTreeResource':['108ac23f'],
        'TemplateResource':['674340cf'], 'ImpactProgram':['56188199']}.items():
        for guid in guids:targets.append(next((work/'baseline'/kind).glob(guid+'*')).stem)
    export=work/'patched'
    with (work/'patched-export.log').open('w') as log:
        subprocess.run([str(work/'parser/kfc-parser.exe'),'unpack','-g',str(server),'-o',str(export),'-f',','.join(targets)],stdout=log,stderr=subprocess.STDOUT,check=True)
    def read(kind,prefix):return json.loads(next((export/kind).glob(prefix+'*')).read_text())
    item=read('ItemInfo','3cb0ef06')
    assert abs(item['damageSetup']['dmgMod']-1.68)<1e-5
    assert item['itemTargetingSetup']['targetingRange']==30
    mana=[x['$value']['value'] for x in item['impactValues']['simple'] if x['$value']['configId']['value']==2938334926]
    assert mana==[50]
    assert read('ItemInfo','bf55416d')['damageSetup']['dmgMod']==0.75
    sequence=read('ActorSequenceResource','12f3cda4')
    cast=[e['$value'] for s in sequence['subSequences'] for e in s['events'] if e['$type']=='keen::actor::SpawnImpact' and e['$value']['impact']=='e28f0d79-e2fe-46ba-8d82-9ba368cb30c7'][0]
    assert cast['colliderData']['dataArray'][0]['$value']['shape']['radius']==10
    program=read('ImpactProgram','56188199')
    for cid,value,encoding in [(1815063917,20,'<f'),(4130293191,3,'<I')]:
        layout=[x for x in program['dataLayout'] if x['configId']['value']==cid][0]
        start=layout['offsetInBytes'];assert struct.unpack(encoding,bytes(program['data'][start:start+4]))[0]==value
    record('Decoded packaged values match requested settings')
    # Check all exported JSON changes against an explicit whitelist below.
    def diffs(a,b,path=''):
        if isinstance(a,dict) and isinstance(b,dict):
            assert a.keys()==b.keys(),path
            return [x for k in a for x in diffs(a[k],b[k],path+'.'+k)]
        if isinstance(a,list) and isinstance(b,list):
            assert len(a)==len(b),path
            return [x for i,(v,w) in enumerate(zip(a,b)) for x in diffs(v,w,path+f'[{i}]')]
        return [] if a==b else [(path,a,b)]
    changed={}
    for file in export.rglob('*.json'):
        baseline=work/'baseline'/file.relative_to(export)
        difference=diffs(json.loads(baseline.read_text()),json.loads(file.read_text()))
        changed[file.relative_to(export).as_posix()]=difference
    (work/'exact-resource-diff.json').write_text(json.dumps(changed,indent=2))
    allowed = {
        '12f3cda4': ['.subSequences[0].events[16].$value.colliderData.dataArray[0].$value.shape.radius'],
        '56188199': ['.data[50]', '.data[240]'],
        '3cb0ef06': ['.impactValues.simple[0].$value.value', '.itemTargetingSetup.targetingRange', '.damageSetup.dmgMod'],
        '4c425eba': ['.itemTargetingSetup.targetingRange'],
        '4d0bab0f': ['.itemTargetingSetup.targetingRange'],
        'd033d5d2': ['.itemTargetingSetup.targetingRange'],
        'fcf60ecf': ['.itemTargetingSetup.targetingRange'],
        '5c93fd11': [], 'a3ef08e9': [],
        'bf55416d': ['.damageSetup.dmgMod'],
        '108ac23f': ['.nodes[32].configValues.simple[0].$value.value'],
        '674340cf': ['.components[2].$value.colliders[0].dataArray[0].$value.shape.radius'],
    }
    assert len(changed)==len(allowed)
    for name, difference in changed.items():
        assert [entry[0] for entry in difference]==allowed[Path(name).name[:8]],name
    record('Only expected fields changed across all 12 exported resources')
    mod.restore();assert eml.digest(server/'enshrouded_server.kfc')==original
    record('Restore matches original index byte for byte')
    for name,invalid in [('out of bounds',defaults.replace('spread_radius = 7.0','spread_radius = -1')),
                         ('unknown option',defaults.replace('schema_version = 1','unknown_option = 1, schema_version = 1')),
                         ('nonfinite number',defaults.replace('spread_radius = 7.0','spread_radius = 0/0')),
                         ('syntax error',defaults+'!')]:
        mod.config_file(mid,'src/config.lua',invalid)
        try:mod.apply()
        except RuntimeError:pass
        else:raise AssertionError('Invalid config accepted: '+name)
        assert eml.digest(server/'enshrouded_server.kfc')==original
        record('Reject '+name+' and retain baseline')
    mod.config_file(mid,'src/config.lua',tuned);mod.apply()
    record('Valid config recovers after invalid config')
    mod.apply()
    # EML's archive serialization is not byte-deterministic. Compare resource
    # content instead of treating different index bytes as changed semantics.
    repeated=work/'repeated'
    with (work/'repeated-export.log').open('w') as log:
        subprocess.run([str(work/'parser/kfc-parser.exe'),'unpack','-g',str(server),'-o',str(repeated),'-f',','.join(targets)],stdout=log,stderr=subprocess.STDOUT,check=True)
    for file in export.rglob('*.json'):
        assert json.loads(file.read_text())==json.loads((repeated/file.relative_to(export)).read_text()),file.name
    record('Repeated apply does not compound changes')
    mod.config_file(mid,'src/config.lua',defaults);mod.apply()
    assert 'Applied 0 patches' in last_run_log()
    record('Reset to default config removes all resource patches')
except Exception:
    print(mod.log()[-12000:],flush=True)
    raise
finally:
    mod.restore()
