using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace FL26Previewer.EditorTools
{
    /// <summary>
    /// Phase 13B composition renderer: renders the game appearance equation for a
    /// LIST of appearance states in ONE Unity batch launch:
    ///   head mesh (dual submesh: iris slot + face slot) + face texture (bake)
    ///   + iris texture + optional hair GO (static bind pose) + hair color tint.
    /// Output per state: front/45L/45R/side PNGs + state manifest.
    /// Additive to DashboardRender (untouched). Job via PHASE13B_JOB env var.
    /// Face-shape (b14) morph is IL2CPP-internal: NOT applied here (flagged in manifest).
    /// </summary>
    public static class Phase13BRender
    {
        [Serializable]
        class AppearanceState
        {
            public string name;
            public string faceMesh;     // head prefab GO name, e.g. face_EastAsia_new1
            public string faceTex;      // face texture (bake) name IN BUNDLE
            public string faceTexPath;  // OR external bake PNG path (overrides faceTex)
            public string irisTex;      // iris texture name (eye_darkbrown etc.)
            public string hairGO;       // hair GameObject name ("" = none)
            public string hairTex;      // hair texture name ("" = auto by name)
            public string hairColor;    // RRGGBB hex tint
            public string hairTintTex;  // pre-tinted texture PNG path (overrides hairColor)
        }

        [Serializable]
        class Job
        {
            public string bundlePath;
            public string outDir;
            public List<AppearanceState> states;
        }

        const int CaptureW = 1280, CaptureH = 960;

        public static void Run()
        {
            var jobPath = Environment.GetEnvironmentVariable("PHASE13B_JOB");
            if (string.IsNullOrEmpty(jobPath))
                jobPath = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "phase13b_job.json"));
            var job = JsonUtility.FromJson<Job>(File.ReadAllText(jobPath));
            var outDirRoot = Path.GetFullPath(job.outDir);
            Directory.CreateDirectory(outDirRoot);

            var log = new StringBuilder();
            log.AppendLine("=== Phase13BRender " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " ===");
            log.AppendLine("bundle=" + job.bundlePath + " states=" + (job.states != null ? job.states.Count : 0));

            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var camGo = new GameObject("Cam");
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.18f, 0.18f, 0.20f, 1f);
            cam.fieldOfView = 30f;
            cam.nearClipPlane = 0.01f; cam.farClipPlane = 100f;
            RenderSettings.ambientLight = new Color(0.55f, 0.55f, 0.55f, 1f);
            var l1 = new GameObject("Key").AddComponent<Light>();
            l1.type = LightType.Directional; l1.intensity = 1.4f;
            l1.transform.rotation = Quaternion.Euler(35f, 30f, 0f);
            var l2 = new GameObject("Fill").AddComponent<Light>();
            l2.type = LightType.Directional; l2.intensity = 0.5f;
            l2.transform.rotation = Quaternion.Euler(20f, 200f, 0f);

            var bundle = AssetBundle.LoadFromFile(job.bundlePath);
            if (bundle == null) throw new Exception("bundle load failed: " + job.bundlePath);
            var texByName = new Dictionary<string, Texture2D>();
            foreach (var t in bundle.LoadAllAssets<Texture2D>())
                if (!texByName.ContainsKey(t.name)) texByName[t.name] = t;
            log.AppendLine("textures indexed: " + texByName.Count);

            var results = new List<string>();
            int okCount = 0;
            foreach (var st in job.states)
            {
                try
                {
                    var stale = UnityEngine.Object.FindObjectsOfType<GameObject>();
                    for (int i = stale.Length - 1; i >= 0; i--)
                    {
                        var go = stale[i];
                        if (go == null) continue;   // destroyed as a child of an already-destroyed root
                        if (go.name == "Cam" || go.name == "Key" || go.name == "Fill") continue;
                        if (go.transform.parent == null && go.name.StartsWith("root_"))
                            UnityEngine.Object.DestroyImmediate(go);
                    }

                    // ---- head ----
                    var headPrefab = bundle.LoadAsset<GameObject>(st.faceMesh);
                    if (headPrefab == null)
                        headPrefab = bundle.LoadAllAssets<GameObject>()
                            .FirstOrDefault(g => string.Equals(g.name, st.faceMesh, StringComparison.OrdinalIgnoreCase));
                    if (headPrefab == null) throw new Exception("head prefab not found: " + st.faceMesh);
                    var head = UnityEngine.Object.Instantiate(headPrefab);
                    head.SetActive(true);
                    head.name = "head_" + st.name;
                    // stable scene-root container so ConvertSmr's parent logic always has a valid parent
                    var root = new GameObject("root_" + st.name);
                    head.transform.SetParent(root.transform, false);

                    Texture2D faceTex = null;
                    if (!string.IsNullOrEmpty(st.faceTexPath) && File.Exists(st.faceTexPath))
                    {
                        faceTex = new Texture2D(4, 4, TextureFormat.RGB24, false);
                        faceTex.LoadImage(File.ReadAllBytes(st.faceTexPath));
                        faceTex.name = Path.GetFileNameWithoutExtension(st.faceTexPath);
                    }
                    else faceTex = ResolveTex(bundle, texByName, st.faceTex);
                    var irisTex = string.IsNullOrEmpty(st.irisTex) ? null : ResolveTex(bundle, texByName, st.irisTex);
                    int faceApplied = 0, irisApplied = 0;
                    foreach (var r in head.GetComponentsInChildren<Renderer>(true))
                    {
                        if (r == null || r.sharedMaterials == null) continue;
                        var mats = r.sharedMaterials;
                        for (int i = 0; i < mats.Length; i++)
                        {
                            var m = mats[i];
                            if (m == null || m.shader == null) continue;
                            var mn = m.name.ToLower();
                            if ((mn.Contains("eye")) && irisTex != null && m.HasProperty("_MainTex"))
                            { m.SetTexture("_MainTex", irisTex); mats[i] = m; irisApplied++; }
                            else if ((mn.Contains("face") || mn.Contains("head") || mn.Contains("skin")) && m.HasProperty("_MainTex"))
                            { m.SetTexture("_MainTex", faceTex); mats[i] = m; faceApplied++; }
                        }
                        r.sharedMaterials = mats;
                    }

                    // ---- hair ----
                    Transform hairStatic = null;
                    int hairTinted = 0;
                    if (!string.IsNullOrEmpty(st.hairGO))
                    {
                        var hairPrefab = bundle.LoadAsset<GameObject>(st.hairGO);
                        if (hairPrefab == null)
                            hairPrefab = bundle.LoadAllAssets<GameObject>()
                                .FirstOrDefault(g => string.Equals(g.name, st.hairGO, StringComparison.OrdinalIgnoreCase));
                        if (hairPrefab == null) throw new Exception("hair GO not found: " + st.hairGO);
                        var hair = UnityEngine.Object.Instantiate(hairPrefab);
                        hair.SetActive(true);
                        hair.name = "hair_" + st.name;
                        hair.transform.SetParent(root.transform, false);

                        var hairTex = string.IsNullOrEmpty(st.hairTex)
                            ? FindTexFor(texByName, st.hairGO)
                            : ResolveTex(bundle, texByName, st.hairTex);
                        foreach (var r in hair.GetComponentsInChildren<Renderer>(true))
                        {
                            if (r == null || r.sharedMaterials == null) continue;
                            var mats = r.sharedMaterials;
                            bool needsMat = false;
                            for (int i = 0; i < mats.Length; i++)
                                if (mats[i] == null || mats[i].shader == null || mats[i].name.StartsWith("13 - Default") || mats[i].name.StartsWith("?"))
                                    needsMat = true;
                            if (needsMat && hairTex != null)
                            {
                                var nm = new Material(Shader.Find("Standard"));
                                nm.name = "p13b_hair_" + st.name;
                                var texPath = st.hairTintTex;
                                if (!string.IsNullOrEmpty(texPath) && File.Exists(texPath))
                                {
                                    var data = File.ReadAllBytes(texPath);
                                    var t2 = new Texture2D(2, 2, TextureFormat.RGB24, false);
                                    t2.LoadImage(data);
                                    t2.name = Path.GetFileNameWithoutExtension(texPath);
                                    nm.SetTexture("_MainTex", t2);
                                }
                                else nm.SetTexture("_MainTex", hairTex);
                                for (int i = 0; i < mats.Length; i++) mats[i] = nm;
                            }
                            if (!string.IsNullOrEmpty(st.hairColor) && st.hairColor.Length == 6)
                            {
                                var c = HexColor(st.hairColor);
                                for (int i = 0; i < mats.Length; i++)
                                {
                                    var m = mats[i];
                                    if (m != null && m.shader != null && m.HasProperty("_Color")) { m.SetColor("_Color", c); hairTinted++; }
                                }
                            }
                            r.sharedMaterials = mats;
                        }
                        hairStatic = ConvertSmr(hair, root.transform);
                        // hair transform follows head's conversion, keep same-space alignment:
                        if (hairStatic != null)
                        {
                            hairStatic.SetParent(head.transform.parent, true);
                        }
                    }

                    // ---- head -> static ----
                    var headStatic = ConvertSmr(head, root.transform);
                    if (headStatic == null) throw new Exception("head SMR conversion failed");

                    // align hair to head using bind-pose relative offset (same source space)
                    if (hairStatic != null)
                    {
                        var hb = hairStatic.GetComponent<MeshFilter>().sharedMesh.bounds;
                        var fb = headStatic.GetComponent<MeshFilter>().sharedMesh.bounds;
                        var headC = headStatic.transform.TransformPoint(fb.center);
                        var hairC = hairStatic.transform.TransformPoint(hb.center);
                        // hair should sit so its center-Y is above head center by (headExtY+hairExtY)*0.55
                        var dy = (fb.extents.y + hb.extents.y) * 0.55f;
                        var target = headC + new Vector3(0f, dy, 0f);
                        hairStatic.transform.position += target - hairC;
                    }

                    var fb2 = headStatic.GetComponent<MeshFilter>().sharedMesh.bounds;
                    var headC2 = headStatic.transform.TransformPoint(fb2.center);
                    var d = fb2.extents.magnitude * 3.5f + 0.05f;

                    var stateDir = Path.Combine(outDirRoot, st.name);
                    Directory.CreateDirectory(stateDir);
                    var captures = new List<string>();
                    foreach (var (dirDeg, tag) in new (float, string)[] { (0f, "front"), (45f, "45L"), (315f, "45R"), (90f, "side") })
                    {
                        var rad = dirDeg * Mathf.Deg2Rad;
                        cam.transform.position = headC2 + new Vector3(Mathf.Sin(rad) * d, 0f, Mathf.Cos(rad) * d);
                        cam.transform.LookAt(headC2);
                        var fn = st.name + "_" + tag + ".png";
                        Capture(cam, Path.Combine(stateDir, fn));
                        captures.Add(fn);
                    }

                    results.Add(string.Format(
                        "{{\"state\":\"{0}\",\"ok\":true,\"faceTexAssigned\":{1},\"irisAssigned\":{2},\"hair\":\"{3}\",\"hairTinted\":{4}}}",
                        st.name, faceApplied, irisApplied, st.hairGO ?? "", hairTinted));
                    okCount++;
                    log.AppendLine("[OK] " + st.name + " face=" + faceApplied + " iris=" + irisApplied + " hairTinted=" + hairTinted);
                }
                catch (Exception ex)
                {
                    results.Add("{\"state\":\"" + st.name + "\",\"ok\":false,\"error\":\"" + ex.Message.Replace("\"", "'") + "\"}");
                    log.AppendLine("[FAIL] " + st.name + ": " + ex);
                }
            }

            var done = new StringBuilder();
            done.AppendLine("{");
            done.AppendLine("  \"ok\": " + (okCount > 0 ? "true" : "false") + ",");
            done.AppendLine("  \"statesOk\": " + okCount + ",");
            done.AppendLine("  \"states\": [" + string.Join(",", results) + "]");
            done.AppendLine("}");
            File.WriteAllText(Path.Combine(outDirRoot, "render_done.json"), done.ToString());
            File.WriteAllText(Path.Combine(outDirRoot, "render_log.txt"), log.ToString());
            Debug.Log("[Phase13BRender] done, ok=" + okCount);
            EditorApplication.Exit(0);
        }

        static Texture2D ResolveTex(AssetBundle b, Dictionary<string, Texture2D> idx, string name)
        {
            if (idx.TryGetValue(name, out var t)) return t;
            return b.LoadAllAssets<Texture2D>()
                .FirstOrDefault(x => string.Equals(x.name, name, StringComparison.OrdinalIgnoreCase));
        }

        // hair texture heuristic: prefer exact GO name, then mesh name, then same prefix
        static Texture2D FindTexFor(Dictionary<string, Texture2D> idx, string goName)
        {
            if (idx.TryGetValue(goName, out var t)) return t;
            var key = goName.ToLower();
            Texture2D best = null;
            foreach (var kv in idx)
            {
                var k = kv.Key.ToLower();
                if (k.StartsWith(key) || key.StartsWith(k)) { best = kv.Value; break; }
            }
            return best;
        }

        static Color HexColor(string hex)
        {
            var r = Convert.ToByte(hex.Substring(0, 2), 16) / 255f;
            var g = Convert.ToByte(hex.Substring(2, 2), 16) / 255f;
            var b = Convert.ToByte(hex.Substring(4, 2), 16) / 255f;
            return new Color(r, g, b, 1f);
        }

        // SMR -> static MeshRenderer in bind pose (proven conversion from Step9/Dashboard)
        static Transform ConvertSmr(GameObject avatar, Transform parent)
        {
            Transform best = null;
            int bestVc = -1;
            foreach (var smr in avatar.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr.sharedMesh == null || smr.sharedMesh.vertexCount == 0) continue;
                var st = new GameObject(smr.name + "_static");
                var srcT = smr.rootBone != null ? smr.rootBone.transform : smr.transform;
                st.transform.SetParent(parent != null ? parent : avatar.transform.parent, false);
                var verts = smr.sharedMesh.vertices;
                if (verts != null && verts.Length > 0)
                {
                    var mn = verts[0]; var mx = verts[0];
                    foreach (var v in verts) { mn = Vector3.Min(mn, v); mx = Vector3.Max(mx, v); }
                    smr.sharedMesh.bounds = new Bounds((mn + mx) * 0.5f, mx - mn);
                }
                var rel = avatar.transform.worldToLocalMatrix * srcT.localToWorldMatrix;
                st.transform.localPosition = rel.GetColumn(3);
                st.transform.localRotation = Quaternion.Euler(0f, 180f, 0f) * Quaternion.Euler(-90f, 0f, 0f) * Quaternion.Euler(0f, -90f, 0f) * rel.rotation * Quaternion.Euler(90f, 0f, 0f);
                st.transform.localScale = rel.lossyScale;
                var mf = st.AddComponent<MeshFilter>();
                mf.sharedMesh = smr.sharedMesh;
                var mr = st.AddComponent<MeshRenderer>();
                mr.sharedMaterials = smr.sharedMaterials;
                if (smr.sharedMesh.vertexCount > bestVc) { bestVc = smr.sharedMesh.vertexCount; best = st.transform; }
                UnityEngine.Object.DestroyImmediate(smr);
            }
            // apply the same recentring to every produced static under this avatar
            if (best != null)
            {
                var b = best.GetComponent<MeshFilter>().sharedMesh.bounds;
                Vector3 w0 = best.transform.TransformPoint(b.center);
                best.transform.localRotation = Quaternion.Euler(0f, 0f, 180f) * best.transform.localRotation;
                Vector3 w1 = best.transform.TransformPoint(b.center);
                foreach (var t in best.transform.parent.GetComponentsInChildren<Transform>(true))
                    if (t.name.EndsWith("_static"))
                        t.position += w0 - w1;
            }
            return best;
        }

        static void Capture(Camera cam, string path)
        {
            var rt = new RenderTexture(CaptureW, CaptureH, 24);
            var prev = cam.targetTexture;
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(CaptureW, CaptureH, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, CaptureW, CaptureH), 0, 0);
            tex.Apply();
            cam.targetTexture = prev;
            RenderTexture.active = null;
            File.WriteAllBytes(path, tex.EncodeToPNG());
            RenderTexture.DestroyImmediate(rt);
            UnityEngine.Object.DestroyImmediate(tex);
        }
    }
}
