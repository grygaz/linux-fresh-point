#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only
import os
from pathlib import Path
import shutil
import subprocess
source=Path(__file__).resolve().parent
if os.geteuid()==0:raise SystemExit('Run this installer without sudo.')
data=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))
target=data/'linux-tvarka/app'
target.mkdir(parents=True,exist_ok=True)
# Install language resources before replacing the entry point.
files=['gnu-logo.svg','LICENSE-GNU-ICON.md','LICENSE','NOTICE','about_content.py','i18n.py','translations.json','backend.py','point_store.py','portable.py','portable.sh','PORTABLE.md','apt_backend.py','native_backend.py','system_info.py','terminal_apply.py','cleanup_core.py','style.css','icon.svg','start','NAUDOJIMAS.md','app.py']
for name in files:
 if (source/name).resolve()!=(target/name).resolve():shutil.copy2(source/name,target/name)
shutil.copytree(source/'descriptions',target/'descriptions',dirs_exist_ok=True)
(target/'start').chmod(0o755)
(target/'paleisti.sh').unlink(missing_ok=True)
app_path=str(target/'app.py')
if any(c in app_path for c in '\n\r"`$\\'):raise SystemExit('Unsupported characters in installation path.')
menu=data/'applications'
menu.mkdir(parents=True,exist_ok=True)
(menu/'lt.local.LinuxTvarka.desktop').write_text('[Desktop Entry]\nType=Application\nVersion=1.0\nName=Linux fresh point\nComment=Applications and restore points\nExec=/usr/bin/python3 -I "'+app_path.replace('%','%%')+'"\nIcon='+str(target/'icon.svg')+'\nTerminal=false\nCategories=System;PackageManager;\nStartupNotify=true\n')
if shutil.which('update-desktop-database'):subprocess.run(['update-desktop-database',str(menu)],check=False)
print('Installed: Linux fresh point')
