from __future__ import annotations
import argparse
import asyncio
import concurrent.futures as cf
from contextlib import contextmanager
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]

@contextmanager
def serve(directory):
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(directory)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}'
    finally:server.shutdown();server.server_close();thread.join()

def freeze(game,recipe,out, mode="subscription_with_simulated_profile"):
    out.mkdir(parents=True,exist_ok=False)
    sources={}
    for directory in ('environments/'+game,'runtime','policies/'+game,'profiles/'+game):
        for p in sorted((ROOT/directory).rglob('*')):
            if p.is_file()and '__pycache__' not in p.parts:
                rel=str(p.relative_to(ROOT))
                data=p.read_bytes();sources[rel]=hashlib.sha256(data).hexdigest()
                if p.suffix in ('.py','.js','.mjs','.json','.txt','.md','.css','.html','.toml'):
                    target=out/'source_snapshot'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    (out/'manifest.json').write_text(json.dumps({'game':game,'recipe':recipe,'source_sha256':sources,
        'mode':mode,'real_time_api_acceptance':False,
        'transport_adapter':{
            'subscription_with_simulated_profile':'native app-server subscription; sampled virtual timing',
            'real_time_subscription':'native app-server subscription; continuously advancing wall clock',
            'realtime_api':'streamed paid API; continuously advancing wall clock',
            'serial_api_profile':'strictly serial paid API on retained inputs; no gameplay actions',
        }.get(mode,'Transport is declared in the recipe and transport-specific run records'),
        'created_at_unix':time.time()},indent=2))

def rhythm(recipe,out,a):
    from runtime.rhythm import simulate
    return simulate(ROOT,recipe,out,a)

def touhou(recipe,out,a):
    sys.path.insert(0,str(ROOT/'environments/touhou'))
    from research import subscription
    from runtime.subscription import SubscriptionClient
    subscription.SubscriptionClient=SubscriptionClient
    from research.run_episode import run
    config=dict(recipe['args']);config.update(profile=str(ROOT/recipe['profile']),suite=str(ROOT/'vendor'))
    if a.seed is not None:config['seed']=a.seed
    config['browser_executable']=a.browser_executable
    if a.duration is not None:raise ValueError('Touhou acceptance uses a complete game; --duration is not supported')
    with serve(ROOT/'environments/touhou/dist') as url:
        config['url']=url
        run(config,out/'episode')
    summary=json.loads((out/'episode/summary.json').read_text())
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    from runtime.touhou_records import evaluation_record
    evaluation_record(ROOT,out)
    return summary

def asterix(recipe,out,a):
    sys.path.insert(0,str(ROOT/'environments/asterix'))
    from runner import run_recipe
    from runtime.subscription import SubscriptionClient
    os.environ['SOL_QUOTA_STOP_PERCENT']=str(min(int(os.environ.get('SOL_QUOTA_STOP_PERCENT','80')),recipe['args']['quota_stop_percent']))
    return run_recipe(ROOT,recipe,out,a,SubscriptionClient,
        mode='realtime' if a.command=='eval' else 'simulation')

