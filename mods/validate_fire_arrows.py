"""Package/restore checks and emitted-bytecode models, NOT native combat proof."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import struct
import subprocess
import zipfile
from test_arrow_chain_program import Program, VM

ROOT = Path(__file__).resolve().parents[1]
GUID = 'c0a8231a-f87f-467c-ad9d-6d4fe93ecda7'
TIERS = {15: 685713190, 28: 225262139, 45: 678529367}
ZONE='47746ed5-c7ab-4835-850b-0dc02b1665b7'
ZONE_TEMPLATE='44cb7678-8c69-435a-802e-69adb11375a9'
TEMPLATES = ['f1174ce0-7b9f-40c8-a208-2018a58e532c', '12056e78-fbb4-4929-9765-be94c69b91b9',
             'd6dca074-b8df-454b-a973-608740cf86c4']


class FireVM(VM):
    def __init__(self, program, tier=45, positions=None, **options):
        super().__init__(program, TIERS[tier], positions or {10: 0}, True, 0)
        self.set('ZatArrowChain::managed_flight', 1)
        self.set('Damage.Magical_Fire::value', 50)
        self.set('mul2::result', 1.5)
        self.ignitions, self.burn_ticks, self.visual_leases = [], [], []
        self.ground_visuals, self.ground_destroyed = [], []
        self.soaked, self.soak_at = set(), {}
        self.death_at, self.logout_at = {}, math.inf
        self.tick_ms = 100
        for key, value in options.items(): setattr(self, key, value)

    def native(self, call_id, function):
        name, params = self.program.functions[function]
        handled = {'HasBuffNode', 'HasEntityTag', 'ApplyBuff', 'MulValues', 'ApplyDamage', 'IsValidEntity', 'IsInState', 'GetSelf', 'SpawnEntity', 'DestroyEntity', 'ForEachCollisionInStream', 'RandomValueNode', 'AddValues'}
        if name not in handled: return super().native(call_id, function)
        args, refs = {}, {}
        for role in ('out', 'cfg', 'in'):
            for kind, key, typ in params:
                if kind == role:
                    ptr = self.stack.pop(); refs[key] = ptr; args[key] = self.read(ptr)
        result = True
        if name == 'ForEachCollisionInStream':
            assert refs['transform'] and not refs['otherRootEntity']
            self.write(refs['transform'], self.impact_point)
            self.write(refs['position'], self.impact_point)
            self.write(refs['otherEntity'], 0)
            self.write(refs['isCombatTarget'], 0)
        elif name == 'RandomValueNode': self.write(refs['value'], 0)
        elif name == 'AddValues': self.write(refs['result'], args['valueA']+args['valueB'])
        elif name == 'GetSelf': self.write(refs['entityId'], 2)
        elif name == 'SpawnEntity':
            import uuid
            assert args['templateInput'] == uuid.UUID('44cb7678-8c69-435a-802e-69adb11375a9').bytes_le
            assert args['parentEntityId']==2 and args['addDespawnLink']==1
            assert args['breakImpactHierarchy']==0 and args['targetEntityId'] is None
            entry=self.program.layout[refs['transform'] & 0xffff]
            rotation_scale=struct.unpack_from('<7f',self.mem,entry['offsetInBytes']+24)
            assert rotation_scale[:4]==(0,0,0,1) and rotation_scale[5]==1
            assert rotation_scale[4]==rotation_scale[6]
            self.ground_visuals.append((self.now,args['transform']))
            self.write(refs['entityId'],1000)
        elif name == 'DestroyEntity':
            assert args['entityId']==1000
            self.ground_destroyed.append(self.now)
        elif name == 'IsValidEntity':
            e = args['entityId']; result = self.now < self.logout_at if e == 1 else e in self.positions
        elif name == 'IsInState':
            e = args['entityId']; result = e in self.dead_targets or self.now >= self.death_at.get(e, math.inf)
        elif name == 'HasBuffNode':
            e = args['targetEntityId']; result = e in self.soaked or self.now >= self.soak_at.get(e, math.inf)
        elif name == 'HasEntityTag':
            # All modeled enemies have the small-size visual tag.
            ptr = refs['entityTag']; result = 'fire_tag_Small' in self.program.layout[ptr & 0xffff]['dbgName']
        elif name == 'ApplyBuff':
            assert args['damageSetup'] is None and args['usedItem'] is None
            event=(self.now, args['targetEntityId'], args['durationInput'])
            self.visual_leases.append(event)
            assert args['durationInput']==500000000
            if not any(e==args['targetEntityId'] for _,e,_ in self.ignitions): self.ignitions.append(event)
        elif name == 'MulValues':
            assert args['op'] == 2
            self.write(refs['result'], args['valueA'] * args['valueB'])
        elif name == 'ApplyDamage':
            assert args['sourceId'] == 1
            # Native tooltip: true ignores entities that were ALREADY hit.
            # Model the filter rather than assuming every submitted tick lands.
            if args['ignoreConsecutiveHits'] and args['targetId'] in self.visited:
                self.stack.append(0)
                return
            if 'ZatArrowChain::fire_neutral_material' in self.program.names: assert args['materialId'] == 0
            assert args['canCrit'] == 0 and args['canBeBlocked'] == 0
            for key in ('manaCost', 'specialAbilityGain', 'attackStaminaMod', 'noiseRange'):
                assert args[key] is None
            assert args['pushBack'] == 0 and args['hitReaction'] == 0
            damage = struct.unpack('<9f4i', args['damageSetup'])
            assert all(value == 0 for i, value in enumerate(damage) if i != 3)
            for key, entry in [('weaponCategory', 'WeaponCategory::value'),
                               ('attackCategory', 'AttackCategory::value'),
                               ('damageScaleAttribute', 'DamageScaleAttribute::value')]:
                assert refs[key] == 0xffff0000 + self.program.names[entry]
            assert args['attackMod'] == 1.5
            assert self.now > 0  # No instant ignition blast.
            self.burn_ticks.append((self.now, args['targetId'], damage[3]*args['attackMod']))
            self.visited.add(args['targetId'])
        self.stack.append(int(result))

    def execute(self, overrides=None, kill_initial=False, blocked=False, ground_hit=False):
        for key, value in (overrides or {}).items(): self.set('ZatArrowChain::fire_45_fire_'+key, value)
        if ground_hit:
            self.impact_point = getattr(self,'impact_point',(40,0,0))
            self.set('AttackVariation::value',0)
            self.set('muloffset::value',1)
            self.set('AttackMod::value',1.5)
            self.run(39,{60})
            assert self.stack.pop()==1
            self.run(self.program.code[221],{92,191})
            assert not self.stack and not self.queries
            return self
        self.run(self.program.code[89], {94})
        self.visited.add(10)  # Original arrow hit precedes the burn controller.
        if kill_initial: self.positions.pop(10)
        if not blocked: self.run(self.program.code[211], {191})
        assert not self.stack and not self.queries
        return self


def check(p):
    results = []
    def record(name): results.append(name); print('PASS fire:', name, flush=True)
    def run(**kwargs):
        overrides = kwargs.pop('overrides', None)
        kill_initial = kwargs.pop('kill_initial', False)
        blocked = kwargs.pop('blocked', False)
        return FireVM(p, **kwargs).execute(overrides, kill_initial, blocked)
    def targets(v): return [e for _, e, _ in v.ignitions]
    for tier in TIERS:
        v = run(tier=tier)
        assert targets(v) == [10] and len(v.burn_ticks) == 10
        assert math.isclose(sum(x[2] for x in v.burn_ticks), 75, rel_tol=1e-6)
        assert v.burn_ticks[-1][0] == 5000
    record('all fire tiers: independent 5-second fire-only burns, original source/category/scaling inputs retained')
    for tick in (0, 50, 100, 333, 500, 777, 10000):
        v = run(overrides={'tick': tick}, tick_ms=100)
        assert math.isclose(sum(x[2] for x in v.burn_ticks), 75, rel_tol=1e-6)
    record('tick interval does not multiply DPS; final partial tick and zero interval are accounted for')
    v=run(positions={10:0,11:2},overrides={'duration':10000,'tick':50},tick_ms=50)
    for target in (10,11):
        ticks=[d for _,e,d in v.burn_ticks if e==target]
        assert len(ticks)==200 and math.isclose(sum(ticks),150,rel_tol=1e-6)
    record('reported 50ms/10s settings repeatedly damage original and secondary victims despite native hit history')
    ground={'ground_duration':1000,'ground_scale':3,'fanout':0,'duration':500,'tick':100}
    v=run(positions={10:0,11:20,12:20},overrides=ground,moves={4:{11:(2,0,0)},11:{12:(2,0,0)}})
    assert targets(v)==[10,11] and next(t for t,e,_ in v.ignitions if e==11)==400
    assert len(v.ground_visuals)==1 and v.ground_destroyed==[1000]
    assert math.isclose(sum(d for _,e,d in v.burn_ticks if e==11),7.5,rel_tol=1e-6)
    record('lingering initial area ignites late entrants, expires at its deadline and gives each entrant its own burn')
    v=run(positions={10:0,11:20},overrides=ground,kill_initial=True,moves={6:{11:(2,0,0)}})
    assert targets(v)==[11] and v.burn_ticks[-1][0]==1100 and v.ground_destroyed==[1000]
    record('empty ground area survives the initial kill; entrant burns continue after ground expiry')
    v=run(positions={10:0,11:20},overrides=ground,moves={4:{10:(100,0,0),11:(2,0,0)}})
    assert 11 in targets(v) and v.ground_visuals[0][1]==(0,0,0)
    record('ground origin stays at initial victim feet when that victim moves')
    v=run(overrides=ground,logout_at=300)
    assert v.ground_destroyed==[300]
    record('shooter disappearance cleans up the lingering ground visual')
    v=run(positions={10:0,11:20,12:20},overrides={**ground,'limit':1},moves={4:{11:(2,0,0),12:(1,0,0)}})
    assert targets(v)==[10,12] and v.ground_destroyed==[1000]
    record('ground entrants share the shot budget and select the nearest eligible newcomer first')
    v=run(positions={10:0,11:20},overrides=ground,moves={4:{11:(2,0,0)}},soaked={11})
    assert targets(v)==[10]
    record('ground area does not ignite Soaked entrants')
    v=run(overrides={**ground,'ground_scale':0})
    assert not v.ground_visuals and not v.ground_destroyed
    record('zero visual scale hides only the flames without disabling area lifetime')
    v=FireVM(p)
    v.set('ZatArrowChain::fire_ground_entity_value',1000)
    saved=p.code;p.code=p.p['codeShutdown']
    try: v.run(0,set())
    finally:p.code=saved
    assert v.ground_destroyed==[0] and not v.queries and not v.stack
    record('Impact shutdown explicitly destroys its own ground visual')
    v = run(overrides={'duration': 1250, 'tick': 700}, tick_ms=100)
    assert math.isclose(sum(x[2] for x in v.burn_ticks), 18.75, rel_tol=1e-6)
    record('uneven duration and tick cadence pay exactly the configured burn time')
    positions = {10: 0, 11: 2, 12: -2, 13: 4, 14: -4, 15: 8, 99: 1}
    v = run(positions=positions)
    assert targets(v)[:3] == [10, 11, 12] and len(targets(v)) == 6 and len(set(targets(v))) == 6
    assert all(t == 0 for t, _, _ in v.ignitions[:3])
    assert next(t for t,e,_ in v.ignitions if e==15) >= 800
    record('initial radius ignites all hostiles without blast, then delayed per-victim propagation beyond impact radius')
    v = run(positions={10:0,11:4,12:-4,13:8,14:-8}, overrides={'initial_radius':0,'fanout':1,'radius':4.1})
    assert targets(v) == [10,11,13]
    v = run(positions={10:0,11:4,12:-4,13:8,14:-8}, overrides={'initial_radius':0,'fanout':2,'radius':4.1})
    assert targets(v) == [10,11,12,13,14]
    record('linear versus two-way fan-out uses each living spreader as its own center')
    v = run(positions={10:0,11:4,12:-4,13:(0,4,0),14:8}, overrides={'initial_radius':0,'fanout':3,'radius':4.1})
    assert targets(v)[:4] == [10,11,12,13] and 14 in targets(v)
    record('three-way fan-out and 3D tie ordering')
    v = run(positions={10:0,40:4,41:1,42:2}, factions={40:2,41:12,42:11}, reorder_queries=True,
            overrides={'initial_radius':0,'fanout':1})
    assert targets(v) == [10,41,42,40]
    record('closest living hostile selection is independent of species/faction/query ordering')
    v = run(positions={10:0,11:1,12:2,13:3,14:4,15:5,16:6}, dead_targets={11},
            health={12:0,13:-1,14:None}, soaked={15})
    assert targets(v) == [10]
    record('corpses, nonpositive/missing health and Soaked enemies are not ignited')
    for opts in ({'soak_at':{10:200}}, {'death_at':{10:200}}):
        v=run(positions={10:0,11:4}, overrides={'initial_radius':0}, **opts)
        assert targets(v)==[10] and not v.burn_ticks
    record('death or Soaked before propagation cancels that branch and its remaining damage')
    v=run(positions={10:0,11:2,12:-2,13:6,14:-6}, death_at={11:200})
    assert 14 in targets(v) and not any(e==11 for _,e,_ in v.burn_ticks)
    record('extinguished sibling does not cancel another surviving branch')
    v=run(positions={10:0,11:2,12:4}, kill_initial=True)
    assert targets(v)==[11,12]
    record('an initial killing hit still seeds nearby living enemies from the saved impact origin')
    for budget in (1,2,3):
        v=run(positions=positions,overrides={'limit':budget})
        assert len(targets(v))==budget+1
    record('shared finite budget counts initial-area and later ignitions, excluding the first target')
    v=run(positions=positions,overrides={'strength':0})
    assert len(targets(v))==6 and all(d==0 for _,_,d in v.burn_ticks)
    record('explicit visited ledger prevents cycling at zero damage without native hit history')
    v=run(positions=positions,overrides={'fanout':0})
    assert targets(v)==[10,11,12]
    record('zero fan-out preserves the initial area and burn')
    v=run(positions={10:0,11:4},overrides={'initial_radius':0,'delay':10000})
    assert targets(v)==[10] and v.burn_ticks[-1][0]==5000
    record('burn expiry cancels spread when delay exceeds duration')
    v=run(positions={10:0,11:4},overrides={'initial_radius':0,'delay':0})
    assert v.ignitions[1][0]==100
    record('zero spread delay yields an engine update before the next generation')
    v=run(positions=positions,logout_at=600)
    assert max(t for t,_,_ in v.burn_ticks)==500
    record('source disappearance stops the controller')
    assert run(blocked=True).ignitions==[]
    assert run(dead_targets={10}).ignitions==[]
    record('blocked or already dead initial hits cannot start burns')
    v=run(positions={10:0,4294967294:2,268435457:2})
    assert targets(v)==[10,268435457,4294967294]
    record('exact high-bit entity IDs survive ledger load/store and ties')
    v=run(now=0xfffffff0)
    assert math.isclose(sum(x[2] for x in v.burn_ticks),75,rel_tol=1e-6)
    record('countdowns survive uint32 millisecond clock rollover')
    v=run(overrides={'duration':4294967295,'tick':4294967295,'delay':4294967295},tick_ms=1000000000)
    assert len(v.burn_ticks)==1 and math.isclose(v.burn_ticks[0][2],50*1.5*.2*4294967.295,rel_tol=1e-6)
    record('full uint32 duration/tick/delay work without signed-time truncation')
    v=run(overrides={'strength':1000})
    assert math.isclose(sum(x[2] for x in v.burn_ticks),375000,rel_tol=1e-6)
    record('high representable strength is accepted without a balance clamp')
    # Force the actual emitted capacity guard, not a test-only replacement branch.
    v=FireVM(p,positions=positions);v.set('ZatArrowChain::fire_capacity',3);v.execute()
    assert len(targets(v))==3 and len(v.burn_ticks)==30
    record('full ledger stops new ignition and finishes all existing burns')
    for tier in TIERS:
        v=FireVM(p,tier=tier);v.run(0,{2});v.stack.pop()
        v.now=4999;v.run(0,{2});v.stack.pop();assert not v.destroyed
        v.now=5000;v.run(0,{2});assert v.destroyed and not v.stack
    record('all enabled fire-arrow misses retain a five-second flight watchdog')
    # Exercise the last compiled record through the actual balanced dispatch.
    v=FireVM(p);slot_ptr=0xffff0000+p.names['ZatArrowChain::fire_slot']
    capacity=v.read(0xffff0000+p.names['ZatArrowChain::fire_capacity'])
    midpoint_ptr=0xffff0000+p.names['ZatArrowChain::fire_index_'+str(capacity//2)]
    roots=[i for i in range(len(p.code)-5) if p.code[i:i+5]==[22,slot_ptr,22,midpoint_ptr,5]]
    assert len(roots)==2
    read_root,write_root=roots
    written=len(p.code)-6
    loaded=p.code[write_root-1]  # Last read leaf branches to record_loaded.
    fields=['id','remaining','unpaid','spread_left','clock','pending']
    values=[4294967294,4294967295,123456789,2147483648,0xfffffff0,1]
    for slot in (0,capacity//2,capacity-1):
        v.set('ZatArrowChain::fire_slot',slot)
        for field,value in zip(fields,values):v.set('ZatArrowChain::fire_r_'+field,value)
        v.run(write_root,{written})
        for field in fields:v.set('ZatArrowChain::fire_r_'+field,0)
        v.run(read_root,{loaded})
        assert [v.read(0xffff0000+p.names['ZatArrowChain::fire_r_'+f]) for f in fields]==values
    record('first, middle and last compiled ledger records round-trip exact uint32 values without overwriting dispatch constants')
    return results


def check_zone(arrow_program, out, base_dir):
    file=next((out/'ImpactProgram').glob(ZONE+'*'))
    with (out/'zone-disassembly.log').open('w') as log:
        subprocess.run([str(out.parent/'parser/kfc-parser.exe'),'impact','disassemble','-i',str(file),'-o',str(out/'zone')],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
    zone=Program(json.loads(file.read_text()),(out/'zone.impact').read_text())
    zone.validate_structure((out/'zone.shutdown.impact').read_text())
    baseline=json.loads(next((base_dir/'ImpactProgram').glob(ZONE+'*')).read_text())
    code=zone.code[:len(baseline['code'])]
    for i in (0,1,50,51,52,54,55,56): code[i]=baseline['code'][i]
    assert code==baseline['code'] and zone.p['data'][:len(baseline['data'])]==baseline['data']
    clean=json.loads(next((base_dir/'TemplateResource').glob(ZONE_TEMPLATE+'*')).read_text())
    edited=json.loads(next((out/'TemplateResource').glob(ZONE_TEMPLATE+'*')).read_text())
    clean['components']=[c for c in clean['components'] if c['$type']!='keen::ecs::LifeTime']
    cfg=next(c['$value']['configValues'] for c in edited['components'] if c['$type']=='keen::ecs::ImpactConfiguration')
    marker=zone.layout[zone.names['ZatIncendiaryGround::managed_lifetime']]['configId']
    cfg['simple']=[c for c in cfg['simple'] if c['$value']['configId']!=marker]
    assert clean==edited  # Client VFX, sound, parameters, collider and vanilla damage config remain intact.
    arrow=json.loads(next((out/'TemplateResource').glob(TEMPLATES[2]+'*')).read_text())
    tags=next(c['$value']['tags'] for c in arrow['components'] if c['$type']=='keen::ecs::EntityTagContainer')
    assert {'tag':'b7ab3989-b293-45f6-b70f-998a2bf248de'} in tags

    class ZoneVM(VM):
        def __init__(self, marked=False, managed=True, parent_until=12000):
            super().__init__(arrow_program,TIERS[45],{},True,0)
            self.program=zone;self.mem=bytearray(zone.p['data']);self.marked=marked
            self.parent_until=parent_until;self.buff_count=0;self.tick_ms=10
            self.set('ZatIncendiaryGround::managed_lifetime',int(managed))
        def native(self, call_id, function):
            name,params=self.program.functions[function];args={};refs={}
            for role in ('out','cfg','in'):
                for kind,key,typ in params:
                    if kind==role:
                        ptr=self.stack.pop();refs[key]=ptr;args[key]=self.read(ptr)
            result=True
            if name=='GetParent': self.write(refs['entityId'],2)
            elif name=='IsValidEntity': result=self.now<self.parent_until
            elif name=='HasEntityTag':
                import uuid
                assert args['entityTag']==uuid.UUID('b7ab3989-b293-45f6-b70f-998a2bf248de').bytes_le
                result=self.marked
            elif name in ('OnEvent','FilterFriends'): self.write(refs['eventStream'],1)
            elif name=='ForEachCollisionInStream':
                result=args['index']==0;self.write(refs['index'],1)
                self.write(refs['otherRootEntity'],11)
            elif name=='ApplyBuff': self.buff_count+=1
            else: raise AssertionError(name)
            self.stack.append(int(result))
    visual=ZoneVM(marked=True);visual.run(0,set())
    assert visual.buff_count==0 and visual.destroyed and visual.now==12000
    ordinary=ZoneVM();ordinary.run(0,set())
    assert ordinary.buff_count>2 and ordinary.destroyed and ordinary.now==9000, (ordinary.buff_count,ordinary.destroyed,ordinary.now)
    unrelated=ZoneVM(managed=False)
    unrelated.run(0,{2})
    for _ in range(3):
        unrelated.run(2,{0});assert not unrelated.destroyed
        unrelated.run(0,{2})
    assert unrelated.buff_count==6
    return ['incendiary template retains native client VFX/audio and original damage configuration',
            'marked arrow zones apply no native buffs and survive past nine seconds until parent cleanup',
            'ordinary construct grenades retain native burns and a nine-second lifetime; other grenade templates bypass watchdog']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir',required=True,type=Path)
    parser.add_argument('--regression-package',type=Path)
    args=parser.parse_args();work=args.fixture_dir.resolve()
    assert (work/'SHOCK_MOD_TEST_FIXTURE').read_text().strip()=='disposable-shock-mod-test'
    spec=importlib.util.spec_from_file_location('eml',ROOT/'enshrouded_manager/eml_support.py')
    eml=importlib.util.module_from_spec(spec);spec.loader.exec_module(eml)
    mod=eml.EML(work/'Server',work/'state',ROOT/'enshrouded_manager/vendor/eml-v0.2.0/emm.exe')
    source=ROOT/'mods/zat-shock-tuning';mid='zat-shock-tuning'
    defaults=(source/'src/config.lua').read_text();version=json.loads((source/'mod.json').read_text())['version']
    original=eml.digest(work/'Server/enshrouded_server.kfc');results=[]
    def apply(config): mod.config_file(mid,'src/config.lua',config);mod.apply()
    def export(name):
        out=work/name;out.mkdir(exist_ok=True)
        with (out/'export.log').open('w') as log:
            subprocess.run([str(work/'parser/kfc-parser.exe'),'unpack','-g',str(work/'Server'),'-o',str(out),
                            '-f',','.join([GUID+'_d4922d88_0',*(g+'_39768775_0' for g in TEMPLATES),ZONE+'_d4922d88_0',ZONE_TEMPLATE+'_39768775_0'])],
                           stdout=log,stderr=subprocess.STDOUT,check=True)
        file=next((out/'ImpactProgram').glob(GUID+'*'))
        with (out/'disassembly.log').open('w') as log:
            subprocess.run([str(work/'parser/kfc-parser.exe'),'impact','disassemble','-i',str(file),'-o',str(out/'fire')],
                           stdout=log,stderr=subprocess.STDOUT,check=True)
        p=Program(json.loads(file.read_text()),(out/'fire.impact').read_text())
        p.validate_structure((out/'fire.shutdown.impact').read_text())
        return p,out
    try:
        mod.enable(True)
        if mid in mod.state()['mods']: mod.change_mod(mid,'remove')
        if args.regression_package:
            mod.import_zip(args.regression_package.read_bytes());mod.change_mod(mid,'enable')
            with zipfile.ZipFile(args.regression_package) as z:
                old_config=z.read(next(n for n in z.namelist() if n.endswith('src/config.lua'))).decode()
            apply(old_config.replace('fire_45 = { enabled = false','fire_45 = { enabled = true'))
            old_program,_=export('fire-alpha1-regression')
            broken=FireVM(old_program,positions={10:0,11:2},tick_ms=50).execute({'duration':10000,'tick':50})
            assert not any(e==10 for _,e,_ in broken.burn_ticks)
            assert len(broken.burn_ticks)==1 and broken.burn_ticks[0][1]==11
            results.append('shipped alpha.1 reproduces zero original-target ticks and one tiny secondary tick with native history semantics')
            mod.change_mod(mid,'remove')
        mod.import_zip((ROOT/f'dist/mods/Zat-Shock-Tuning-v{version}.zip').read_bytes());mod.change_mod(mid,'enable')
        assert 'src/config.lua' in mod.config_file(mid)['files']
        apply(defaults);baseline,base_dir=export('fire-baseline')
        assert 'Applied 0 setting changes' in mod.log().rsplit('ESM-Z: emm run',1)[-1]
        legacy=defaults[:defaults.index('    fire_arrows = {')]+defaults[defaults.index('    mass_destruction = {'):]
        apply(legacy)
        assert 'Applied 0 setting changes' in mod.log().rsplit('ESM-Z: emm run',1)[-1]
        results.append('legacy config without fire_arrows keeps fire entirely disabled')
        fire_config=defaults.replace('fire_15 = { enabled = false','fire_15 = { enabled = true')\
            .replace('fire_28 = { enabled = false','fire_28 = { enabled = true')\
            .replace('fire_45 = { enabled = false','fire_45 = { enabled = true')
        apply(fire_config);p,out=export('fire-enabled')
        old=baseline.code;new=p.code[:len(old)]
        for offset in (0,1,39,40,89,211,221): new[offset]=old[offset]
        assert new==old and p.p['data'][:len(baseline.p['data'])]==baseline.p['data']
        assert p.layout[:len(baseline.layout)]==baseline.layout
        for guid in TEMPLATES:
            clean=json.loads(next((base_dir/'TemplateResource').glob(guid+'*')).read_text())
            patched=json.loads(next((out/'TemplateResource').glob(guid+'*')).read_text())
            clean['components']=[c for c in clean['components'] if c['$type']!='keen::ecs::LifeTime']
            values=next(c['$value']['configValues'] for c in patched['components'] if c['$type']=='keen::ecs::ImpactConfiguration')
            values['simple']=[v for v in values['simple'] if v['$value']['configId']!=p.layout[p.names['ZatArrowChain::managed_flight']]['configId']]
            assert clean==patched
        results.append('package imports/configures remotely; default zero patches; original arrow body and unrelated fields preserved')
        results.extend(check(p))
        only45=defaults.replace('fire_45 = { enabled = false','fire_45 = { enabled = true')
        apply(only45);single,single_dir=export('fire-only45-enabled')
        for guid in TEMPLATES[:2]:
            assert json.loads(next((base_dir/'TemplateResource').glob(guid+'*')).read_text())==json.loads(next((single_dir/'TemplateResource').glob(guid+'*')).read_text())
        assert not FireVM(single,tier=15).execute().burn_ticks
        assert not FireVM(single,tier=28).execute().burn_ticks
        assert len(FireVM(single,tier=45).execute().burn_ticks)==10
        results.append('enabling only fire45 leaves disabled fire tiers and their templates untouched')
        apply(only45.replace('ground_fire_enabled = false','ground_fire_enabled = true'))
        ground_program,ground_dir=export('fire-ground-enabled')
        ground_vm=FireVM(ground_program).execute()
        assert len(ground_vm.ground_visuals)==1 and ground_vm.ground_destroyed==[5000]
        results.append('ground options compile from uploaded config and execute without test overrides')
        gv=FireVM(ground_program,positions={11:41,12:80},moves={3:{12:(42,0,0)}}).execute(ground_hit=True)
        assert {e for _,e,_ in gv.burn_ticks}=={11,12}
        assert gv.ground_visuals==[(0,(40,0,0))] and gv.ground_destroyed==[5000]
        assert not gv.hits and 0 not in {e for _,e,_ in gv.ignitions}
        results.append('terrain collision uses actual contact transform, ignites nearby and entering enemies, no direct terrain damage')
        gv=FireVM(ground_program,positions={11:80},moves={20:{11:(41,0,0)}}).execute(ground_hit=True)
        assert gv.burn_ticks and min(t for t,_,_ in gv.burn_ticks)>=2500
        results.append('an empty ground impact remains active until a later enemy enters')
        for tier in (15,28):
            gv=FireVM(ground_program,tier=tier).execute(ground_hit=True)
            assert not gv.ground_visuals and not gv.burn_ticks
        assert not FireVM(single).execute(ground_hit=True).ground_visuals
        results.append('disabled tiers and ground_fire_enabled=false retain the vanilla terrain path')
        results.extend(check_zone(ground_program,ground_dir,base_dir))
        # Full mix must compile within BOTH actual 16-bit native limits.
        apply(defaults.replace('enabled = false','enabled = true').replace('targets_per_spread = 1','targets_per_spread = 3'))
        mixed,_=export('fire-mixed-enabled')
        assert len(mixed.code)<=65535 and len(mixed.p['data'])<=65535
        assert len(mixed.scenario().hits)==3
        assert len(FireVM(mixed).execute().burn_ticks)==10
        results.append('all three fire and shock tiers coexist within native limits; both controllers execute')
        apply((ROOT/'mods/fixtures/fire_damage_report.lua').read_text())
        reported,_=export('fire-reported-settings')
        report_vm=FireVM(reported,positions={10:0,11:2},tick_ms=50).execute()
        for target in (10,11):
            ticks=[d for _,e,d in report_vm.burn_ticks if e==target]
            assert len(ticks)==200 and math.isclose(sum(ticks),150,rel_tol=1e-6)
        assert report_vm.ground_destroyed==[10000]
        results.append('user tuning plus new ten-second ground fire imports and applies alongside enabled shock45')
        # Invalid fields must fail validation before any resource patch.
        for old,new in [('burn_tick_ms = 500','burn_tick_ms = -1'),
                        ('burn_duration_ms = 5000','burn_duration_ms = 1.5'),
                        ('initial_radius = 3.0','initial_radius = 1e400'),
                        ('burn_damage_multiplier_per_second = 0.2','burn_damage_multiplier_per_second = 1e38'),
                        ('ground_fire_enabled = false','ground_fire_enabled = 1'),
                        ('ground_fire_duration_ms = 5000','ground_fire_duration_ms = -1'),
                        ('ground_fire_visual_scale = 1.0','ground_fire_visual_scale = 1e400')]:
            try: apply(fire_config.replace(old,new))
            except Exception: pass
            else: raise AssertionError('invalid config accepted: '+new)
        results.append('negative/fractional/nonfinite/derived-overflow fire settings rejected')
    finally:
        mod.config_file(mid,'src/config.lua',defaults);mod.restore()
        assert eml.digest(work/'Server/enshrouded_server.kfc')==original
        (work/'fire-results.json').write_text(json.dumps({'version':version,'checks':results,'count':len(results),
            'restored_original_index':True,'combat_tested':False},indent=2))
    print(json.dumps({'checks':len(results),'restored':True,'combat_tested':False}))


if __name__=='__main__': main()
