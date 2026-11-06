"""Validate the single combined mod, including the reported startup failure."""
import argparse
import importlib.util
import json
import re
import struct
import subprocess
import uuid
from pathlib import Path
from test_arrow_chain_program import Program
from validate_fire_effect_lab import PreviewVM, startup

ROOT=Path(__file__).resolve().parents[1]
MID=BASE='zat-shock-tuning'
ARROW='c0a8231a-f87f-467c-ad9d-6d4fe93ecda7'

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
    assert not mod.state()['mods'].get('zat-fire-effect-lab',{}).get('enabled'), 'Remove the old companion from this disposable fixture first'
    original_index=eml.digest(work/'Server/enshrouded_server.kfc')
    original_config=mod.config_file(BASE,'src/config.lua')['content'] if BASE in mod.state()['mods'] else None
    defaults=(ROOT/f'mods/{MID}/src/config.lua').read_text()
    version=json.loads((ROOT/f'mods/{MID}/mod.json').read_text())['version']
    package=ROOT/f'dist/mods/Zat-Shock-Tuning-v{version}.zip'
    catalog=dict((key,(guid,vfx)) for key,guid,vfx in re.findall(r'(\w+)=\{"([^"]+)","([^"]+)"\}',(ROOT/f'mods/{MID}/src/fire_effect_catalog.lua').read_text()))
    results=[]
    def record(s):results.append(s);print('PASS combined:',s,flush=True)
    def merge(main,effects):
        # Replace the full top-level fire_effects block while retaining gameplay settings.
        section=effects[effects.index('    fire_effects = {'):effects.index('    mass_destruction = {')]
        if '    fire_effects = {' in main:
            return main[:main.index('    fire_effects = {')]+section+main[main.index('    mass_destruction = {'):]
        return main.replace('    mass_destruction = {',section+'    mass_destruction = {')
    main_config=(ROOT/'mods/fixtures/fire_damage_report.lua').read_text()
    def apply(text,main=None):
        content=merge(main_config if main is None else main,text)
        mod.config_file(MID,'src/config.lua',content);mod.apply()
        assert mod.config_file(MID,'src/config.lua')['content']==content
    def raw_apply(content):
        mod.config_file(MID,'src/config.lua',content);mod.apply()
    def arrow_export(name):
        out=export(name,[ARROW+'_d4922d88_0'])
        return json.loads(next((out/'ImpactProgram').glob(ARROW+'*')).read_text())
    def export(name,guids):
        out=work/('combined-'+name);out.mkdir(exist_ok=True)
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
        assert set(mod.state()['mods'])=={BASE}, 'Combined tests must install only one mod'
        raw_apply(defaults)
        assert 'Applied 0 patches' in mod.log().rsplit('ESM-Z: emm run',1)[-1]
        apply(defaults)
        first=export('off',[ARROW+'_d4922d88_0']);baseline=json.loads(next((first/'ImpactProgram').glob('*.json')).read_text())
        record('one ZIP and one config; vanilla defaults patch nothing; existing tuning config remains compatible')
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
        if not a.quick:
            selected=defaults.replace('dragon_germination_ground = false','dragon_germination_ground = true')
            # Reproduce the actual failure: enabled fire_45, all ground switches false.
            no_ground=main_config.replace('ground_fire_enabled = true','ground_fire_enabled = false')
            raw_apply(no_ground)
            expected=arrow_export('no-ground-baseline')
            apply(selected,no_ground)
            assert 'Inactive: no enabled ground-fire profile' in mod.log().rsplit('ESM-Z: emm run',1)[-1]
            assert arrow_export('no-ground-selected')==expected
            record('reported missing-ground-hook condition applies successfully and preserves combat output')
            if a.startup:
                inactive_startup=startup(work)
                record('reported missing-ground-hook condition reaches native server Run')
            for label,main in [
                ('all tiers disabled',main_config.replace('enabled = true','enabled = false')),
                ('zero radius',main_config.replace('initial_radius = 14','initial_radius = 0')),
                ('zero chance',main_config.replace('chance_percent = 100','chance_percent = 0')),
                ('zero burn duration',main_config.replace('burn_duration_ms = 10000','burn_duration_ms = 0')),
                ('zero ground duration',main_config.replace('ground_fire_duration_ms = 10000','ground_fire_duration_ms = 0'))]:
                raw_apply(main);expected=arrow_export('inactive-'+label.replace(' ','-')+'-baseline')
                apply(selected,main)
                assert arrow_export('inactive-'+label.replace(' ','-'))==expected
                record(label+': selected visuals are inactive without changing arrow behavior')
            # The shared duration must validate the final damage coefficient too.
            overflow=main_config.replace('burn_damage_multiplier_per_second = 0.2','burn_damage_multiplier_per_second = 1e32')
            bad=selected.replace('burn_time_ms = 10000','burn_time_ms = 4294967295')
            try:apply(bad,overflow)
            except RuntimeError:
                assert 'shared total burn multiplier' in mod.log().rsplit('ESM-Z: emm run',1)[-1]
                assert eml.digest(work/'Server/enshrouded_server.kfc')==original_index
            else:raise AssertionError('shared duration overflow accepted')
            record('shared burn duration rejects float32 overflow and restores the clean index')
            raw_apply(main_config)
            assert arrow_export('legacy-config')==baseline
            record('older config without fire_effects retains exact gameplay output')
            # Keep duration/scale changes confined to active ground tiers.
            mixed=main_config.replace('fire_15 = { enabled = false','fire_15 = { enabled = true')
            apply(selected,mixed)
            data=arrow_export('mixed-tiers');entries={e['dbgName']:e for e in data['dataLayout']}
            for key,want in [('fire_15_fire_duration',5000),('fire_15_fire_ground_duration',0),
                             ('fire_45_fire_duration',10000),('fire_45_fire_ground_duration',10000)]:
                e=entries['ZatArrowChain::'+key]
                assert struct.unpack_from('<I',bytes(data['data']),e['offsetInBytes'])[0]==want
            record('shared duration affects active ground tiers only')
            # Validate the exact config supplied for the user's migration.
            supplied=ROOT/'mods/fixtures/combined_fire_report.lua'
            raw_apply(supplied.read_text())
            data=arrow_export('migrated-user-config');entries={e['dbgName']:e for e in data['dataLayout']}
            e=entries['ZatArrowChain::fire_ground_template']
            assert str(uuid.UUID(bytes_le=bytes(data['data'][e['offsetInBytes']:e['offsetInBytes']+16])))==catalog['dragon_germination_ground'][0]
            for key,want in [('fire_45_fire_duration',10000),('fire_45_fire_ground_duration',10000)]:
                e=entries['ZatArrowChain::'+key]
                assert struct.unpack_from('<I',bytes(data['data']),e['offsetInBytes'])[0]==want
            e=entries['ZatArrowChain::fire_45_fire_ground_scale']
            assert struct.unpack_from('<f',bytes(data['data']),e['offsetInBytes'])[0]==3
            record('migrated user config selects dragon germination, ten-second burn and visual scale 3')
            if a.startup:
                user_startup=startup(work)
                record('migrated user config reaches native server Run')
        report={'package_sha256':eml.digest(package),'checks':results,'count':len(results),'unique_effects_tested':len(seen),'native_rendering_tested':False,'combat_tested':False}
        if a.startup:
            if not a.quick:
                report['inactive_startup']=inactive_startup
                report['migrated_config_startup']=user_startup
            settings=defaults
            for key in catalog:settings=settings.replace(key+' = false',key+' = true')
            apply(settings)
            report['isolated_startup']=startup(work)
            record('single combined mod reaches native Run with all 16 switches enabled')
            report['count']=len(results)
    finally:
        mod.config_file(BASE,'src/config.lua',original_config or defaults)
        mod.restore()
        assert eml.digest(work/'Server/enshrouded_server.kfc')==original_index
    report['restored_original_index']=True
    (work/'combined-fire-effects-results.json').write_text(json.dumps(report,indent=2))
    package.with_suffix('.zip.validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
