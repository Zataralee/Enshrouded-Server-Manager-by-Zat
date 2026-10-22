"""Real EML package checks plus adversarial modeled execution of emitted bytecode.

Does not establish live multiplayer authority, native timing or replication.
"""
import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
from test_arrow_chain_program import Program, VM

ROOT=Path(__file__).resolve().parents[1]
ARROW='c0a8231a-f87f-467c-ad9d-6d4fe93ecda7_d4922d88_0'
SPELL='e28f0d79-e2fe-46ba-8d82-9ba368cb30c7_d4922d88_0'
SEQUENCE='12f3cda4-c44d-4a09-bc76-749e40f1c60f'
TEMPLATES=['9e8b9693-f81f-4dbd-82a2-f9a638d7fe6f','805d84da-8e66-4757-abee-03271ada0155',
           'ee33f908-7e96-449c-b1fe-8596a1e7fe28']

# Farthest targets deliberately enumerated before nearer ones. Distinct limbs
# each have three successors beyond the initial radius.
TREE={31:(-2,11,0),30:(2,11,0),29:(0,12,0),
      28:(-11,-2,0),27:(-11,2,0),26:(-12,0,0),
      25:(11,-2,0),24:(11,2,0),23:(12,0,0),
      13:(0,6,0),12:(-6,0,0),11:(6,0,0),10:(0,0,0),99:(1,0,0)}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir',required=True,type=Path)
    work=parser.parse_args().fixture_dir.resolve()
    assert (work/'SHOCK_MOD_TEST_FIXTURE').read_text().strip()=='disposable-shock-mod-test'
    spec=importlib.util.spec_from_file_location('eml',ROOT/'enshrouded_manager/eml_support.py')
    eml=importlib.util.module_from_spec(spec);spec.loader.exec_module(eml)
    mod=eml.EML(work/'Server',work/'state',ROOT/'enshrouded_manager/vendor/eml-v0.2.0/emm.exe')
    source=ROOT/'mods/zat-shock-tuning';mid='zat-shock-tuning'
    defaults=(source/'src/config.lua').read_text();version=json.loads((source/'mod.json').read_text())['version']
    original=eml.digest(work/'Server/enshrouded_server.kfc');results=[]
    def record(name): results.append(name);print('PASS',name,flush=True)
    def export(name):
        out=work/name;out.mkdir(exist_ok=True)
        with (out/'export.log').open('w') as log:
            subprocess.run([str(work/'parser/kfc-parser.exe'),'unpack','-g',str(work/'Server'),'-o',str(out),
                '-f',','.join([ARROW,SPELL,f'{SEQUENCE}_9fd4a561_0',*(g+'_39768775_0' for g in TEMPLATES)])],stdout=log,stderr=subprocess.STDOUT,check=True)
        programs=[]
        for guid,stem in [(ARROW,'arrow'),(SPELL,'spell')]:
            file=out/'ImpactProgram'/f'{guid}.json'
            with (out/f'{stem}-disassembly.log').open('w') as log:
                subprocess.run([str(work/'parser/kfc-parser.exe'),'impact','disassemble','-i',str(file),
                    '-o',str(out/stem)],stdout=log,stderr=subprocess.STDOUT,check=True)
            p=Program(json.loads(file.read_text()),(out/f'{stem}.impact').read_text())
            p.validate_structure((out/f'{stem}.shutdown.impact').read_text());programs.append(p)
        seq=json.loads(next((out/'ActorSequenceResource').glob(SEQUENCE+'*')).read_text())
        return *programs,seq
    def apply(config): mod.config_file(mid,'src/config.lua',config);mod.apply()
    try:
        mod.enable(True)
        if mid in mod.state()['mods']: mod.change_mod(mid,'remove')
        mod.import_zip((ROOT/f'dist/mods/Zat-Shock-Tuning-v{version}.zip').read_bytes());mod.change_mod(mid,'enable')
        apply(defaults);a0,s0,seq0=export('fanout-baseline')
        config=defaults.replace('enabled = false','enabled = true').replace('targets_per_spread = 1','targets_per_spread = 3')
        apply(config);a,s,seq=export('fanout-enabled')
        for old,new,offsets in [(a0,a,[0,1,89,211]),(s0,s,[94,276])]:
            code=new.code[:len(old.code)]
            for offset in offsets: code[offset]=old.code[offset]
            assert code==old.code
            assert new.p['data'][:len(old.p['data'])]==old.p['data']
            assert new.layout[:len(old.layout)]==old.layout
        events=[e['$value'] for sub in seq['subSequences'] for e in sub['events'] if e['$type']=='keen::actor::SpawnImpact']
        flag=s.layout[s.names['ZatSpellChain::enabled']]
        gate=[v['$value'] for e in events for v in e['impactValues']['simple'] if v['$value']['configId']==flag['configId']]
        assert len(gate)==1 and gate[0]['value'] is True
        assert s.p['data'][flag['offsetInBytes']]==0
        # Revert only the new opt-in config, then compare the entire sequence.
        for e in events: e['impactValues']['simple']=[v for v in e['impactValues']['simple'] if v['$value']['configId']!=flag['configId']]
        assert seq==seq0
        assert s.spell_scenario(enabled=False).hits==[]
        record('both existing programs preserve original bodies; player sequence gates spell changes, other casts bypass')
        for guid in TEMPLATES:
            baseline=json.loads(next((work/'fanout-baseline/TemplateResource').glob(guid+'*')).read_text())
            patched=json.loads(next((work/'fanout-enabled/TemplateResource').glob(guid+'*')).read_text())
            baseline['components']=[c for c in baseline['components'] if c['$type']!='keen::ecs::LifeTime']
            flag=a.layout[a.names['ZatArrowChain::managed_flight']]['configId']
            config_values=next(c['$value']['configValues'] for c in patched['components']
                              if c['$type']=='keen::ecs::ImpactConfiguration')
            selected=[c for c in config_values['simple'] if c['$value']['configId']==flag]
            assert len(selected)==1 and selected[0]['$value']['value'] is True
            config_values['simple']=[c for c in config_values['simple'] if c['$value']['configId']!=flag]
            assert patched==baseline
        record('enabled templates change only server LifeTime removal and the private flight-watchdog opt-in')
        for ammo in (3133483038,2453015274,2369196415):
            v=VM(a,ammo,{10:0},True,0);v.now=0xfffffff0
            v.run(0,{2});v.stack.pop()
            v.now+=4999;v.run(0,{2});v.stack.pop();assert not v.destroyed
            v.now+=1;v.run(0,{2});assert v.destroyed and not v.stack
        v=VM(a,123,{10:0},True,0);v.now=100000;v.run(0,{2});v.stack.pop()
        assert not v.destroyed
        v=VM(a,0,{10:0},True,0);v.set('ZatArrowChain::managed_flight',1)
        v.run(0,{2});v.stack.pop();v.now=5000;v.run(0,{2})
        assert v.destroyed
        record('flight watchdog expires marked projectiles at five seconds even without ammo metadata; unrelated templates bypass')
        for name,p,run,prefix in [('arrow',a,a.scenario,'eternal_20'),('spell',s,s.spell_scenario,'spell')]:
            v=run(positions=TREE)
            assert [t for _,t in v.hit_waves if _==1]==[11,12,13],v.hit_waves
            assert len([t for wave,t in v.hit_waves if wave==2])==9,v.hit_waves
            assert len(v.hits)==12 and len({t for t,_ in v.hits})==12
            assert v.visuals[:3]==[(0.,11),(0.,12),(0.,13)]
            # Children at (11,+/-2) precede the farther child at (12,0).
            assert [t for _,t in v.visuals[3:6]]==[24,25,23],v.visuals
            record(name+': three nearest children then nine grandchildren, using each spreader position')
            v=run(positions={10:0,40:6,41:1,42:3},overrides={prefix+'_fanout':1})
            assert [t for t,_ in v.hits]==[41,42,40],v.hits
            record(name+': linear mode ignores far-first enumeration and always chooses nearest')
            v=run(positions={10:(0,0,0),40:(0,0,6),41:(0,0,1),42:(0,0,3)},overrides={prefix+'_fanout':1})
            assert [t for t,_ in v.hits]==[41,42,40]
            record(name+': distance ordering includes elevation')
            v=run(positions={10:(0,0,0),11:(6,0,0),12:(0,6,0),13:(6,6,0)},overrides={prefix+'_fanout':2})
            assert [t for t,_ in v.hits]==[11,12,13]
            record(name+': converging branches reserve a common victim once before history updates')
            v=run(positions={10:0,4294967294:2,268435457:2},overrides={prefix+'_fanout':1})
            assert [t for t,_ in v.hits]==[268435457,4294967294]
            record(name+': high-bit entity IDs survive queue copies and deterministic equal-distance ordering')
            v=run(positions=TREE,kill_initial=True)
            assert len(v.hits)==12
            record(name+': killing the initial victim retains its propagation origin')
            v=run(positions=TREE,history=False)
            assert len(v.hits)==3
            record(name+': missing native history stops after the submitted generation without revisits')
            v=run(positions=TREE,overrides={prefix+'_fanout':0})
            assert v.hits==[]
            record(name+': zero fan-out sends no secondary hits')
            v=run(positions={10000+i:i for i in range(1,1101)}|{10:0},overrides={prefix+'_radius':1.1,prefix+'_fanout':1})
            assert len(v.hits)==1100
            record(name+': zero limit traverses 1100 targets with circular frontier slot reuse')
            assert v.hit_times[-1][0]>5000
            v=run(positions={10:0,11:1,12:2,13:3,14:4,15:5},dead_targets={11},
                  health={12:0,13:-1,14:None},overrides={prefix+'_fanout':1})
            assert [t for t,_ in v.hits]==[15]
            record(name+': existing corpses, zero/negative HP and non-health entities are excluded')
            assert run(dead_targets={10}).hits==[]
            assert run(health={10:0}).hits==[]
            record(name+': an initially dead victim cannot start a new chain')
            v=run(positions={10:0,11:6,12:1,13:3},factions={11:2,12:12,13:11},
                  reorder_queries=True,overrides={prefix+'_fanout':1})
            assert [t for t,_ in v.hits]==[12,13,11]
            record(name+': nearest hostile wins across factions and reordered query enumeration')
            v=run(positions={10:0,11:6,12:-6,13:-12},missing_history={11},
                  overrides={prefix+'_fanout':2})
            assert [t for t,_ in v.hits]==[11,12,13]
            record(name+': one unconfirmed branch does not cancel confirmed siblings')
            v=run(positions={10:0,11:6,12:12,13:18},tick_ms=50,history_delay=3,
                  overrides={prefix+'_fanout':1})
            assert v.hit_times==[(250,11),(500,12),(750,13)],v.hit_times
            record(name+': 250 ms cadence allows history delayed across three updates')
            v=run(positions={10:0,11:6,12:12,13:18},now=0xfffffff0,tick_ms=50,
                  overrides={prefix+'_fanout':1})
            assert [t-0xfffffff0 for t,_ in v.hit_times]==[250,500,750]
            record(name+': millisecond timer handles uint32 clock rollover')
            v=run(positions={10:0,11:6,12:12,13:18},tick_ms=50,
                  overrides={prefix+'_fanout':1,prefix+'_delay':0})
            assert [t for t,_ in v.hit_times]==[50,100,150]
            record(name+': zero delay yields one update per generation')
            v=run(positions={10:0,11:6,12:12,13:18},moves={2:{11:(17.,0.,0.)}},
                  overrides={prefix+'_fanout':1})
            assert [t for t,_ in v.hits]==[11,13,12],v.hits
            assert v.visuals[1]==(17.,13)
            record(name+': moving spreader uses its current position after the delay')
        v=a.scenario(positions={10:0,11:1,12:2,13:3},block_targets={11},reject_targets={12})
        assert [t for t,_ in v.hits]==[11,13]
        record('blocked/rejected closest candidates do not loop or suppress farther eligible targets')
        v=a.scenario(positions={10:0,11:6,12:12,13:18},kill_targets={11})
        assert len(v.hits)==3
        record('a killing secondary hit spreads from its saved transform after the entity disappears')
        v=a.scenario(positions=TREE,overrides={'eternal_20_fanout':1})
        assert len([t for wave,t in v.hit_waves if wave==1])==1
        assert len([t for wave,t in a.scenario(ammo=2453015274,positions=TREE).hit_waves if wave==1])==3
        assert len([t for wave,t in a.scenario(ammo=2369196415,positions=TREE).hit_waves if wave==1])==3
        record('each arrow tier consumes its own independent fan-out setting')
        mixed=config.replace('eternal_20 = { enabled = true','eternal_20 = { enabled = false')
        mixed=mixed.replace('eternal_36 = { enabled = true','eternal_36 = { enabled = false')
        apply(mixed);export('fanout-one-tier')
        for guid in TEMPLATES[:2]:
            assert json.loads(next((work/'fanout-one-tier/TemplateResource').glob(guid+'*')).read_text())==json.loads(
                next((work/'fanout-baseline/TemplateResource').glob(guid+'*')).read_text())
        record('disabling individual tiers preserves their original projectile lifetime and every template field')
        apply(config.replace('max_jumps = 0','max_jumps = 5'));limited_a,limited_s,_=export('fanout-limited')
        for run in (limited_a.scenario,limited_s.spell_scenario):
            v=run(positions=TREE,tick_ms=50,history_delay=3)
            assert len(v.hits)==5 and not v.pending_hits
            assert {t for t,_ in v.hits}.issubset(v.visited)
        record('finite total-secondary budget is shared across all branches for arrows and spells')
        apply(config.replace('max_jumps = 0','max_jumps = 4294967295'));wide_a,wide_s,_=export('fanout-uint32')
        assert len(wide_a.scenario(positions=TREE).hits)==12
        assert len(wide_s.spell_scenario(positions=TREE).hits)==12
        record('full uint32 jump limits do not terminate at the signed integer boundary')
        for bad in ('-1','1.5','4294967296','math.huge'):
            mod.restore()
            try: apply(config.replace('targets_per_spread = 3','targets_per_spread = '+bad))
            except RuntimeError: pass
            else: raise AssertionError('accepted invalid fan-out '+bad)
            assert eml.digest(work/'Server/enshrouded_server.kfc')==original
        record('negative, fractional, overflowing and nonfinite fan-out are refused without a patch')
        for bad in ('-1','1.5','4294967296','math.huge'):
            mod.restore()
            try: apply(config.replace('spread_delay_ms = 250','spread_delay_ms = '+bad))
            except RuntimeError: pass
            else: raise AssertionError('accepted invalid delay '+bad)
            assert eml.digest(work/'Server/enshrouded_server.kfc')==original
        record('delay rejects negative, fractional, nonfinite and uint32 overflow values without a patch')
        apply(config.replace('spread_delay_ms = 250','spread_delay_ms = 4294967295'))
        delay_a,delay_s,_=export('fanout-long-delay')
        for p,run,prefix in [(delay_a,delay_a.scenario,'eternal_20'),(delay_s,delay_s.spell_scenario,'spell')]:
            v=run(positions={10:0,11:1},tick_ms=2147483647,overrides={prefix+'_fanout':1})
            assert v.hit_times[0][0]==6442450941
        record('full uint32 millisecond delay is accepted and counts down across timer rollover')
        # Representability only: fan-out greater than the native frontier is
        # accepted. The queue guards its actual capacity rather than overflowing.
        apply(config.replace('targets_per_spread = 3','targets_per_spread = 4294967295'))
        huge_a,huge_s,_=export('fanout-large')
        assert len(huge_a.scenario(positions={10:0,11:1,12:2}).hits)==2
        assert len(huge_s.spell_scenario(positions={10:0,11:1,12:2}).hits)==2
        record('no balance cap on fan-out: full uint32 accepted and consumed')
        for p,run in [(a,a.scenario),(s,s.spell_scenario)]:
            v=run(positions=TREE,overrides={'capacity':2})
            assert len(v.hits)==2
        record('frontier exhaustion terminates before any native buffer overwrite')
    finally:
        mod.config_file(mid,'src/config.lua',defaults);mod.restore()
        assert eml.digest(work/'Server/enshrouded_server.kfc')==original
    record('fixture defaults and exact original game index restored')
    (work/'fanout-results.json').write_text(json.dumps(results,indent=2))

if __name__=='__main__': main()
