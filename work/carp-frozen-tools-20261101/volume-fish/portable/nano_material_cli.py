"""Use the Foundry CLI with isolated Nano Banana2 material-reference settings.

Only process-local config changes; credentials stay in the normal provider store.
Briefs within a fish experiment use their own directory, never the game root.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'cli'))
import gamefactory
import workflow_cmds

original_load = gamefactory.load_config
original_paths = workflow_cmds.default_paths_for_brief


def load():
    config = original_load()
    config['image'] = dict(config.get('image', {}), provider='apilio',
        use_text_provider=False, model='gemini-3.1-flash-image',
        api_base='https://api.apilio.ai/v1')
    return config


def paths(brief_path, **kwargs):
    brief = Path(brief_path).resolve()
    if not brief.is_relative_to(ROOT / 'projects/fishing-2d/experiments'):
        return original_paths(brief_path, **kwargs)
    folder = brief.parent
    return dict(project_root=folder, brief=brief, output_dir=folder/'output',
        plans_dir=folder/'plans', godot_project=folder/'game',
        manifest=folder/'pipeline/manifest.json', progress=folder/'progress.json',
        production=folder/'production.json', isolated=True)


gamefactory.load_config = load
workflow_cmds.default_paths_for_brief = paths

if __name__ == '__main__':
    gamefactory.cli()
