using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace FL26Previewer.EditorTools
{
    /// <summary>
    /// Step 9 batch verification driver (EDIT MODE, orbit capture around the head center).
    /// Drives PreviewerBootstrap's own private methods via reflection so the verification
    /// exercises the exact runtime code paths (enumeration, face loading, deps dumps, c4).
    /// </summary>
    public static class Step9BatchRunner
    {
        const string OutputDirRel = "runs/preview";
        const int CaptureW = 1280, CaptureH = 960;

        static readonly StringBuilder summary = new StringBuilder();
        static readonly List<string> errors = new List<string>();
        static string outputDir;

        public static void Run()
        {
            string projectDir = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            outputDir = Path.Combine(projectDir, OutputDirRel.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(outputDir);
            summary.AppendLine("=== Step9BatchRunner (edit mode, orbit capture) ===");
            summary.AppendLine("unity=" + Application.unityVersion);
            summary.AppendLine("buildTarget=" + EditorUserBuildSettings.activeBuildTarget);
            summary.AppendLine("projectDir=" + projectDir);
            summary.AppendLine("start=" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));

            try
            {
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

                var camGo = new GameObject("PreviewCam");
                var cam = camGo.AddComponent<Camera>();
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = new Color(0.18f, 0.18f, 0.20f, 1f);
                cam.fieldOfView = 30f;
                cam.nearClipPlane = 0.01f;
                cam.farClipPlane = 100f;
                RenderSettings.ambientLight = new Color(0.55f, 0.55f, 0.55f, 1f);
                var lightGo = new GameObject("PreviewLight");
                var li = lightGo.AddComponent<Light>();
                li.type = LightType.Directional;
                li.intensity = 1.4f;
                lightGo.transform.rotation = Quaternion.Euler(35f, 30f, 0f);
                var fillGo = new GameObject("PreviewFill");
                var fill = fillGo.AddComponent<Light>();
                fill.type = LightType.Directional;
                fill.intensity = 0.5f;
                fillGo.transform.rotation = Quaternion.Euler(20f, 200f, 0f);
                var pivot = new GameObject("Pivot");

                var holder = new GameObject("FL26Previewer");
                var comp = holder.AddComponent<FL26Previewer.PreviewerBootstrap>();
                Type t = typeof(FL26Previewer.PreviewerBootstrap);
                var flags = BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;
                var fBundle = t.GetField("bundle", flags);
                var fCam = t.GetField("cam", flags);
                var fPivot = t.GetField("pivot", flags);
                var fAvatar = t.GetField("currentAvatar", flags);
                var fRenderer = t.GetField("currentRenderer", flags);
                var mEnumerate = t.GetMethod("EnumerateAssets", flags);
                var mLoadFace = t.GetMethod("LoadFace", flags);
                var mMeshFallback = t.GetMethod("LoadMeshFallback", flags);
                var mWriteReport = t.GetMethod("WriteReport", flags);
                var fNames = t.GetField("faceObjectNames", flags);
                var fCandidates = t.GetField("bundleCandidates", flags);
                var mResolve = t.GetMethod("ResolveExisting", flags);
                fCam.SetValue(comp, cam);
                fPivot.SetValue(comp, pivot);

                string[] candidates = (string[])fCandidates.GetValue(null);
                string usedPath = null;
                var attempts = new StringBuilder();
                foreach (var rel in candidates)
                {
                    string full = (string)mResolve.Invoke(null, new object[] { rel });
                    if (full == null) continue;
                    var ab = AssetBundle.LoadFromFile(full);
                    if (ab != null) { fBundle.SetValue(comp, ab); usedPath = full; break; }
                    attempts.AppendLine("  failed: " + full);
                    Log("candidate exists but LoadFromFile failed: " + full);
                }
                summary.AppendLine("bundleLoaded=" + (usedPath != null));
                summary.AppendLine("bundlePath=" + usedPath);
                if (attempts.Length > 0)
                {
                    summary.AppendLine("load attempts:");
                    summary.AppendLine(attempts.ToString());
                }
                if (usedPath == null)
                {
                    Fail("no loadable candidate among [" + string.Join(" | ", candidates) + "]");
                    Finish(1);
                    return;
                }
                Log("Bundle loaded: " + usedPath);

                t.GetMethod("BuildAssetPathMap", flags)?.Invoke(comp, null);
                mEnumerate.Invoke(comp, null);
                string[] names = (string[])fNames.GetValue(null);

                for (int i = 0; i < names.Length; i++)
                {
                    CleanupAvatar(comp, fAvatar, fRenderer);
                    bool ok = (bool)mLoadFace.Invoke(comp, new object[] { i });
                    if (!ok) ok = LoadFaceViaAllAssets(comp, t, flags, fBundle, fAvatar, fRenderer, fPivot, names[i]);
                    if (!ok && mMeshFallback != null) mMeshFallback.Invoke(comp, new object[] { i });
                    ConvertSmrToStatic(comp, fAvatar, fRenderer);
                    // runtime parity: the game's FaceMaterialSupplier assigns the per-appearance
                    // face texture at load time; the bundle material only carries a generic
                    // default (face_southAsia_new1). Replicate it so the preview shows the MOD
                    // face texture (Ma Jiantao bake) exactly like on device.
                    AssignModFaceTexture(comp, t, flags, fBundle, fAvatar, i + 1);
                    if (!CaptureHeadSet(comp, fRenderer, cam, names[i]))
                        errors.Add("no static mesh for " + names[i]);
                    Log("loaded " + names[i] + " (fallback=" + !ok + ")");
                }

                string c4 = (string)mResolve.Invoke(null,
                    new object[] { "face_benchmark/runs/test01/candidates/c4/baked.png" });
                summary.AppendLine("c4TextureFound=" + (c4 != null));
                if (c4 != null)
                {
                    CleanupAvatar(comp, fAvatar, fRenderer);
                    if (!(bool)mLoadFace.Invoke(comp, new object[] { 0 }))
                        LoadFaceViaAllAssets(comp, t, flags, fBundle, fAvatar, fRenderer, fPivot, names[0]);
                    ConvertSmrToStatic(comp, fAvatar, fRenderer);
                    AssignModFaceTexture(comp, t, flags, fBundle, fAvatar, 1);
                    var renderer = fRenderer.GetValue(comp) as Renderer;
                    var faceMf = renderer != null ? renderer.GetComponent<MeshFilter>() : null;
                    if (renderer != null && faceMf != null && faceMf.sharedMesh != null)
                    {
                        var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
                        tex.LoadImage(File.ReadAllBytes(c4));
                        tex.wrapMode = TextureWrapMode.Clamp;
                        var mat = renderer.material;
                        if (mat.HasProperty("_MainTex")) mat.SetTexture("_MainTex", tex);
                        else mat.mainTexture = tex;
                        Log("candidate c4 applied");
                        var headC = renderer.transform.TransformPoint(faceMf.sharedMesh.bounds.center);
                        var d = faceMf.sharedMesh.bounds.extents.magnitude * 3.5f + 0.05f;
                        OrbitCapture(cam, headC, d, 0f, "batch_c4_view1.png");
                        OrbitCapture(cam, headC, d, 45f, "batch_c4_view2.png");
                        OrbitCapture(cam, headC, d, 315f, "batch_c4_view3.png");
                        OrbitCapture(cam, headC, d, 90f, "batch_c4_view4.png");
                    }
                    else errors.Add("no static face renderer for candidate texture");
                }

                int fallbackCount = 0;
                foreach (var f in Directory.GetFiles(outputDir, "deps_*.txt"))
                    if (File.ReadAllText(f).Contains("SHADER_FALLBACK_INTERNALERROR")) fallbackCount++;
                summary.AppendLine("shaderFallbackAvatarCount=" + fallbackCount);
                summary.AppendLine("depsFiles=" + Directory.GetFiles(outputDir, "deps_*.txt").Length);
                summary.AppendLine("enumerationPresent=" + File.Exists(Path.Combine(outputDir, "asset_enumeration.txt")));

                mWriteReport.Invoke(comp, null);
                Finish(0);
            }
            catch (Exception ex)
            {
                Fail(ex.ToString());
                Finish(1);
            }
        }

        /// <summary>Replicates the game's FaceMaterialSupplier: assign face_eastasia_new{fam}
        /// (the Ma Jiantao bake replaced by the allchina mod) to the "face" material, so the
        /// preview matches what the device renders for China players.</summary>
        static void AssignModFaceTexture(UnityEngine.Object comp, Type t, BindingFlags flags, FieldInfo fBundle, FieldInfo fAvatar, int fam)
        {
            var bundle = fBundle.GetValue(comp) as AssetBundle;
            var avatar = fAvatar.GetValue(comp) as GameObject;
            if (bundle == null || avatar == null) return;
            // exact container path used by the v5c build script (male face textures;
            // a female duplicate exists, so the name map cannot be trusted here)
            var texPath = "assets/models/player2021/textures/face/face_eastasia_new" + fam + ".png";
            var modTex = bundle.LoadAsset<Texture2D>(texPath);
            if (modTex == null) { Log("mod texture missing: " + texPath); return; }
            int applied = 0;
            foreach (var r in avatar.GetComponentsInChildren<Renderer>(true))
                foreach (var m in r.materials)
                    if (m.name.ToLower().Contains("face") && m.HasProperty("_MainTex"))
                    {
                        m.SetTexture("_MainTex", modTex);
                        applied++;
                    }
            Log("mod face texture assigned x" + applied + ": " + texPath);
        }

        static bool CaptureHeadSet(UnityEngine.Object comp, FieldInfo fRenderer, Camera cam, string name)
        {
            var renderer = fRenderer.GetValue(comp) as Renderer;
            var faceMf = renderer != null ? renderer.GetComponent<MeshFilter>() : null;
            if (renderer == null || faceMf == null || faceMf.sharedMesh == null) return false;
            var headC = renderer.transform.TransformPoint(faceMf.sharedMesh.bounds.center);
            var d = faceMf.sharedMesh.bounds.extents.magnitude * 3.5f + 0.05f;
            OrbitCapture(cam, headC, d, 0f, "batch_face_" + name + "_front.png");
            OrbitCapture(cam, headC, d, 180f, "batch_face_" + name + "_back.png");
            return true;
        }

        static void OrbitCapture(Camera cam, Vector3 headCenter, float dist, float dirDeg, string fileName)
        {
            var rad = dirDeg * Mathf.Deg2Rad;
            cam.transform.position = headCenter + new Vector3(Mathf.Sin(rad) * dist, 0f, Mathf.Cos(rad) * dist);
            cam.transform.LookAt(headCenter);
            Capture(cam, fileName);
        }

        static bool LoadFaceViaAllAssets(UnityEngine.Object comp, Type t, BindingFlags flags, FieldInfo fBundle,
            FieldInfo fAvatar, FieldInfo fRenderer, FieldInfo fPivot, string name)
        {
            var bundle = fBundle.GetValue(comp) as AssetBundle;
            if (bundle == null) return false;
            var all = bundle.LoadAllAssets<GameObject>();
            var go = all.FirstOrDefault(g => string.Equals(g.name, name, StringComparison.OrdinalIgnoreCase));
            if (go == null) return false;
            var inst = UnityEngine.Object.Instantiate(go);
            inst.SetActive(true);
            inst.transform.SetParent(((GameObject)fPivot.GetValue(comp)).transform, false);
            fAvatar.SetValue(comp, inst);
            var renderer = inst.GetComponentInChildren<Renderer>();
            fRenderer.SetValue(comp, renderer);
            foreach (var r in inst.GetComponentsInChildren<Renderer>())
                foreach (var m in r.materials)
                    if (m.shader == null || m.shader.name == "Hidden/InternalErrorShader")
                        m.shader = Shader.Find("Unlit/Texture");
            var mDump = t.GetMethod("DumpAvatarDeps", flags);
            if (mDump != null)
                File.WriteAllText(Path.Combine(outputDir, "deps_" + name + ".txt"),
                    (string)mDump.Invoke(comp, new object[] { inst }));
            Log("loaded via LoadAllAssets: " + name);
            return true;
        }

        static void ForceUnlit(UnityEngine.Object comp, FieldInfo fAvatar)
        {
            var avatar = fAvatar.GetValue(comp) as GameObject;
            if (avatar == null) return;
            var unlit = Shader.Find("Unlit/Texture");
            foreach (var r in avatar.GetComponentsInChildren<Renderer>(true))
                foreach (var m in r.materials)
                {
                    var tex = m.HasProperty("_MainTex") ? m.GetTexture("_MainTex") : null;
                    m.shader = unlit;
                    if (m.HasProperty("_MainTex")) m.SetTexture("_MainTex", tex);
                }
        }

        static void ConvertSmrToStatic(UnityEngine.Object comp, FieldInfo fAvatar, FieldInfo fRenderer)
        {
            var avatar = fAvatar.GetValue(comp) as GameObject;
            if (avatar == null) return;
            var smrs = avatar.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            MeshRenderer faceMr = null;
            int faceVc = -1;
            foreach (var smr in smrs)
            {
                if (smr.sharedMesh == null || smr.sharedMesh.vertexCount == 0) continue;
                if (faceMr != null && smr.sharedMesh.vertexCount <= faceVc) continue;
                var go = new GameObject(smr.name + "_static");
                var srcT = smr.rootBone != null ? smr.rootBone.transform : smr.transform;
                go.transform.SetParent(avatar.transform, false);
                go.layer = avatar.layer;
                var mf = go.AddComponent<MeshFilter>();
                mf.sharedMesh = smr.sharedMesh;
                var verts = smr.sharedMesh.vertices;
                if (verts != null && verts.Length > 0)
                {
                    var mn = verts[0]; var mx = verts[0];
                    foreach (var v in verts) { mn = Vector3.Min(mn, v); mx = Vector3.Max(mx, v); }
                    smr.sharedMesh.bounds = new Bounds((mn + mx) * 0.5f, mx - mn);
                }
                var rel = avatar.transform.worldToLocalMatrix * srcT.localToWorldMatrix;
                go.transform.localPosition = rel.GetColumn(3);
                go.transform.localRotation = Quaternion.Euler(0f, 180f, 0f) * Quaternion.Euler(-90f, 0f, 0f) * Quaternion.Euler(0f, -90f, 0f) * rel.rotation * Quaternion.Euler(90f, 0f, 0f);
                go.transform.localScale = rel.lossyScale;
                Vector3 headW0 = go.transform.TransformPoint(mf.sharedMesh.bounds.center);
                go.transform.localRotation = Quaternion.Euler(0f, 0f, 180f) * go.transform.localRotation;
                Vector3 headW1 = go.transform.TransformPoint(mf.sharedMesh.bounds.center);
                go.transform.position += headW0 - headW1;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterials = smr.sharedMaterials;
                if (faceMr == null || smr.sharedMesh.vertexCount > faceVc)
                {
                    faceMr = mr;
                    faceVc = smr.sharedMesh.vertexCount;
                }
                UnityEngine.Object.DestroyImmediate(smr);
            }
            if (faceMr != null) fRenderer.SetValue(comp, faceMr);
        }

        static void CleanupAvatar(UnityEngine.Object comp, FieldInfo fAvatar, FieldInfo fRenderer)
        {
            var prev = fAvatar.GetValue(comp) as GameObject;
            if (prev != null) UnityEngine.Object.DestroyImmediate(prev);
            fAvatar.SetValue(comp, null);
            fRenderer.SetValue(comp, null);
        }

        static void Capture(Camera cam, string fileName)
        {
            try
            {
                var rt = new RenderTexture(CaptureW, CaptureH, 24);
                var prevTarget = cam.targetTexture;
                cam.targetTexture = rt;
                cam.Render();
                RenderTexture.active = rt;
                var tex = new Texture2D(CaptureW, CaptureH, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, CaptureW, CaptureH), 0, 0);
                tex.Apply();
                cam.targetTexture = prevTarget;
                RenderTexture.active = null;
                string path = Path.Combine(outputDir, fileName);
                File.WriteAllBytes(path, tex.EncodeToPNG());
                summary.AppendLine("captured " + fileName + " (" + new FileInfo(path).Length + " B)");
                Log("captured " + fileName);
            }
            catch (Exception ex)
            {
                errors.Add("capture " + fileName + ": " + ex.Message);
                Log("capture FAILED " + fileName + ": " + ex.Message);
            }
        }

        static void Log(string msg)
        {
            UnityEngine.Debug.Log("[Step9BatchRunner] " + msg);
        }

        static void Fail(string why)
        {
            errors.Add(why);
            Log("FAIL: " + why);
        }

        static void Finish(int code)
        {
            summary.AppendLine("errorCount=" + errors.Count);
            foreach (var e in errors) summary.AppendLine("  error: " + e);
            summary.AppendLine("end=" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " exitCode=" + code);
            summary.AppendLine("result=" + (code == 0 && errors.Count == 0 ? "OK" : "FAILED"));
            File.WriteAllText(Path.Combine(outputDir, "batch_summary.txt"), summary.ToString());
            EditorApplication.Exit(code);
        }
    }
}
