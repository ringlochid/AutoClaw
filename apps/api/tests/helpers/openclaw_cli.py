from __future__ import annotations

from pathlib import Path

_FAKE_OPENCLAW_CLI = """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

config_path = Path(os.environ['OPENCLAW_CONFIG_PATH'])
if config_path.is_file():
    payload = json.loads(config_path.read_text(encoding='utf-8'))
else:
    payload = {}

def save() -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

def merge(base, patch):
    if isinstance(base, dict) and isinstance(patch, dict):
        merged = dict(base)
        for key, value in patch.items():
            if value is None:
                merged.pop(key, None)
            elif isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    return patch

args = sys.argv[1:]
if args[:3] == ['agents', 'list', '--json']:
    default_agents = [{'id': 'main', 'default': True}]
    raw_agents = payload.get('agents', {}).get('list') or default_agents
    out = []
    has_default = any(
        isinstance(item, dict) and item.get('default') is True
        for item in raw_agents
    )
    for index, entry in enumerate(raw_agents):
        if not isinstance(entry, dict):
            continue
        agent_id = entry.get('id')
        if not isinstance(agent_id, str) or not agent_id.strip():
            continue
        out.append({
            'id': agent_id.strip(),
            'isDefault': bool(
                entry.get('default') is True or (not has_default and index == 0)
            ),
            'name': entry.get('name'),
            'workspace': entry.get('workspace'),
            'agentDir': entry.get('agentDir'),
        })
    print(json.dumps(out))
    raise SystemExit(0)
if len(args) >= 6 and args[:2] == ['agents', 'add'] and args[3] == '--workspace':
    agent_id = args[2]
    workspace = args[4]
    agents = payload.setdefault('agents', {}).setdefault('list', [])
    agents.append({
        'id': agent_id,
        'name': agent_id,
        'workspace': workspace,
        'agentDir': str(Path(workspace) / '.openclaw-agent'),
    })
    save()
    print(json.dumps({'agentId': agent_id, 'workspace': workspace}))
    raise SystemExit(0)
if len(args) == 4 and args[:2] == ['mcp', 'set']:
    name = args[2]
    value = json.loads(args[3])
    servers = payload.setdefault('mcp', {}).setdefault('servers', {})
    servers[name] = value
    save()
    print(f'Saved MCP server {name}')
    raise SystemExit(0)
if args == ['config', 'patch', '--stdin']:
    payload = merge(payload, json.load(sys.stdin))
    save()
    print('Patched config')
    raise SystemExit(0)
print('unsupported openclaw test command: ' + ' '.join(args), file=sys.stderr)
raise SystemExit(2)
"""


def write_fake_openclaw_cli(path: Path) -> None:
    path.write_text(_FAKE_OPENCLAW_CLI, encoding="utf-8")
    path.chmod(0o755)
