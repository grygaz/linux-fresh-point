#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only
"""Dispatch only to the detected host's package manager."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from system_info import detect

if __name__ == '__main__':
    try:
        if len(sys.argv) == 4 and sys.argv[1:3] == ['point-delete', '--id']:
            import point_store
            print(json.dumps({'ok':True,'data':point_store.delete(sys.argv[3])}))
            sys.exit(0)
        system = detect()
        if system['manager'] == 'apt':
            import apt_backend
            original = apt_backend.inventory
            def inventory():
                return original() | {'system':system}
            apt_backend.inventory = inventory
            apt_backend.main()
        else:
            import native_backend
            native_backend.main(system)
    except Exception as exc:
        print(json.dumps({'ok':False,'error':str(exc)}, ensure_ascii=False))
        sys.exit(1)
