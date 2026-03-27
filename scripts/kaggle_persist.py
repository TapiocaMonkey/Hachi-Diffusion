# ~ kaggle_persist.py | by ANXETY (modified for Kaggle persistence) ~
"""
Kaggle Persistence Helper
=========================
This script helps you manage the persistent Stable Diffusion installation
on Kaggle. Because Kaggle sessions are ephemeral, the recommended workflow is:

  1. First run:  install everything normally (cells 1-2 of the notebook).
  2. Save output: go to "Data" tab → "Output" → "Save Version" (or run this
                  script with --save to trigger a dataset commit via the API).
  3. Next session: add the saved dataset as an Input dataset in your notebook
                   settings. The restore logic in downloading.py will
                   automatically copy it back from /kaggle/input/<name>/ into
                   /kaggle/working/sd-persistent/ before re-installing.

Usage (inside a notebook cell):
    %run $scripts_dir/kaggle_persist.py --status        # show install status
    %run $scripts_dir/kaggle_persist.py --restore       # manually restore from input
    %run $scripts_dir/kaggle_persist.py --save-info     # print instructions to save
"""

from pathlib import Path
import argparse
import shutil
import sys
import os


PERSISTENT_DIR = Path('/kaggle/working/sd-persistent')
INPUT_GLOB_PATTERN = '/kaggle/input/*/sd-persistent'
FLAT_MARKER_FILES = ['ANXETY', 'venv']   # top-level dirs that identify a flat layout


# ============================= HELPERS =============================

def _find_input_source():
    """Locate a previously saved persistent directory from Kaggle Input datasets."""
    import glob
    # Preferred: /kaggle/input/<dataset>/sd-persistent/
    candidates = glob.glob(INPUT_GLOB_PATTERN)
    if candidates:
        return sorted(candidates)[-1]
    # Fallback: dataset root IS the persistent dir (flat layout)
    for p in sorted(glob.glob('/kaggle/input/*')):
        if any((Path(p) / marker).exists() for marker in FLAT_MARKER_FILES):
            return p
    return None


def cmd_status(args):
    """Print current installation status."""
    print('=== Kaggle Persistent SD Status ===\n')
    print(f'Persistent dir : {PERSISTENT_DIR}')
    print(f'Exists         : {PERSISTENT_DIR.exists()}')
    if PERSISTENT_DIR.exists():
        # Rough size estimate
        total = sum(f.stat().st_size for f in PERSISTENT_DIR.rglob('*') if f.is_file())
        print(f'Disk usage     : {total / 1e9:.2f} GB')
        webui_dirs = [d.name for d in PERSISTENT_DIR.iterdir()
                      if d.is_dir() and d.name not in ('ANXETY', 'venv')]
        print(f'WebUI dirs     : {webui_dirs or "none yet"}')
    src = _find_input_source()
    print(f'\nInput dataset  : {src or "not found — run as first session or add saved output as Input"}')
    print()


def cmd_restore(args):
    """Restore the persistent directory from a Kaggle Input dataset."""
    src = _find_input_source()
    if not src:
        print('⚠️  No input dataset found containing a previous sd-persistent install.')
        print('    → On Kaggle, go to the notebook Settings and add your saved')
        print('      output dataset as an Input dataset, then re-run this cell.')
        sys.exit(1)

    PERSISTENT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'♻️  Restoring from {src} → {PERSISTENT_DIR} …')

    import subprocess
    result = subprocess.run(
        ['rsync', '-a', '--ignore-existing', '--info=progress2',
         f'{src}/', str(PERSISTENT_DIR)],
    )
    if result.returncode == 0:
        print('✅ Restore complete!')
    else:
        print(f'❌ rsync failed with code {result.returncode}')
        sys.exit(result.returncode)


def cmd_save_info(args):
    """Print instructions for saving the current install as a Kaggle Dataset."""
    size_gb = 0.0
    if PERSISTENT_DIR.exists():
        total = sum(f.stat().st_size for f in PERSISTENT_DIR.rglob('*') if f.is_file())
        size_gb = total / 1e9

    print('=== How to Save Your SD Install on Kaggle ===\n')
    print(f'Current install size: {size_gb:.2f} GB')
    print()
    print('Option A — Kaggle UI (easiest):')
    print('  1. In the top-right of the notebook click "Save Version"')
    print('     (or "Save & Run All" for a full commit).')
    print('  2. After the run finishes, go to the notebook → Data tab → Output.')
    print('  3. You will see the output files including sd-persistent/.')
    print('  4. Click "New Dataset" to save the output as a reusable dataset.')
    print('  5. In future sessions, add that dataset as an Input dataset.')
    print('     The restore logic will automatically copy it back.')
    print()
    print('Option B — Kaggle API (from a terminal cell):')
    print('  kaggle datasets version -p /kaggle/working/sd-persistent \\')
    print('      -m "SD persistent update" --dir-mode zip')
    print()
    print('Tip: models are large. You can exclude them from the saved dataset')
    print('and rely on the Download step (cell 2) to re-download only models,')
    print('while keeping the venv and WebUI code persistent.')
    print()


# ============================= MAIN ================================

def main():
    if 'KAGGLE_URL_BASE' not in os.environ:
        print('⚠️  This script is intended for use on Kaggle only.')
        sys.exit(0)

    parser = argparse.ArgumentParser(description='Kaggle SD persistence helper')
    sub = parser.add_subparsers(dest='command')
    sub.add_parser('--status',    help='Show installation status').set_defaults(func=cmd_status)
    sub.add_parser('--restore',   help='Restore from input dataset').set_defaults(func=cmd_restore)
    sub.add_parser('--save-info', help='Print save instructions').set_defaults(func=cmd_save_info)

    # Support both --flag and positional style (%run script.py --status)
    parser.add_argument('--status',    dest='cmd_flag', action='store_const', const='status')
    parser.add_argument('--restore',   dest='cmd_flag', action='store_const', const='restore')
    parser.add_argument('--save-info', dest='cmd_flag', action='store_const', const='save_info')

    args, _ = parser.parse_known_args()

    dispatch = {
        'status':    cmd_status,
        'restore':   cmd_restore,
        'save_info': cmd_save_info,
    }

    fn = dispatch.get(args.cmd_flag) or dispatch.get(getattr(args, 'command', None))
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
