"""Validate the companion with the shipped base ZIP in a disposable fixture."""
import argparse
import importlib.util
import json
import re
import struct
import subprocess
import secrets
import time
import uuid
from pathlib import Path

from test_arrow_chain_program import Program, VM

ROOT=Path(__file__).resolve().parents[1]
MID='zat-fire-effect-lab'
BASE='zat-shock-tuning'
ARROW='c0a8231a-f87f-467c-ad9d-6d4fe93ecda7'


class PreviewVM(VM):
    def set(self,name,value):
        if name in self.program.names: super().set(name,value)

    def __init__(self,p,marked=True,selected=True,ancestor=False,until=1e20,ordinary=False,leader=False):
        super().__init__(p,0,{},True,0)
        self.marked,self.ancestor,self.until=marked,ancestor,until
        self.tick_ms=100
        self.set('ZatFireEffectLab::selected',int(selected))
        self.set('ZatFireEffectLab::leader',int(leader))
        self.native_calls=[]
        self.ordinary=ordinary
        self.spawns=[]

    def native(self,call_id,function):
        name,params=self.program.functions[function]
        args,refs={},{}
        for role in ('out','cfg','in'):
            for kind,key,typ in params:
                if kind==role:
                    ptr=self.stack.pop();refs[key]=ptr;args[key]=self.read(ptr)
        self.native_calls.append(name)
        result=True
        if name=='GetParent':self.write(refs['entityId'],2)
        elif name=='GetEntityParent':self.write(refs['entityId'],3)
        elif name=='IsValidEntity':result=self.now<self.until
        elif name=='HasEntityTag':result=self.marked if args['entityId']==2 else self.ancestor
        elif name=='GetSelf':self.write(refs['entityId'],4)
        elif name=='GetTransform':
            assert args['entityId']==4
            self.write(refs['transform'],(40,2,60))
            entry=self.program.layout[refs['transform'] & 0xffff]
            struct.pack_into('<3f',self.mem,entry['offsetInBytes']+40,2,1,2)
        elif name=='SpawnEntity':
            assert args['parentEntityId']==2 and args['addDespawnLink']==1
            assert args['breakImpactHierarchy']==0 and args['transform']==(40,2,60)
            entry=self.program.layout[refs['transform'] & 0xffff]
            assert struct.unpack_from('<3f',self.mem,entry['offsetInBytes']+40)==(2,1,2)
            self.spawns.append(str(uuid.UUID(bytes_le=args['templateInput'])))
        elif self.ordinary and name=='GetRoot':self.write(refs['entityId'],1)
        elif self.ordinary and (name=='OnEvent' or name.startswith('Filter')): self.write(refs['eventStream'],1)
        elif self.ordinary and name=='ForEachCollisionInStream':
            result=args['index']==0;self.write(refs['index'],1);self.write(refs['otherEntity'],11)
        elif self.ordinary and name=='ApplyBuff': pass
        else: raise AssertionError('Native effect executed in preview: '+name)
        self.stack.append(int(result))


