"""Package/apply/export and control-flow checks in a disposable EML server fixture.

Native calls in the bytecode scenarios are modeled. Combat/network certification
requires real clients. The server index and config are restored in finally.
"""
import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
from test_arrow_chain_program import Program, check

ROOT = Path(__file__).resolve().parents[1]
GUID = 'c0a8231a-f87f-467c-ad9d-6d4fe93ecda7_d4922d88_0'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir', required=True, type=Path)
    parser.add_argument('--regression-package', type=Path,
                        help='Optional original alpha.1 ZIP to reproduce the reported invalid native load')
    parser.add_argument('--single-hop-package', type=Path,
                        help='Optional alpha.2 ZIP to check the deferred-history single-hop regression')
    args = parser.parse_args()
    work = args.fixture_dir.resolve()
    assert (work/'SHOCK_MOD_TEST_FIXTURE').read_text().strip() == 'disposable-shock-mod-test'
    spec = importlib.util.spec_from_file_location('eml', ROOT/'enshrouded_manager/eml_support.py')
    eml = importlib.util.module_from_spec(spec); spec.loader.exec_module(eml)
    mod = eml.EML(work/'Server', work/'state', ROOT/'enshrouded_manager/vendor/eml-v0.2.0/emm.exe')
    mid = 'zat-shock-tuning'
    source = ROOT/'mods'/mid
    version = json.loads((source/'mod.json').read_text())['version']
    defaults = (source/'src/config.lua').read_text()
    reported = (ROOT/'mods/fixtures/arrow_chain_damage_report.lua').read_text()
    original = eml.digest(work/'Server/enshrouded_server.kfc')
    results = []
    def record(name):
        results.append(name); print('PASS', name, flush=True)
    def log():
        return mod.log().rsplit('ESM-Z: emm run', 1)[-1]
    def export(name):
        out = work/name; out.mkdir(exist_ok=True)
        with (out/'export.log').open('w') as output:
            subprocess.run([str(work/'parser/kfc-parser.exe'), 'unpack', '-g', str(work/'Server'),
                            '-o', str(out), '-f', GUID], stdout=output, stderr=subprocess.STDOUT, check=True)
        file = out/'ImpactProgram'/f'{GUID}.json'
        with (out/'disassembly.log').open('w') as output:
            subprocess.run([str(work/'parser/kfc-parser.exe'), 'impact', 'disassemble', '-i', str(file),
                            '-o', str(out/'chain')], stdout=output, stderr=subprocess.STDOUT, check=True)
        return json.loads(file.read_text()), (out/'chain.impact').read_text()
    try:
        mod.enable(True)
        if mid in mod.state()['mods']:
            mod.change_mod(mid, 'remove')
        if args.regression_package:
            mod.import_zip(args.regression_package.read_bytes()); mod.change_mod(mid, 'enable')
            mod.config_file(mid, 'src/config.lua', reported); mod.apply()
            broken, assembly = export('chain-alpha1-regression')
            old = Program(broken, assembly)
            for ammo in (123, 3133483038, 2453015274, 2369196415):
                try:
                    old.scenario(ammo=ammo)
                except AssertionError as error:
                    assert 'native VM rejects GLoad type before damage' in str(error), error
                    assert 'Ammunition::value' in str(error), error
                else:
                    raise AssertionError('Regression did not catch the alpha.1 unsupported ItemId load')
            record('original alpha.1 and reported settings reproduce invalid native ItemId load for every ammo ID')
            mod.restore(); mod.change_mod(mid, 'remove')
        if args.single_hop_package:
            mod.import_zip(args.single_hop_package.read_bytes()); mod.change_mod(mid, 'enable')
            mod.config_file(mid, 'src/config.lua', reported); mod.apply()
            old_resource, assembly = export('chain-alpha2-single-hop')
            old = Program(old_resource, assembly)
            assert len(old.scenario(ammo=2369196415, deferred=True).hits) == 1
            assert len(old.scenario(ammo=2369196415, deferred=False).hits) == 3
            record('alpha.2 reproduces one secondary hit under deferred history but passes the old immediate-history model')
            mod.restore(); mod.change_mod(mid, 'remove')
        mod.import_zip((ROOT/f'dist/mods/Zat-Shock-Tuning-v{version}.zip').read_bytes())
        mod.change_mod(mid, 'enable')
        assert mod.config_file(mid)['default_file'] == 'src/config.lua'
        mod.apply()
        assert 'Applied 0 patches' in log()
        baseline, _ = export('chain-baseline')
        record('ZIP imports, editable config is default, disabled chains leave zero patches')
        enabled = defaults.replace('enabled = false, chance_percent', 'enabled = true, chance_percent')
        mod.config_file(mid, 'src/config.lua', enabled); mod.apply()
        assert 'Applied 1 patches' in log(), log()
        p, text = export('chain-enabled')
        original_code = p['code'][:len(baseline['code'])]
        for offset in (89, 211):
            original_code[offset] = baseline['code'][offset]
        assert original_code == baseline['code']
        assert p['data'][:len(baseline['data'])] == baseline['data']
        assert p['dataLayout'][:55] == baseline['dataLayout']
        assert p['programGuid'] == baseline['programGuid'] and p['id'] == baseline['id']
        assert len(p['queryCallIds']) == 3
        assert len(set(p['queryCallIds'])) == 3
        record('one existing program patched; original data/layout and all but two branch operands preserved')
        maximum = Program(p, text).validate_structure((work/'chain-enabled/chain.shutdown.impact').read_text())
        record(f'complete control-flow/operand audit: balanced stacks, valid branches, maximum stack {maximum}')
        results.extend(check(p, text))
        mod.apply()
        repeated, _ = export('chain-repeated')
        assert repeated == p
        record('reapplying reconstructs identical decoded program without compounding')
        mixed = enabled.replace(
            'eternal_20 = { enabled = true, chance_percent = 100, spread_radius = 7.0, damage = 0.5, max_jumps = 0, targets_per_spread = 1 }',
            'eternal_20 = { enabled = true, chance_percent = 25, spread_radius = 7.0, damage = 9, max_jumps = 2, targets_per_spread = 1 }')
        mixed = mixed.replace(
            'eternal_36 = { enabled = true, chance_percent = 100, spread_radius = 7.0, damage = 0.5, max_jumps = 0, targets_per_spread = 1 }',
            'eternal_36 = { enabled = true, chance_percent = 100, spread_radius = 7.0, damage = 3, max_jumps = 1, targets_per_spread = 1 }')
        mixed = mixed.replace('eternal_45 = { enabled = true', 'eternal_45 = { enabled = false')
        mod.config_file(mid, 'src/config.lua', mixed); mod.apply()
        profile, assembly = export('chain-mixed')
        q = Program(profile, assembly)
        q.validate_structure((work/'chain-mixed/chain.shutdown.impact').read_text())
        assert q.scenario(rng=0.5).hits == []
        assert q.scenario(rng=0.1).hits == [(11, 9), (12, 9)]
        assert q.scenario(ammo=2453015274).hits == [(11, 3)]
        assert q.scenario(ammo=2369196415).hits == []
        record('modeled chance pass/fail, finite jump limits and independent tier enable/damage')
        mod.config_file(mid, 'src/config.lua', reported); mod.apply()
        profile, assembly = export('chain-reported-settings')
        q = Program(profile, assembly)
        q.validate_structure((work/'chain-reported-settings/chain.shutdown.impact').read_text())
        original_ammo = profile['dataLayout'][q.names['Ammunition::value']]
        alias = profile['dataLayout'][q.names['ZatArrowChain::ammunition_value']]
        assert alias['offsetInBytes'] == original_ammo['offsetInBytes']
        assert alias['size'] == original_ammo['size'] == 4
        assert alias['type']['value'] == 848563180
        # scenario() executes pre-hit code through the real branch back to the
        # original direct-hit path. Both enabled and unrelated IDs must reach it.
        for ammo in (123, 3133483038, 2453015274):
            assert q.scenario(ammo=ammo).hits == []
        assert q.scenario(ammo=2369196415).hits == [(11, 3), (12, 3), (13, 3)]
        record('reported config: aliased runtime ammo value, all direct-hit paths reachable, level 45 alone chains')
        mod.config_file(mid, 'src/config.lua', reported.replace('enabled = true', 'enabled = false')); mod.apply()
        without_chain, _ = export('chain-reported-disabled')
        assert without_chain == baseline
        record('reported config with chain disabled restores the entire original projectile program')
        # Zero chance and zero radius compile to a no-op, even with enabled=true.
        for name, config in [
            ('zero chance', enabled.replace('chance_percent = 100', 'chance_percent = 0')),
            ('zero spread', enabled.replace('spread_radius = 7.0', 'spread_radius = 0')),
        ]:
            # Keep existing spell's radius vanilla for the zero-spread profile.
            config = config.replace('spread_radius = 0,    -- Combat sphere', 'spread_radius = 7.0,    -- Combat sphere')
            mod.config_file(mid, 'src/config.lua', config); mod.apply()
            assert 'Applied 0 patches' in log(), log()
            record(name + ' creates no chain program patch')
        for name, config in [
            ('probability over 100', enabled.replace('chance_percent = 100', 'chance_percent = 101')),
            ('fractional jump limit', enabled.replace('max_jumps = 0', 'max_jumps = 1.5')),
            ('overflowing jump limit', enabled.replace('max_jumps = 0', 'max_jumps = 4294967296')),
            ('nonboolean enable', enabled.replace('enabled = true', 'enabled = 1')),
            ('negative chain damage', enabled.replace('damage = 0.5, max_jumps', 'damage = -1, max_jumps')),
        ]:
            mod.restore()
            mod.config_file(mid, 'src/config.lua', config)
            try:
                mod.apply()
            except RuntimeError:
                pass
            else:
                raise AssertionError('Accepted ' + name)
            assert eml.digest(work/'Server/enshrouded_server.kfc') == original
            record('reject ' + name + ' without leaving a patch')
    finally:
        mod.config_file(mid, 'src/config.lua', defaults)
        mod.restore()
        assert eml.digest(work/'Server/enshrouded_server.kfc') == original
    record('default config and exact original index restored')
    (work/'chain-results.json').write_text(json.dumps({
        'version': version, 'checks': results, 'passed': len(results),
        'scope': 'EML integration, static decode and mocked-native bytecode execution; no combat/network certification'
    }, indent=2))


if __name__ == '__main__':
    main()
