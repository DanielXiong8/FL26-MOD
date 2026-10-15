# -*- coding: utf-8 -*-
"""
Track A device capture: adb screencap loop.
Usage:
  python appearance_diff_capture.py start <duration_minutes>
  python appearance_diff_capture.py once <name>
Saves to C:\\FL26_Mod\\logs\\appearance_diff\\
"""
import sys, io, os, subprocess, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
OUT = r'C:\FL26_Mod\logs\appearance_diff'
os.makedirs(OUT, exist_ok=True)

def capture(path):
    r = subprocess.run([ADB, 'exec-out', 'screencap', '-p'], capture_output=True, timeout=30)
    if r.returncode == 0 and len(r.stdout) > 1000:
        with open(path, 'wb') as f:
            f.write(r.stdout)
        return True
    return False

if sys.argv[1] == 'once':
    name = sys.argv[2]
    p = os.path.join(OUT, f'{name}.png')
    print('OK' if capture(p) else 'FAIL', p)
elif sys.argv[1] == 'start':
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 5
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
    n = int(minutes * 60 / interval)
    print(f"capturing {n} frames @ {interval}s ({minutes} min)...")
    for i in range(n):
        p = os.path.join(OUT, f'cap_{i:04d}.png')
        ok = capture(p)
        print(f"  {time.strftime('%H:%M:%S')} cap_{i:04d}: {'OK' if ok else 'FAIL'}", flush=True)
        time.sleep(interval)
    print("capture loop done")