def startup(work):
    server=work/'Server';file=server/'enshrouded_server.json';saved=file.read_bytes()
    prefix='lab-startup-'+uuid.uuid4().hex[:8];logs=server/(prefix+'-logs');logs.mkdir()
    proc=None
    try:
        config=json.loads(saved);config.update(name=prefix,ip='127.0.0.1',queryPort=31079,slotCount=2,
            saveDirectory=str(server/(prefix+'-save')),logDirectory=str(logs))
        for group in config.get('userGroups',[]):group['password']=secrets.token_urlsafe(32)
        file.write_text(json.dumps(config,indent=2));start=time.monotonic()
        with (logs/'stdout.log').open('w') as output:
            proc=subprocess.Popen([str(server/'enshrouded_server.exe')],cwd=server,stdout=output,
                stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            ready=False
            while time.monotonic()-start<45 and proc.poll() is None:
                text='\n'.join(p.read_text(errors='replace') for p in logs.glob('*.log'))
                ready="current='Host_Online'" in text and 'Switching state from LoadEcsScene to Run' in text
                if ready:break
                time.sleep(.5)
            assert ready and proc.poll() is None,'Server startup failed: '+str(logs)
            return {'reached_run':True,'elapsed_seconds':round(time.monotonic()-start,1),'log_directory':str(logs)}
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
        file.write_bytes(saved)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixture-dir',required=True,type=Path)
    ap.add_argument('--quick',action='store_true')
    ap.add_argument('--startup',action='store_true')
    a=ap.parse_args();work=a.fixture_dir.resolve()
    assert (work/'SHOCK_MOD_TEST_FIXTURE').read_text().strip()=='disposable-shock-mod-test'
    spec=importlib.util.spec_from_file_location('eml',ROOT/'enshrouded_manager/eml_support.py')
    eml=importlib.util.module_from_spec(spec);spec.loader.exec_module(eml)
    mod=eml.EML(work/'Server',work/'state',ROOT/'enshrouded_manager/vendor/eml-v0.2.0/emm.exe')
    assert mod.state()['mods'][BASE]['version']==json.loads((ROOT/f'mods/{BASE}/mod.json').read_text())['version']
    assert mod.state()['mods'][BASE]['enabled']
    original_index=eml.digest(work/'Server/enshrouded_server.kfc')
    original_state=mod.state_path.read_bytes()
    original_config=mod.config_file(BASE,'src/config.lua')['content']
    defaults=(ROOT/f'mods/{MID}/src/config.lua').read_text()
    version=json.loads((ROOT/f'mods/{MID}/mod.json').read_text())['version']
    package=ROOT/f'dist/mods/Zat-Fire-Effect-Lab-v{version}.zip'
    catalog=dict((key,(guid,vfx)) for key,guid,vfx in re.findall(r'(\w+)=\{"([^"]+)","([^"]+)"\}',(ROOT/f'mods/{MID}/src/catalog.lua').read_text()))
    results=[]
    def record(s):results.append(s);print('PASS lab:',s,flush=True)
    def apply(text):mod.config_file(MID,'src/config.lua',text);mod.apply()
    def export(name,guids):
        out=work/('lab-'+name);out.mkdir(exist_ok=True)
        with (out/'export.log').open('w') as log:
            subprocess.run([str(work/'parser/kfc-parser.exe'),'unpack','-g',str(work/'Server'),'-o',str(out),'-f',','.join(guids)],stdout=log,stderr=subprocess.STDOUT,check=True)
        return out
    def program(out,guid):
        path=next((out/'ImpactProgram').glob(guid+'*'));stem=out/guid
        with (out/(guid+'.log')).open('w') as log:
            subprocess.run([str(work/'parser/kfc-parser.exe'),'impact','disassemble','-i',str(path),'-o',str(stem)],stdout=log,stderr=subprocess.STDOUT,check=True)
        p=Program(json.loads(path.read_text()),stem.with_suffix('.impact').read_text())
        p.validate_structure(stem.with_suffix('.shutdown.impact').read_text())
        return p
    try:
        if MID in mod.state()['mods']:mod.change_mod(MID,'remove')
        mod.import_zip(package.read_bytes());mod.change_mod(MID,'enable')
        assert mod.config_file(MID)['default_file']=='src/config.lua'
        main_config=(ROOT/'mods/fixtures/fire_damage_report.lua').read_text()
        mod.config_file(BASE,'src/config.lua',main_config)
        apply(defaults)
        first=export('off',[ARROW+'_d4922d88_0']);baseline=json.loads(next((first/'ImpactProgram').glob('*.json')).read_text())
        record('separate ZIP imports and Configure selects config.lua; both mods apply with reported tuning')
        selected_catalog=list(catalog.items())[:1] if a.quick else list(catalog.items())
        seen=set()
        for key,(guid,vfx) in selected_catalog:
            settings=defaults.replace(key+' = false',key+' = true')
            apply(settings)
            # Extract selected template to discover its native/server-controller program.
            out=export(key,[guid+'_39768775_0',ARROW+'_d4922d88_0'])
            template=json.loads(next((out/'TemplateResource').glob(guid+'*')).read_text())
            cs={x['$type']:x['$value'] for x in template['components']}
            assert cs['keen::ecs::VfxComponentResource']['vfx']==vfx
            assert 'keen::ecs::LifeTime' not in cs
            pg=cs['keen::ecs::Impact']['program']
            out=export(key,[pg+'_d4922d88_0'])
            p=program(out,pg)
            configs={v['$value']['configId']['value']:v['$value']['value'] for v in cs['keen::ecs::ImpactConfiguration']['configValues']['simple']}
            assert configs[p.p['dataLayout'][p.names['ZatFireEffectLab::selected']]['configId']['value']] is True
            preview=PreviewVM(p);preview.run(0,set())
            assert preview.destroyed and preview.now==10000 and not preview.stack
            for duration in (100,1500,30000,4294967295):
                timed=PreviewVM(p);timed.set('ZatFireEffectLab::duration',duration)
                timed.tick_ms=duration;timed.run(0,set())
                assert timed.destroyed and timed.now==duration
            cancelled=PreviewVM(p,until=300);cancelled.run(0,set())
            assert cancelled.destroyed and cancelled.now==300
            if key=='construct_heavy_fire_ground':
                ordinary=PreviewVM(p,marked=False,ordinary=True)
                ordinary.set('ZatFireEffectLab::native_lifetime',24000)
                ordinary.run(0,set())
                assert ordinary.destroyed and ordinary.now==24000
                assert ordinary.native_calls.count('ApplyBuff')==240
                record('ordinary heavy-fire instances retain native burning and 24-second lifetime despite ten-second preview setting')
            patched=json.loads(next((out/'ImpactProgram').glob(ARROW+'*')).read_text()) if pg!=ARROW else p.p
            assert patched['code']==baseline['code'] and patched['dataLayout']==baseline['dataLayout']
            mapping={e['dbgName']:e for e in patched['dataLayout']}
            for suffix in ('duration','ground_duration'):
                e=mapping['ZatArrowChain::fire_45_fire_'+suffix]
                assert struct.unpack_from('<I',bytes(patched['data']),e['offsetInBytes'])[0]==10000
            assert mod.config_file(BASE,'src/config.lua')['content']==main_config
            record(key+': compiles, keeps native VFX, no preview native damage/spawns, timed and early cleanup; original arrow code unchanged')
            if key=='construct_heavy_flamethrower':
                beam='80024779-8439-4e3c-afde-bb1f80ec10bc'
                child=program(export('beam-child',[beam+'_d4922d88_0']),beam)
                descendant=PreviewVM(child,marked=False,selected=False,ancestor=True)
                descendant.run(0,set());assert descendant.destroyed and descendant.now==0
                record('heavy flamethrower beam descendants stop before damage or snow terraforming')
            seen.add(guid)
        if not a.quick:
            combos=[['construct_incendiary_ground','player_incendiary_ground'],
                    ['construct_barrage_explosion','construct_barrage_fuse'],
                    ['construct_modular_flamethrower_on','construct_modular_left_flame','construct_modular_right_flame','construct_modular_onehanded_flame','construct_modular_firebeam'],
                    list(catalog)]
            for combo_index,combo in enumerate(combos):
                settings=defaults.replace('burn_time_ms = 10000','burn_time_ms = 1700')
                for key in combo:settings=settings.replace(key+' = false',key+' = true')
                apply(settings)
                expected=[]
                for key in sorted(combo):
                    if catalog[key][0] not in expected:expected.append(catalog[key][0])
                out=export('combo-'+str(combo_index),[*(g+'_39768775_0' for g in expected),ARROW+'_d4922d88_0'])
                templates={g:json.loads(next((out/'TemplateResource').glob(g+'*')).read_text()) for g in expected}
                components={g:{x['$type']:x['$value'] for x in t['components']} for g,t in templates.items()}
                program_ids={cs['keen::ecs::Impact']['program'] for cs in components.values()}
                export('combo-'+str(combo_index),[g+'_d4922d88_0' for g in program_ids])
                programs={g:program(out,g) for g in program_ids}
                spawns=[]
                for i,g in enumerate(expected):
                    cs=components[g];p=programs[cs['keen::ecs::Impact']['program']]
                    configs={v['$value']['configId']['value']:v['$value']['value'] for v in cs['keen::ecs::ImpactConfiguration']['configValues']['simple']}
                    leader_id=p.layout[p.names['ZatFireEffectLab::leader']]['configId']['value']
                    assert configs[leader_id]==(i==0)
                    assert sum(e['dbgName']=='ZatFireEffectLab::selected' for e in p.layout)==1
                    vm=PreviewVM(p,leader=configs[leader_id]);vm.run(0,set())
                    assert vm.now==1700 and vm.destroyed and not vm.stack
                    assert vm.spawns==(expected[1:] if i==0 else [])
                    early=PreviewVM(p,leader=configs[leader_id],until=300);early.run(0,set())
                    assert early.destroyed and early.now==300
                    spawns.extend(vm.spawns)
                assert [expected[0],*spawns]==expected and len(set(expected))==len(expected)
                arrow=json.loads(next((out/'ImpactProgram').glob(ARROW+'*')).read_text())
                assert arrow['code']==baseline['code'] and arrow['dataLayout']==baseline['dataLayout']
                mapping={e['dbgName']:e for e in arrow['dataLayout']}
                ptr=mapping['ZatArrowChain::fire_ground_template']
                assert str(uuid.UUID(bytes_le=bytes(arrow['data'][ptr['offsetInBytes']:ptr['offsetInBytes']+16])))==expected[0]
                record('combination '+str(combo_index+1)+': '+str(len(combo))+' switches / '+str(len(expected))+' visuals; each spawns once at common transform with arrow cleanup, shared duration, no recursion or arrow-code changes')
            for bad in [defaults.replace('burn_time_ms = 10000','burn_time_ms = -1'),
                        defaults.replace('burn_time_ms = 10000','burn_time_ms = 1.5'),
                        defaults.replace('visual_scale = 1.0','visual_scale = 1e400'),
                        defaults.replace('construct_incendiary_ground = false','construct_incendiary_ground = 1')]:
                try:apply(bad)
                except Exception:pass
                else:raise AssertionError('invalid settings accepted')
            record('invalid boolean, negative/fractional time and overflowing scale rejected; multiple selections accepted')
            apply(defaults.replace('construct_incendiary_ground = false','construct_incendiary_ground = true').replace('burn_time_ms = 10000','burn_time_ms = 0'))
            off=export('zero',[ARROW+'_d4922d88_0'])
            assert json.loads(next((off/'ImpactProgram').glob('*.json')).read_text())==baseline
            apply(defaults)
            off=export('off-again',[ARROW+'_d4922d88_0'])
            assert json.loads(next((off/'ImpactProgram').glob('*.json')).read_text())==baseline
            record('zero time and all-false are exact no-ops; switching off restores original mod output')
        report={'package_sha256':eml.digest(package),'checks':results,'count':len(results),'unique_effects_tested':len(seen),'native_rendering_tested':False,'combat_tested':False}
        if a.startup:
            settings=defaults
            for key in catalog:settings=settings.replace(key+' = false',key+' = true')
            apply(settings)
            report['isolated_startup']=startup(work)
            record('both mods reach native Run with all 16 switches enabled')
            report['count']=len(results)
    finally:
        mod.config_file(BASE,'src/config.lua',original_config)
        if MID in mod.state()['mods']:mod.change_mod(MID,'remove')
        mod.restore();mod.state_path.write_bytes(original_state)
        assert eml.digest(work/'Server/enshrouded_server.kfc')==original_index
    report['restored_original_index_and_config']=True
    (work/'fire-effect-lab-results.json').write_text(json.dumps(report,indent=2))
    package.with_suffix('.zip.validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
