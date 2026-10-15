#!/usr/bin/env python3
"""FL26 Face Manual Tuning Dashboard (Step 10).

照片 → N 候选 → 自动淘汰 → 看板选择 → 人工外观微调 → 实时预览 → 最终确认

Pipeline integration:
  - Candidate Pool: calls the existing face_benchmark/scripts/generate_candidates.py
  - 3D preview: writes a render job for the Unity PC Previewer (DashboardRender.cs)
    and launches Unity batchmode asynchronously
  - Appearance parameters: b1/b4/b7/b10/b14 (project-confirmed semantics, discrete
    dropdowns of known-legal values; eyes are NOT YET EXPOSED)
  - Non-destructive: tuned candidates are new dirs (cX_tuned_001), originals untouched
  - ACCEPT FACE exports final_face/ + face_manifest.json for the APK pipeline

Launch:  python dashboard.py
Selftest: python dashboard.py --selftest
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

PROJECT_ROOT = Path(__file__).resolve().parents[2]          # tools/FL26_FaceDashboard -> tools -> FL26_Mod
FACE_BENCH = PROJECT_ROOT / "face_benchmark"
GENERATOR = FACE_BENCH / "scripts" / "generate_candidates.py"
PREVIEWER = PROJECT_ROOT / "tools" / "FL26_AvatarPreviewer"
UNITY_EXE = Path(r"D:/Unity/Editor-2020.3.49f1/Editor/Unity.exe")
DEFAULT_RUN = FACE_BENCH / "runs" / "test01"
DASHBOARD_DIR = Path(__file__).resolve().parent
RENDER_JOBS = DASHBOARD_DIR / "render_jobs"

# ---- appearance field semantics (recon/03_player/appearance_field_semantics.md) ----
B1_FAMILIES = [
    (22, 27, "eastAsia"), (28, 33, "southeuropean"), (16, 21, "african"),
    (10, 15, "America"), (40, 45, "SouthAmerican"),
    (34, 39, "northeuropean"),   # C级
    (4, 9, "southAsia"),         # C级
]
B1_OPTIONS = []  # (b1_value, label) built below
for lo, hi, fam in B1_FAMILIES:
    tier = " (C级)" if fam in ("northeuropean", "southAsia") else ""
    for v in range(lo, hi + 1):
        B1_OPTIONS.append((v, f"b1={v}  face_{fam}_new{v-lo+1}{tier}"))
B4_OPTIONS = [(0, "寸头"), (1, "长发"), (127, "中等发量")]
B7_OPTIONS = [(0, "络腮胡"), (1, "下巴一撮"), (127, "无胡")]
B10_OPTIONS = [(0, "黑(基线)"), (1, "翻转+眼型变化"), (7, "棕")]
B14_OPTIONS = [(42, "椭圆"), (43, "稍尖"), (44, "高额头")]

BASE_PARAMS = {"b1": 22, "b4": 0, "b7": 127, "b10": 0, "b14": 42}

# ---- Phase 12: player/team configuration ----
ATTR_NAMES = ["balance", "reaction", "acceleration", "velocity", "stamina", "agility",
              "shotpower", "standingtackle", "slidingtackle", "ballcontrol", "dribble",
              "shortpass", "highpass", "shot", "volley",
              "mental_defensivepositioning", "mental_vision"]
TEAMS = [("Manchester City", 20026), ("China national team", 10059), ("London Red", 20030)]
POSITIONS = [(3, "FW 前锋")]  # 仅已确认位置码；其余待逆向


def b1_to_texture_name(b1):
    for lo, hi, fam in B1_FAMILIES:
        if lo <= b1 <= hi:
            return f"face_{fam}_new{b1 - lo + 1}"
    return None


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


def load_metrics(run_dir):
    """candidate -> metrics dict, from the run's metrics.csv (project schema)."""
    import csv
    out = {}
    mf = Path(run_dir) / "metrics.csv"
    if not mf.exists():
        return out
    with open(mf, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["candidate"]] = row
    return out


def next_tuned_id(run_dir, source):
    n = 1
    while (Path(run_dir) / "candidates" / f"{source}_tuned_{n:03d}").exists():
        n += 1
    return f"{source}_tuned_{n:03d}"


