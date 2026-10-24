"""Local HTTP serving and source snapshots shared by experiment runners."""
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

ROOT = Path(__file__).resolve().parents[1]

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
    paths = [ROOT / directory for directory in ('environments/'+game, 'runtime', 'policies/'+game, 'profiles/'+game)]
    paths += [ROOT/'scripts'/f'{game}.py', ROOT/'environments/registry.json']
    for path in paths:
        for p in sorted(path.rglob('*')) if path.is_dir() else [path]:
            if p.is_file()and '__pycache__' not in p.parts:
                rel=str(p.relative_to(ROOT))
                if p.suffix in ('.py','.js','.mjs','.json','.txt','.md','.css','.html','.toml'):
                    target=out/'source_snapshot'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
    if game=='asterix' and recipe.get('provider')=='openai_api':
        for name in ('api_client.py','budget.py'):
            rel='environments/touhou/research/'+name
            target=out/'source_snapshot'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/rel).read_bytes())
    (out/'manifest.json').write_text(json.dumps({'game':game,'recipe':recipe,'mode':mode,'real_time_api_acceptance':False,
        'transport_adapter':{
            'subscription_with_simulated_profile':'native app-server subscription; sampled virtual timing',
            'real_time_subscription':'native app-server subscription; continuously advancing wall clock',
            'realtime_api':'streamed paid API; continuously advancing wall clock',
            'serial_api_profile':'strictly serial paid API on retained inputs; no gameplay actions',
            'claude_with_simulated_profile':'stateless Claude Code CLI; sampled virtual timing',
            'real_time_claude':'stateless Claude Code CLI; continuously advancing wall clock',
            'rules_baseline_with_simulated_profile':'true-board rules heuristic (evaluator-side comparison); sampled virtual timing',
        }.get(mode,'Transport is declared in the recipe and transport-specific run records'),
        'created_at_unix':time.time()},indent=2))
