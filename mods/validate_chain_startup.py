"""Boot the packaged mod in the marked disposable fixture; no combat claim."""
import argparse
import importlib.util
import json
import secrets
import subprocess
import time
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir',required=True,type=Path)
    work=parser.parse_args().fixture_dir.resolve()
    assert (work/'SHOCK_MOD_TEST_FIXTURE').read_text().strip()=='disposable-shock-mod-test'
    server=work/'Server'
    spec=importlib.util.spec_from_file_location('eml',ROOT/'enshrouded_manager/eml_support.py')
    eml=importlib.util.module_from_spec(spec);spec.loader.exec_module(eml)
    mod=eml.EML(server,work/'state',ROOT/'enshrouded_manager/vendor/eml-v0.2.0/emm.exe')
    source=ROOT/'mods/zat-shock-tuning';mid='zat-shock-tuning'
    version=json.loads((source/'mod.json').read_text())['version']
    package=ROOT/f'dist/mods/Zat-Shock-Tuning-v{version}.zip'
    defaults=(source/'src/config.lua').read_text()
    config_file=server/'enshrouded_server.json';original_config=config_file.read_bytes()
    original_index=eml.digest(server/'enshrouded_server.kfc')
    prefix='validation-living-'+uuid.uuid4().hex[:8]
    log_dir=server/(prefix+'-logs');log_dir.mkdir()
    proc=None
    result={'version':version,'package_sha256':eml.digest(package),'combat_tested':False}
    try:
        mod.enable(True)
        if mid in mod.state()['mods']:mod.change_mod(mid,'remove')
        mod.import_zip(package.read_bytes());mod.change_mod(mid,'enable')
        mod.config_file(mid,'src/config.lua',defaults.replace('enabled = false','enabled = true')
                        .replace('targets_per_spread = 1','targets_per_spread = 3'))
        mod.apply()
        config=json.loads(original_config)
        config.update(name=prefix,ip='127.0.0.1',queryPort=31079,slotCount=2,
                      saveDirectory=str(server/(prefix+'-save')),logDirectory=str(log_dir))
        for group in config.get('userGroups',[]):group['password']=secrets.token_urlsafe(32)
        config_file.write_text(json.dumps(config,indent=2))
        start=time.monotonic()
        with (log_dir/'stdout.log').open('w') as output:
            proc=subprocess.Popen([str(server/'enshrouded_server.exe')],cwd=server,
                                  stdout=output,stderr=subprocess.STDOUT,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            ready=False
            while time.monotonic()-start<45 and proc.poll() is None:
                logs='\n'.join(p.read_text(errors='replace') for p in log_dir.glob('*.log'))
                ready="current='Host_Online'" in logs and 'Switching state from LoadEcsScene to Run' in logs
                if ready:break
                time.sleep(.5)
            result.update(reached_run=ready,alive=proc.poll() is None,
                          elapsed_seconds=round(time.monotonic()-start,1),log=str(log_dir))
            assert ready and proc.poll() is None,'Isolated startup did not reach Run; inspect fixture logs'
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
        config_file.write_bytes(original_config)
        mod.config_file(mid,'src/config.lua',defaults);mod.restore()
        result['restored_original_index']=eml.digest(server/'enshrouded_server.kfc')==original_index
        result['restored_original_server_config']=config_file.read_bytes()==original_config
        (work/'living-chain-startup-result.json').write_text(json.dumps(result,indent=2))
        assert result['restored_original_index'] and result['restored_original_server_config']
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