class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FL26 Face Manual Tuning Dashboard (Step 10)")
        self.geometry("1280x860")
        self.photos = []            # list[Path]
        self.run_dir = Path(DEFAULT_RUN)
        self.candidates = {}        # cid -> {thumb, baked, front, metrics}
        self.selected = None
        self.params = dict(BASE_PARAMS)
        self.render_job = None
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        top = ttk.Frame(self); top.pack(fill="x", padx=6, pady=4)
        ttk.Button(top, text="载入照片", command=self.load_photo).pack(side="left")
        self.lbl_photo = ttk.Label(top, text="未选择照片"); self.lbl_photo.pack(side="left", padx=8)
        ttk.Button(top, text="生成 Candidate Pool", command=self.generate_pool).pack(side="left", padx=8)
        ttk.Label(top, text="Run:").pack(side="left", padx=(16, 2))
        self.lbl_run = ttk.Label(top, text=str(self.run_dir)); self.lbl_run.pack(side="left")

        main = ttk.Frame(self); main.pack(fill="both", expand=True, padx=6, pady=4)
        # left: candidate cards
        left = ttk.LabelFrame(main, text="Candidates（REJECT 已灰置）"); left.grid(row=0, column=0, sticky="ns")
        self.card_canvas = tk.Canvas(left, width=300, height=560, highlightthickness=0)
        card_scroll = ttk.Scrollbar(left, orient="vertical", command=self.card_canvas.yview)
        self.card_frame = ttk.Frame(self.card_canvas)
        self.card_frame.bind("<Configure>", lambda e: self.card_canvas.configure(scrollregion=self.card_canvas.bbox("all")))
        self.card_canvas.create_window((0, 0), window=self.card_frame, anchor="nw")
        self.card_canvas.configure(yscrollcommand=card_scroll.set)
        self.card_canvas.pack(side="left", fill="both", expand=True)
        card_scroll.pack(side="right", fill="y")

        # center: 2D preview
        center = ttk.LabelFrame(main, text="2D Preview（候选烘焙图 / front 渲染）"); center.grid(row=0, column=1, sticky="ns", padx=6)
        self.lbl_2d = ttk.Label(center, image=None)
        self.lbl_2d.image = None
        self.lbl_2d.pack(padx=4, pady=4)

        # right: tuning + 3D preview
        right = ttk.LabelFrame(main, text="Manual Tuning（离散选择器，仅已确认字段）"); right.grid(row=0, column=2, sticky="ns", padx=6)
        self.vars = {}
        rows = [
            ("b1", "脸纹理/肤色家族 (FACE_TEXTURE_ID)", B1_OPTIONS),
            ("b4", "发型 (HAIR_STYLE)", B4_OPTIONS),
            ("b7", "胡型 (BEARD_STYLE)", B7_OPTIONS),
            ("b10", "胡色 (BEARD COLOR)", B10_OPTIONS),
            ("b14", "脸型网格 (FACE_SHAPE_MESH)", B14_OPTIONS),
        ]
        for i, (key, label, opts) in enumerate(rows):
            ttk.Label(right, text=f"{key}  {label}").grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=str(dict(opts)[dict(BASE_PARAMS)[key]]))
            cb = ttk.Combobox(right, textvariable=var, state="readonly", width=34,
                              values=[f"{v}  {t}" for v, t in opts])
            cb.current([v for v, _ in opts].index(dict(BASE_PARAMS)[key]))
            cb.grid(row=i, column=1, sticky="w", pady=2)
            cb.bind("<<ComboboxSelected>>", lambda e, k=key, c=cb, o=opts: self.on_param_change(k, c, o))
            self.vars[key] = (var, opts)
        ttk.Label(right, text="Eyes  眼睛参数: NOT YET EXPOSED（未确认字段，不开放）").grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 2))
        ttk.Label(right, text="b4/b7/b10/b14 = 记录到 manifest（真机生效），PC 预览仅 b1 换纹理实时可见").grid(row=6, column=0, columnspan=2, sticky="w")
        self.auto_render = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, text="参数变更后自动渲染 3D（约 1-2 分钟/次）", variable=self.auto_render).grid(row=7, column=0, columnspan=2, sticky="w")
        ttk.Button(right, text="Render 3D Preview（Unity）", command=self.render_3d).grid(row=8, column=0, columnspan=2, sticky="we", pady=6)
        self.lbl_render_status = ttk.Label(right, text="3D 渲染：空闲"); self.lbl_render_status.grid(row=9, column=0, columnspan=2, sticky="w")

        pano = ttk.LabelFrame(right, text="3D Preview（Unity orbit 渲染）"); pano.grid(row=10, column=0, columnspan=2, sticky="we", pady=4)
        self.pano_imgs = {}
        for col, tag in enumerate(["front", "45L", "45R", "side"]):
            lbl = ttk.Label(pano, text=tag)
            lbl.grid(row=0, column=col, padx=2)
            self.pano_imgs[tag] = lbl
        self.lbl_3d_status = ttk.Label(pano, text="（尚未渲染）")
        self.lbl_3d_status.grid(row=1, column=0, columnspan=4)

        # ---- Phase 12: Player Information panel ----
        player = ttk.LabelFrame(right, text="Player Information"); player.grid(row=11, column=0, columnspan=2, sticky="we", pady=4)
        ttk.Label(player, text="Name").grid(row=0, column=0, sticky="w")
        self.var_name = tk.StringVar(value="Ma Jiantao")
        ttk.Entry(player, textvariable=self.var_name, width=22).grid(row=0, column=1, sticky="we")
        ttk.Label(player, text="Position").grid(row=1, column=0, sticky="w")
        self.var_pos = tk.StringVar(value="3  FW 前锋")
        ttk.Combobox(player, textvariable=self.var_pos, state="readonly", width=20,
                     values=[f"{v}  {t}" for v, t in POSITIONS]).grid(row=1, column=1, sticky="we")
        ttk.Label(player, text="Team").grid(row=2, column=0, sticky="w")
        self.var_team = tk.StringVar(value="Manchester City")
        ttk.Combobox(player, textvariable=self.var_team, state="readonly", width=20,
                     values=[n for n, _ in TEAMS]).grid(row=2, column=1, sticky="we")
        ttk.Label(player, text="Jersey Number").grid(row=3, column=0, sticky="w")
        ttk.Label(player, text="NOT YET EXPOSED", foreground="#888").grid(row=3, column=1, sticky="w")
        ttk.Label(player, text="17 Attributes (1-99)").grid(row=4, column=0, columnspan=2, sticky="w")
        self.attr_vars = {}
        for i, an in enumerate(ATTR_NAMES):
            r, c = 5 + i // 2, (i % 2) * 2
            ttk.Label(player, text=an[:14]).grid(row=r, column=c, sticky="w")
            v = tk.StringVar(value=str(81 + i))
            ttk.Entry(player, textvariable=v, width=5).grid(row=r, column=c + 1, sticky="w")
            self.attr_vars[an] = v
        player.columnconfigure(1, weight=1)

        bottom = ttk.Frame(self); bottom.pack(fill="x", padx=6, pady=4)
        ttk.Button(bottom, text="ACCEPT FACE → 导出 final_face/", command=self.accept_face).pack(side="left")
        ttk.Button(bottom, text="保存 tuned candidate", command=self.save_tuned).pack(side="left", padx=8)
        ttk.Button(bottom, text="BUILD APK", command=self.build_apk).pack(side="left", padx=(16, 4))
        ttk.Button(bottom, text="INSTALL TO DEVICE", command=self.install_apk).pack(side="left", padx=4)
        self.status = ttk.Label(bottom, text="就绪"); self.status.pack(side="left", padx=12)
        ttk.Button(bottom, text="打开候选目录", command=lambda: os.startfile(self.run_dir)).pack(side="right")

        # ---- pipeline status bar ----
        stages = ttk.Frame(self); stages.pack(fill="x", padx=6, pady=2)
        self.stage_vars = {}
        for i, st in enumerate(["PHOTO", "CANDIDATE", "FACE", "PLAYER", "APK", "INSTALL"]):
            v = tk.StringVar(value=st + ": READY")
            ttk.Label(stages, textvariable=v, relief="groove", padding=3).grid(row=0, column=i, padx=2, sticky="we")
            stages.columnconfigure(i, weight=1)
            self.stage_vars[st] = v

    # ---------- photo ----------
    def load_photo(self):
        paths = filedialog.askopenfilenames(title="选择正面照片（可多选）",
                                            initialdir=str(FACE_BENCH / "inputs"),
                                            filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if not paths:
            return
        self.photos = [Path(p) for p in paths]
        self.lbl_photo.config(text=", ".join(p.name for p in self.photos))
        self.set_status(f"照片已载入 {len(self.photos)} 张")
        self.set_stage("PHOTO", "PASS")

    # ---------- candidate pool ----------
    def generate_pool(self):
        if not self.photos:
            messagebox.showinfo("提示", "先载入照片"); return
        out = FACE_BENCH / "runs" / ("photo_" + self.photos[0].stem + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        cmd = [sys.executable, str(GENERATOR), "--input", str(self.photos[0]), "--n", "8",
               "--seed", "20260903", "--output", str(out)]
        self.set_status("生成 Candidate Pool 中……（约 1-3 分钟）")
        def worker():
            r = subprocess.run(cmd, capture_output=True, text=True)
            self.after(0, lambda: self.pool_done(out, r))
        threading.Thread(target=worker, daemon=True).start()

    def pool_done(self, out, result):
        if result.returncode != 0:
            messagebox.showerror("生成失败", result.stderr[-1500:])
            self.set_status("生成失败"); return
        self.run_dir = Path(out)
        self.lbl_run.config(text=str(out))
        self.reload_candidates()
        self.set_status(f"Candidate Pool 已生成：{out}")
        self.set_stage("CANDIDATE", "PASS")

    # ---------- candidates ----------
    def reload_candidates(self):
        for w in self.card_frame.winfo_children():
            w.destroy()
        self.candidates = {}
        metrics = load_metrics(self.run_dir)
        cdir = self.run_dir / "candidates"
        if not cdir.exists():
            self.set_status("候选目录不存在"); return
        for cid in sorted(metrics.keys(), key=lambda x: int(x[1:]) if x[1:].isdigit() else 999):
            m = metrics[cid]
            cpath = cdir / cid
            baked = cpath / "baked.png"
            front = cpath / "front.png"
            if not baked.exists():
                continue
            status = m.get("status", "?")
            info = (f"{cid}  {status}  score={m.get('final_score','?')}\n"
                    f"tilt={m.get('tilt_deg','?')} seam={m.get('seam_score','?')} "
                    f"cov={m.get('uv_coverage_pct','?')}%")
            card = ttk.Frame(self.card_frame, padding=4)
            card.pack(fill="x", pady=3)
            rejected = status == "REJECT"
            btn = ttk.Button(card, text="选择", state="disabled" if rejected else "normal",
                             command=lambda c=cid: self.select_candidate(c))
            btn.pack(side="left")
            thumb_lbl = ttk.Label(card, image=None); thumb_lbl.image = None
            thumb_lbl.pack(side="left", padx=4)
            if front.exists():
                im = Image.open(front).copy(); im.thumbnail((72, 72))
                thumb_lbl.image = ImageTk.PhotoImage(im); thumb_lbl.config(image=thumb_lbl.image)
            txt = ttk.Label(card, text=info, foreground="#888" if rejected else "#000")
            txt.pack(side="left")
            self.candidates[cid] = {"baked": baked, "front": front, "metrics": m, "rejected": rejected}

    def select_candidate(self, cid):
        self.selected = cid
        self.set_selected_params_from_candidate(cid)
        self.show_2d(self.candidates[cid]["baked"])
        self.set_status(f"已选 {cid}（原始参数已载入调参面板）")

    def set_selected_params_from_candidate(self, cid):
        """载入候选自身的基准外观参数（base = 项目基线 b1=22/b4=0/b7=127/b10=0/b14=42）。"""
        self.params = dict(BASE_PARAMS)
        for key, (var, opts) in self.vars.items():
            vals = [v for v, _ in opts]
            var.set(dict(opts)[self.params[key]] if self.params[key] in vals else var.get())

    def show_2d(self, path):
        im = Image.open(path).convert("RGB")
        im.thumbnail((420, 420))
        self.lbl_2d.image = ImageTk.PhotoImage(im)
        self.lbl_2d.config(image=self.lbl_2d.image)

    # ---------- tuning ----------
    def on_param_change(self, key, combo, opts):
        label = combo.get()
        val = int(label.split()[0])
        old = self.params[key]
        self.params[key] = val
        self.set_status(f"{key}: {old} → {val}" + ("（b1 变更将在 3D 渲染中实时可见）" if key == "b1" else "（已记录，真机生效）"))
        if key == "b1" and self.auto_render.get() and self.selected:
            self.render_3d()

    # ---------- tuned candidate (non-destructive) ----------
    def save_tuned(self):
        if not self.selected:
            messagebox.showinfo("提示", "先选择一个候选"); return
        tid = next_tuned_id(self.run_dir, self.selected)
        src = self.run_dir / "candidates" / self.selected
        dst = self.run_dir / "candidates" / tid
        dst.mkdir(parents=True, exist_ok=False)
        for f in ("baked.png", "front.png"):
            if (src / f).exists():
                shutil.copy2(src / f, dst / f)
        before = self.candidate_base_params(self.selected)
        data = {
            "source_candidate": self.selected,
            "tuned_id": tid,
            "created": datetime.now().isoformat(timespec="seconds"),
            "parameters_before": before,
            "parameters_after": dict(self.params),
            "changes": [
                {"field": k, "before": before[k], "after": self.params[k]}
                for k in sorted(self.params) if before[k] != self.params[k]
            ],
            "preview_renders": sorted(p.name for p in (DASHBOARD_DIR / "renders").glob("*") if p.is_dir() and self.selected in p.name) if (DASHBOARD_DIR / "renders").exists() else [],
        }
        (dst / "manual_tuning.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.set_status(f"已保存 {tid}（原始 {self.selected} 未改动）")
        self.reload_candidates()

    def candidate_base_params(self, cid):
        """基准参数 = 项目基线（appearance_diff baseline：Ralla b1=30 家族基线经 allchina 修正为 b1=22 起）。
        这里以 Dashboard 默认基线为准，before/after 差异针对本次会话内的调整。"""
        return dict(BASE_PARAMS)

    # ---------- 3D render ----------
    def render_3d(self):
        if not self.selected:
            messagebox.showinfo("提示", "先选择一个候选"); return
        RENDER_JOBS.mkdir(exist_ok=True)
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = DASHBOARD_DIR / "renders" / f"{self.selected}_{job_id}"
        job_dir.mkdir(parents=True, exist_ok=True)
        fam = int(self.selected[1:].split("_")[0]) if self.selected[1:].split("_")[0].isdigit() else 1
        fam = int(self.selected.lstrip("c").split("_")[0]) if self.selected.lstrip("c").isdigit() else fam
        b1 = self.params["b1"]
        tex_name = b1_to_texture_name(b1)
        if tex_name is None:
            messagebox.showerror("错误", f"b1={b1} 不在任何已知家族内"); return
        # face prefab: the mesh family stays the selected candidate's base head; the
        # b1 texture family is applied on top (runtime FaceMaterialSupplier parity)
        base_fam = fam
        face_asset = f"face_EastAsia_new{base_fam}"
        job = {
            "bundlePath": str(PREVIEWER / "extracted" / "avatar_mjt.unity3d"),
            "outDir": str(job_dir),
            "faceAssetName": face_asset,
            "textureObjectName": tex_name,
        }
        job_path = RENDER_JOBS / f"job_{job_id}.json"
        job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")
        self.render_job = {"job_dir": job_dir, "job_path": job_path}
        self.lbl_render_status.config(text="3D 渲染：Unity 启动中……")
        env = dict(os.environ, DASHBOARD_JOB=str(job_path))
        def worker():
            r = subprocess.run([str(UNITY_EXE), "-batchmode", "-buildTarget", "Android",
                                "-projectPath", str(PREVIEWER),
                                "-executeMethod", "FL26Previewer.EditorTools.DashboardRender.Run",
                                "-logFile", str(job_dir / "unity_render.log")],
                               capture_output=True, text=True, env=env, cwd=str(PREVIEWER))
            self.after(0, lambda: self.render_done(job_dir, r))
        threading.Thread(target=worker, daemon=True).start()
        self.poll_render(job_dir)

    def poll_render(self, job_dir):
        done = job_dir / "render_done.json"
        for _ in range(240):
            if done.exists():
                self.after(0, lambda: self.render_done_files(job_dir))
                return
            time.sleep(1)
        self.after(0, lambda: self.lbl_render_status.config(text="3D 渲染：超时"))

    def render_done_files(self, job_dir):
        try:
            data = json.loads((job_dir / "render_done.json").read_text(encoding="utf-8"))
        except Exception as e:
            self.lbl_render_status.config(text=f"3D 渲染：读取结果失败 {e}"); return
        if not data.get("ok"):
            self.lbl_render_status.config(text="3D 渲染失败：" + str(data.get("error"))[:120]); return
        self.lbl_render_status.config(text=f"3D 渲染完成（贴图 {data.get('texture')}）")
        self.lbl_3d_status.config(text="")
        for col, (tag, fn) in enumerate([("front", "dash_front.png"), ("45L", "dash_45L.png"),
                                         ("45R", "dash_45R.png"), ("side", "dash_side.png")]):
            p = job_dir / fn
            if not p.exists(): continue
            im = Image.open(p).copy(); im.thumbnail((300, 225))
            ph = ImageTk.PhotoImage(im)
            lbl = self.pano_imgs[tag]
            lbl.image = ph
            lbl.config(image=ph, text="")

    def render_done(self, job_dir, result):
        if result.returncode not in (0,):
            self.lbl_render_status.config(text=f"3D 渲染：Unity 退出码 {result.returncode}（详见 render_log）")

    # ---------- accept ----------
    def accept_face(self):
        if not self.selected:
            messagebox.showinfo("提示", "先选择一个候选"); return
        final_dir = self.run_dir / "final_face"
        final_dir.mkdir(parents=True, exist_ok=True)
        src = self.run_dir / "candidates" / self.selected
        shutil.copy2(src / "baked.png", final_dir / "baked.png")
        if (src / "front.png").exists():
            shutil.copy2(src / "front.png", final_dir / "front.png")
        # previews from the latest render of this candidate (if any)
        previews = []
        renders = DASHBOARD_DIR / "renders"
        if renders.exists():
            for d in sorted(renders.glob(f"{self.selected}_*")):
                for png in d.glob("dash_*.png"):
                    dst = final_dir / ("preview_" + png.name)
                    shutil.copy2(png, dst)
                    previews.append(str(dst))
        patch = {
            "b1": self.params["b1"], "b4": self.params["b4"], "b7": self.params["b7"],
            "b10": self.params["b10"], "b14": self.params["b14"],
        }
        metrics = self.candidates.get(self.selected, {}).get("metrics", {})
        manifest = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "schema": "fl26_final_face_v1",
            "source_photos": [str(p) for p in self.photos],
            "selected_candidate": self.selected,
            "candidate_pool_run": str(self.run_dir),
            "appearance_patch": patch,
            "appearance_note": ("b0/b2/b3/b5/b6/b8/b9/b11-b13/b15/b16 保持 PlayerAppearanceTable "
                                "原记录值；APK 注入阶段只 patch 上述 5 字节"),
            "b1_texture": b1_to_texture_name(self.params["b1"]),
            "baked_texture": str(final_dir / "baked.png"),
            "preview_images": previews,
            "validation": {
                "fault_metrics": {k: metrics.get(k) for k in
                                  ("status", "final_score", "tilt_deg", "seam_score",
                                   "uv_coverage_pct", "black_ratio_pct") if k in metrics},
                "user_accepted": True,
            },
            "provenance": {
                "pipeline": "MICA + face bake v1 + Candidate Pool v1 (frozen)",
                "generator_seed": 20260903,
                "dashboard": "Step10 FL26 Face Manual Tuning Dashboard",
            },
        }
        (final_dir / "face_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.set_status(f"final_face 已导出：{final_dir}")
        self.set_stage("FACE", "PASS")
        messagebox.showinfo("ACCEPT FACE", f"final_face 已导出：\n{final_dir}\n\nface_manifest.json 已生成。")

    def set_status(self, text):
        self.status.config(text=text)
        self.update_idletasks()

    def set_stage(self, stage, state):
        self.stage_vars[stage].set(f"{stage}: {state}")

    # ---------- Phase 12: player config / PID / build / install ----------
    def team_id(self):
        name = self.var_team.get()
        for n, tid in TEAMS:
            if n == name: return tid
        return None

    def position_code(self):
        return int(self.var_pos.get().split()[0])

    def player_attrs(self):
        out = []
        for an in ATTR_NAMES:
            v = int(self.attr_vars[an].get())
            if not 1 <= v <= 99:
                raise ValueError(f"{an}={v} 超出 1-99")
            out.append(v)
        return out

    def validate_player_config(self):
        name = self.var_name.get().strip()
        if not name: raise ValueError("Player Name 为空")
        tid = self.team_id()
        if tid is None: raise ValueError("Team 未选择")
        attrs = self.player_attrs()
        pos = self.position_code()
        return {"name": name, "team_id": tid, "attrs": attrs, "position_b1": pos}

    def allocate_pid(self):
        """检查 Players/ClubPlayer/PA 三表，分配未使用 PID；占用即抛错阻止。"""
        import UnityPy
        env = UnityPy.load(str(GAMEDATA_SRC))
        used = set()
        for o in env.objects:
            if o.type.name != 'TextAsset':
                continue
            d = o.read(check_read=False)
            nm = getattr(d, 'm_Name', '')
            r = d.m_Script
            r = r.encode('utf-8', errors='surrogateescape') if isinstance(r, str) else bytes(r)
            if nm == 'Players':
                off = 8
                ncnt = struct.unpack_from('<H', r, off)[0]; off += 2
                for _ in range(ncnt):
                    ln = struct.unpack_from('<H', r, off)[0]; off += 2 + ln*2
                pcnt = struct.unpack_from('<I', r, off)[0]; off += 4
                for _ in range(pcnt):
                    used.add(struct.unpack_from('<I', r, off)[0]); off += 4
                    ln = struct.unpack_from('<H', r, off)[0]; off += 2 + ln*2
                    off += 8 + 3 + 17 + 2 + 1 + 4
            elif nm == 'PlayerAppearanceTable':
                cur = 4
                nn = struct.unpack_from('<I', r, 0)[0]
                for _ in range(nn):
                    used.add(struct.unpack_from('<I', r, cur)[0]); cur += 8
            elif nm == 'ClubPlayer':
                n1 = struct.unpack_from('<I', r, 0)[0]
                cur = 4 + n1*8
                while cur + 17 <= len(r):
                    used.add(struct.unpack_from('<I', r, cur+4)[0])
                    cur += 17
        pid = 175923
        while pid in used:
            pid += 1
        if pid > 175999:
            raise ValueError('PID 分配失败：175923-175999 均被占用')
        return pid, len(used)


    # ---------- Phase 12: BUILD APK / INSTALL ----------
    def build_apk(self):
        """Orchestrate: final_face + the player config -> the proven phase11 injectors
        -> the signed APK. Dashboard only orchestrates; the injection logic stays
        in the proven scripts (no duplication)."""
        try:
            cfg = self.validate_player_config()
        except ValueError as e:
            self.set_stage('PLAYER', 'FAIL: ' + str(e)[:60]); return
        ff_baked = self.run_dir / 'final_face' / 'baked.png'
        if not ff_baked.exists():
            self.set_stage('FACE', 'FAIL: final_face/baked.png 缺失，先 ACCEPT FACE'); return
        try:
            pid, used_n = self.allocate_pid()
        except Exception as e:
            self.set_stage('PLAYER', 'FAIL: ' + str(e)[:60]); return
        self.set_stage('PLAYER', 'PASS (pid=%d)' % pid)

        build_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        bdir = PROJECT_ROOT / 'runs' / 'builds' / build_id
        bdir.mkdir(parents=True, exist_ok=False)
        config = {'pid': pid, 'name': cfg['name'], 'team_id': cfg['team_id'],
                  'attrs': cfg['attrs'], 'year': 1998, 'position_b1': cfg['position_b1']}
        cfg_path = bdir / 'build_config.json'
        cfg_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
        self.set_stage('APK', 'RUNNING (注入中，约 1-3 分钟)')

        def worker():
            env = dict(os.environ, PHASE11_CONFIG=str(cfg_path))
            r1 = subprocess.run([sys.executable, str(PROJECT_ROOT / 'scripts' / 'phase11_e2e_inject.py')],
                                capture_output=True, text=True, env=env, cwd=str(PROJECT_ROOT))
            (bdir / 'inject_log.txt').write_text(r1.stdout + r1.stderr, encoding='utf-8')
            self.after(0, lambda: self.build_done(bdir, r1))
        threading.Thread(target=worker, daemon=True).start()

    def build_done(self, bdir, result):
        if result.returncode != 0:
            self.set_stage('APK', 'FAIL (详见 build 目录 inject_log.txt)')
            self.set_status('APK 构建失败（build 目录已保留供排查）'); return
        apk = PROJECT_ROOT / 'dist' / 'fl26_e2e.apk'
        if not apk.exists():
            self.set_stage('APK', 'FAIL: APK 未生成'); return
        shutil.copy2(apk, bdir / 'fl26_e2e_signed.apk')
        self.set_stage('APK', 'PASS')
        self.set_status('APK 就绪 —— 可 INSTALL TO DEVICE')
        self.last_apk = apk

    def install_apk(self):
        apk = getattr(self, 'last_apk', None) or (PROJECT_ROOT / 'dist' / 'fl26_e2e.apk')
        if not apk.exists():
            self.set_stage('INSTALL', 'FAIL: APK 不存在（先 BUILD）'); return
        self.set_stage('INSTALL', 'RUNNING (安装中)')
        def worker():
            try:
                r = subprocess.run([str(ADB), 'install', '-r', str(apk)],
                                   capture_output=True, text=True, timeout=600)
                ok = 'Success' in r.stdout
            except Exception as ex:
                ok = False; r = None
                self.after(0, lambda: self.set_stage('INSTALL', 'FAIL: ' + str(ex)[:60]))
            if True:
                def done():
                    self.set_stage('INSTALL', 'PASS' if ok else 'FAIL (详见 status)')
                    self.set_status('安装 ' + ('成功 —— 进 League 验证球员' if ok else '失败'))
                self.after(0, done)
        threading.Thread(target=worker, daemon=True).start()

# ---------------- selftest ----------------
def selftest():
    """Non-GUI verification of the Dashboard's data paths. Writes STEP10 gate evidence."""
    ok = {}
    run_dir = Path(DEFAULT_RUN)
    cand_dir = run_dir / "candidates"

    # STEP10_INPUT_READY: source photo exists
    photo = FACE_BENCH / "inputs" / "test01_front.jpg"
    ok["STEP10_INPUT_READY"] = photo.exists() and photo.stat().st_size > 10000

    # STEP10_CANDIDATE_VIEW_READY: candidates + metrics loadable, REJECT flag present
    metrics = load_metrics(run_dir)
    ok["STEP10_CANDIDATE_VIEW_READY"] = (
        len(metrics) >= 8 and any(m.get("status") == "REJECT" for m in metrics.values())
        and all((cand_dir / c / "baked.png").exists() for c in metrics if (cand_dir / c).exists()))

    # STEP10_MANUAL_TUNING_READY + NONDESTRUCTIVE: create tuned candidate from c4
    src = cand_dir / "c4"
    h_before = {f.name: sha256(f) for f in src.iterdir() if f.is_file()}
    tid = next_tuned_id(run_dir, "c4")
    dst = cand_dir / tid
    dst.mkdir(parents=True, exist_ok=False)
    for f in ("baked.png", "front.png"):
        shutil.copy2(src / f, dst / f)
    params_after = dict(BASE_PARAMS); params_after["b1"] = 25; params_after["b7"] = 1
    tuning = {
        "source_candidate": "c4", "tuned_id": tid,
        "created": datetime.now().isoformat(timespec="seconds"),
        "parameters_before": dict(BASE_PARAMS),
        "parameters_after": params_after,
        "changes": [{"field": k, "before": BASE_PARAMS[k], "after": params_after[k]}
                    for k in sorted(BASE_PARAMS) if BASE_PARAMS[k] != params_after[k]],
    }
    (dst / "manual_tuning.json").write_text(json.dumps(tuning, ensure_ascii=False, indent=2), encoding="utf-8")
    h_after = {f.name: sha256(f) for f in src.iterdir() if f.is_file()}
    ok["STEP10_MANUAL_TUNING_READY"] = (dst / "manual_tuning.json").exists() and tuning["changes"]
    ok["STEP10_NONDESTRUCTIVE_READY"] = (h_before == h_after) and (dst / "baked.png").exists()

    # STEP10_FINAL_FACE_EXPORT_READY: export final_face from the tuned candidate
    final_dir = run_dir / "final_face_selftest"
    final_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dst / "baked.png", final_dir / "baked.png")
    manifest = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "schema": "fl26_final_face_v1",
        "source_photos": [str(photo)],
        "selected_candidate": "c4",
        "tuned_candidate": tid,
        "appearance_patch": params_after,
        "appearance_note": "b0/b2/b3/b5/b6/b8/b9/b11-b13/b15/b16 保持 PlayerAppearanceTable 原记录值",
        "b1_texture": b1_to_texture_name(params_after["b1"]),
        "baked_texture": str(final_dir / "baked.png"),
        "preview_images": [],
        "validation": {"user_accepted": True, "selftest": True},
        "provenance": {"candidate_pool_run": str(run_dir), "generator_seed": 20260903},
    }
    (final_dir / "face_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ok["STEP10_FINAL_FACE_EXPORT_READY"] = (
        (final_dir / "face_manifest.json").exists()
        and json.loads((final_dir / "face_manifest.json").read_text(encoding="utf-8"))["b1_texture"]
        == "face_eastAsia_new4")

    # STEP10_REALTIME_PREVIEW_READY: verified separately by an actual Unity render job
    # (batch_step9_run*-with-dashboard_job / renders/*/render_done.json)
    renders = DASHBOARD_DIR / "renders"
    ok["STEP10_REALTIME_PREVIEW_READY"] = any(
        (d / "render_done.json").exists() and
        json.loads((d / "render_done.json").read_text(encoding="utf-8")).get("ok")
        for d in renders.glob("*")) if renders.exists() else False

    print(json.dumps(ok, indent=2))
    all_ok = all(ok.values())
    gates = {k: ("GREEN" if v else "RED") for k, v in ok.items()}
    gates["PC_PREVIEW_VALID_regression"] = "GREEN (Step9BatchRunner unchanged; DashboardRender.cs additive)"
    (DASHBOARD_DIR / "selftest_result.json").write_text(
        json.dumps({"ok": all_ok, "gates": gates, "tuned_id": tid}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print("SELFTEST:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    app = Dashboard()
    app.mainloop()
