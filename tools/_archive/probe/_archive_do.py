
# -*- coding: utf-8 -*-
"""Archive one-off research scripts under tools/_archive (never delete)."""
import os, re, shutil, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOOLS = r"D:\桌面宠物\tools"
ARCH  = os.path.join(TOOLS, "_archive")
RES   = os.path.join(ARCH, "research")
PRB   = os.path.join(ARCH, "probe")
for d in (ARCH, RES, PRB):
    os.makedirs(d, exist_ok=True)

RES_PAT = re.compile(r"^(scan_|hunt_|cdp_|trace_|dbg_)|(_sso|_login|_auth|_cred|_account|_quota|_token|_cookie|_api|_asar|_bundle|_platform)", re.I)

KEEP = set("""blink_cols.py blink_diff.py blink_final.py blink_frame.py blink_plan.py blink_strip.py
build_anim_sheet.py build_mate_sheet.py build_stickers.py capture_creds.py check_deps.py diff_anim.py
export_pet.py extract_mate_skill.py eye_cols.py eye_geom.py find_pet_hit.py force_front.py frame_cols.py
grab_window.py grid_parts.py install_mate_pet.py launch_mimo_pet.py make_demo_gif.py make_pet.py
pet_control.py pet_frames.py pet_watchdog.py probe_dbl4.py probe_dbl5.py probe_live_bubble.py
probe_owner.py probe_place.py probe_style.py render_eggs.py restart_mimo.py restore_mimo.py
setup_launcher.py shot_mimo.py verify_installed.py""".split())

names = sorted(n for n in os.listdir(TOOLS) if n.endswith(".py"))
moved_res, moved_prb, kept = [], [], []
for n in names:
    if n.startswith("test_") or n in KEEP:
        kept.append(n); continue
    dst = RES if RES_PAT.match(n) else PRB
    try:
        shutil.move(os.path.join(TOOLS, n), os.path.join(dst, n))
        (moved_res if dst is RES else moved_prb).append(n)
    except Exception as e:
        print("FAIL", n, e)

print("kept=%d  moved_research=%d  moved_probe=%d" % (len(kept), len(moved_res), len(moved_prb)))
print("tools/ .py remaining =", len([n for n in os.listdir(TOOLS) if n.endswith('.py')]))
print("research =", len(os.listdir(RES)), " probe =", len(os.listdir(PRB)))