def touhou_realtime(recipe,out,a):
    import getpass
    sys.path.insert(0,str(ROOT/'environments/touhou'))
    from research.run_episode import run
    from research.budget import BudgetLedger
    from runtime.touhou_records import evaluation_record
    config=dict(recipe['args'])
    if config.get('speed')!=1:raise ValueError('Realtime acceptance requires speed=1')
    config.update(profile=str(ROOT/recipe['profile']),suite=str(ROOT/'vendor'),
                  ledger=str(a.ledger.resolve() if a.ledger else out/'ledger.json'),
                  max_calls=a.max_calls,browser_executable=a.browser_executable,
                  budget_limits={'total_limit':str(a.budget_usd),'admission_limit':str(a.budget_usd),
                                 'stage_caps':{k:str(a.budget_usd) for k in ('profile','reprofile','realtime')}})
    if a.seed is not None:config['seed']=a.seed
    ledger=BudgetLedger(config['ledger'],**config['budget_limits']);before=ledger.snapshot()
    if before.get('blocked'):raise RuntimeError('Ledger requires reconciliation before new API calls')
    key=os.environ.get('OPENAI_API_KEY') or getpass.getpass('OpenAI API key (process memory only): ')
    if not key:raise ValueError('A real API credential is required')
    try:
        with serve(ROOT/'environments/touhou/dist') as url:
            config['url']=url
            result=run(config,out/'episode',key)
        (out/'summary.json').write_text(json.dumps(result,indent=2))
        return result
    finally:
        key=None
        record=evaluation_record(ROOT,out,budget_before=before,budget_after=ledger.snapshot())
        m=json.loads((out/'manifest.json').read_text());m['real_time_api_acceptance']=record['passed']
        (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')


def doctor(a):
    import importlib.metadata
    checks={'python':sys.version.split()[0],'node':bool(shutil.which('node')),'codex':os.environ.get('SOL_CODEX_BIN')or shutil.which('codex')}
    for n in (('ale-py','gymnasium','Pillow') if a.game=='asterix' else ('playwright','ale-py','gymnasium','Pillow')):
        checks[n]=importlib.metadata.version(n)
    if a.game in ('asterix','all'):
        sys.path.insert(0,str(ROOT/'environments/asterix'));from simulate_5x import make_env
        env,obs,info,noops=make_env(2);checks['asterix_reset']={'shape':list(obs.shape),'lives':info.get('lives')};env.close()
    if a.game in ('rhythm','touhou','all'):
        from playwright.sync_api import sync_playwright
        with sync_playwright()as p:
            b=p.chromium.launch(headless=True,executable_path=a.browser_executable);checks['chromium']=b.version;b.close()
    if a.auth:
        from runtime.subscription import SubscriptionClient
        c=SubscriptionClient(output=ROOT/'runs/doctor-auth');checks['auth']='chatgpt';checks['quota']=c.quota();c.close()
    print(json.dumps(checks,indent=2))

def main():
    if len(sys.argv)>2 and sys.argv[2] in ('tabletennis','pingpong') and sys.argv[1] in ('simulate','eval','report'):
        raise SystemExit(subprocess.call([sys.executable,str(ROOT/'scripts/tabletennis.py'),sys.argv[1],*sys.argv[3:]]))
    if len(sys.argv)>2 and sys.argv[2]=='badminton' and sys.argv[1] in ('simulate','eval','preflight','audit','report','diagnose','profile'):
        raise SystemExit(subprocess.call([sys.executable,str(ROOT/'scripts/badminton.py'),sys.argv[1],*sys.argv[3:]]))
    # Racing retains its measured driver/transport, with an explicit real API path.
    if len(sys.argv)>2 and sys.argv[2]=='racing' and sys.argv[1] in ('simulate','eval','profile','preflight','record','budget'):
        raise SystemExit(subprocess.call([sys.executable,str(ROOT/'scripts/racing.py'),sys.argv[1],*sys.argv[3:]]))
    p=argparse.ArgumentParser(epilog='Racing: sol simulate racing, sol eval racing, sol profile racing; see docs/racing.md. Badminton: sol simulate badminton, sol eval badminton, sol preflight badminton, sol audit badminton, sol report badminton; see docs/badminton.md. PingPong: sol simulate pingpong, sol eval pingpong, sol report pingpong; see docs/tabletennis.md.');sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('doctor');d.add_argument('--game',choices=['all','rhythm','touhou','asterix'],default='all');d.add_argument('--auth',action='store_true');d.add_argument('--browser-executable')
    e=sub.add_parser('simulate');e.add_argument('game',choices=['rhythm','touhou','asterix']);e.add_argument('--output',type=Path);e.add_argument('--seed',type=int);e.add_argument('--duration',type=float);e.add_argument('--browser-executable');e.add_argument('--recipe',type=Path)
    v=sub.add_parser('eval',help='Continuous evaluation: Asterix subscription or Touhou/Rhythm API (explicit budget)')
    v.add_argument('game',choices=['touhou','asterix','rhythm']);v.add_argument('--output',type=Path);v.add_argument('--seed',type=int)
    v.add_argument('--recipe',type=Path);v.add_argument('--browser-executable');v.add_argument('--budget-usd',help='Required for paid API evaluation')
    v.add_argument('--max-calls',type=int,default=100);v.add_argument('--ledger',type=Path)
    v.add_argument('--duration',type=float);v.add_argument('--audio',type=Path,help='Optional local audio; Rhythm defaults to bundled17s preview')
    r=sub.add_parser('record',help='Append an immutable evaluation record to a chosen registry')
    r.add_argument('--decision',choices=['retain','reject','diagnostic']);r.add_argument('--note');r.add_argument('run',type=Path);r.add_argument('--registry',type=Path,default=ROOT/'artifacts/touhou/evaluations.jsonl')
    c=sub.add_parser('profile',help='Strictly serial API profiling of retained unique observations')
    c.add_argument('game',choices=['touhou','rhythm']);c.add_argument('--episode',type=Path,required=True)
    c.add_argument('--output',type=Path);c.add_argument('--budget-usd',required=True);c.add_argument('--max-calls',type=int,default=21);c.add_argument('--ledger',type=Path)
    a=p.parse_args()
    if a.command=='record':
        manifest=json.loads((a.run/'manifest.json').read_text())
        if manifest['game']=='rhythm':
            if a.decision is not None or a.note is not None:
                if a.decision is None or a.note is None:p.error('Supply both --decision and --note')
                from runtime.evaluation import assess
                print(json.dumps(assess(a.run,a.decision,a.note),indent=2))
            else:
                from runtime.rhythm import append_record
                registry=a.registry if a.registry!=ROOT/'artifacts/touhou/evaluations.jsonl' else ROOT/'artifacts/rhythm/evaluations.jsonl'
                print(json.dumps({'appended':append_record(a.run,registry),'registry':str(registry)}))
            return
        if manifest['game']=='asterix':
            if a.decision is None or a.note is None:p.error('Asterix assessments require --decision and --note')
            from runtime.evaluation import assess
            print(json.dumps(assess(a.run,a.decision,a.note),indent=2));return
        if a.decision is not None or a.note is not None:p.error('--decision and --note apply to Asterix/Rhythm assessments')
        from runtime.touhou_records import append_record
        print(json.dumps({'appended':append_record(a.run,a.registry),'registry':str(a.registry)}));return
    if a.command in ('eval','profile') and a.game in ('touhou','rhythm'):
        from decimal import Decimal,InvalidOperation
        if a.budget_usd is None:p.error('--budget-usd is required for paid API evaluation')
        try:a.budget_usd=Decimal(a.budget_usd)
        except InvalidOperation:p.error('--budget-usd must be a finite positive decimal')
        if not a.budget_usd.is_finite() or a.budget_usd<=0 or a.max_calls<1:p.error('Budget and max-calls must be positive')
    if a.command=='profile' and a.game=='rhythm':
        from runtime.rhythm import profile
        print(json.dumps(profile(ROOT,a),indent=2));return
    if a.command=='profile':
        from runtime.touhou_profile import profile
        profile(ROOT,a)
        return
    if a.command=='doctor':return doctor(a)
    if a.duration is not None and (not math.isfinite(a.duration) or a.duration<=0 or a.game=='asterix' and round(a.duration*60)<1):
        p.error('--duration must be finite and positive')
    recipe=json.loads((a.recipe or ROOT/'recipes'/(f'{a.game}'+('-realtime.json' if a.command=='eval' and a.game=='touhou' else '.json'))).read_text())
    out=(a.output or ROOT/'runs'/f'{a.game}-{time.strftime("%Y%m%dT%H%M%S")}').resolve()
    expected=('api','realtime') if a.command=='eval' else ('subscription','sim')
    if a.game=='touhou' and (recipe['args'].get('provider'),recipe['args'].get('mode'))!=expected:
        p.error('Recipe provider/mode must match the explicitly selected command')
    freeze(a.game,recipe,out,mode=('realtime_api' if a.game in ('touhou','rhythm') else 'real_time_subscription') if a.command=='eval' else 'subscription_with_simulated_profile')
    (out/'transport').mkdir()
    os.environ['SOL_NATIVE_LOG_ROOT']=str(out/'transport')
    try:
        if a.command=='eval' and a.game=='rhythm':
            from runtime.rhythm import evaluate
            result=evaluate(ROOT,recipe,out,a)
        else:result=touhou_realtime(recipe,out,a) if a.command=='eval' and a.game=='touhou' else globals()[a.game](recipe,out,a)
    except BaseException as exc:
        (out/'failure.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc)},indent=2));raise
    finally:
        from runtime.evaluation import record_run
        record_run(out)
    display=result
    if a.game=='rhythm' and a.command=='eval':display={k:v for k,v in result.items() if k in ('complete','passed','native_clock_drift_s','result','requests','errors')}
    print(json.dumps({'output':str(out),'result':display},indent=2))

if __name__=='__main__':main()
