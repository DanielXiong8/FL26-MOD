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
    /// Step 10 Dashboard render job: renders ONE head with a SPECIFIC face texture
    /// (the texture the Dashboard's b1 face-texture-family selector chose) and writes
    /// 4 orbit captures + a render_done.json marker for the Dashboard to poll.
    /// Additive to Step9BatchRunner (which stays untouched for Step 9 regression).
    ///
    /// Job JSON (fixed path, overridable via DASHBOARD_JOB env var):
    /// {
    ///   "bundlePath": "D:/FL26_Mod/tools/FL26_AvatarPreviewer/extracted/avatar_mjt.unity3d",
    ///   "outDir": "D:/FL26_Mod/tools/FL26_FaceDashboard/renders/20260905_001",
    ///   "faceAssetName": "face_EastAsia_new2",
    ///   "textureObjectName": "face_eastAsia_new5"
    /// }
    /// </summary>
    public static class DashboardRender
    {
        [Serializable]
        class RenderJob
        {
            public string bundlePath;
            public string outDir;
            public string faceAssetName;
            public string textureObjectName;
        }

        const int CaptureW = 1280, CaptureH = 960;

        public static void Run()
        {
            var jobPath = Environment.GetEnvironmentVariable("DASHBOARD_JOB");
            if (string.IsNullOrEmpty(jobPath))
                jobPath = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "dashboard_job.json"));
            var job = JsonUtility.FromJson<RenderJob>(File.ReadAllText(jobPath));
            var outDir = Path.GetFullPath(job.outDir);
            Directory.CreateDirectory(outDir);

            var log = new StringBuilder();
            log.AppendLine("=== DashboardRender " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " ===");
            log.AppendLine("bundle=" + job.bundlePath);
            log.AppendLine("face=" + job.faceAssetName + " texture=" + job.textureObjectName);

            try
            {
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

                var camGo = new GameObject("DashCam");
                var cam = camGo.AddComponent<Camera>();
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = new Color(0.18f, 0.18f, 0.20f, 1f);
                cam.fieldOfView = 30f;
                cam.nearClipPlane = 0.01f;
                cam.farClipPlane = 100f;
                RenderSettings.ambientLight = new Color(0.55f, 0.55f, 0.55f, 1f);
                var l1 = new GameObject("KeyLight").AddComponent<Light>();
                l1.type = LightType.Directional; l1.intensity = 1.4f;
                l1.transform.rotation = Quaternion.Euler(35f, 30f, 0f);
                var l2 = new GameObject("FillLight").AddComponent<Light>();
                l2.type = LightType.Directional; l2.intensity = 0.5f;
                l2.transform.rotation = Quaternion.Euler(20f, 200f, 0f);

                var bundle = AssetBundle.LoadFromFile(job.bundlePath);
                if (bundle == null) throw new Exception("bundle load failed: " + job.bundlePath);

                // face prefab: direct name first, LoadAllAssets fallback (asset-range holes)
                var prefab = bundle.LoadAsset<GameObject>(job.faceAssetName);
                if (prefab == null)
                    prefab = bundle.LoadAllAssets<GameObject>()
                        .FirstOrDefault(g => string.Equals(g.name, job.faceAssetName, StringComparison.OrdinalIgnoreCase));
                if (prefab == null) throw new Exception("face prefab not found: " + job.faceAssetName);

                var head = UnityEngine.Object.Instantiate(prefab);
                head.SetActive(true);  // head prefabs ship inactive; game activates at runtime

                // assign the selected face texture to the "face" material
                // (replicates the game runtime FaceMaterialSupplier)
                var tex = bundle.LoadAsset<Texture2D>(job.textureObjectName);
                if (tex == null)
                    tex = bundle.LoadAllAssets<Texture2D>()
                        .FirstOrDefault(x => string.Equals(x.name, job.textureObjectName, StringComparison.OrdinalIgnoreCase));
                if (tex == null) throw new Exception("texture not found: " + job.textureObjectName);
                int applied = 0;
                foreach (var r in head.GetComponentsInChildren<Renderer>(true))
                    foreach (var m in r.materials)
                        if (m.name.ToLower().Contains("face") && m.HasProperty("_MainTex"))
                        {
                            m.SetTexture("_MainTex", tex);
                            applied++;
                        }
                log.AppendLine("texture assigned x" + applied + " (" + tex.name + " " + tex.width + "x" + tex.height + ")");

                // SMR -> static MeshRenderer (edit mode bone matrices are zero)
                var smrs = head.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                MeshRenderer faceMr = null;
                int faceVc = -1;
                foreach (var smr in smrs)
                {
                    if (smr.sharedMesh == null || smr.sharedMesh.vertexCount == 0) continue;
                    if (faceMr != null && smr.sharedMesh.vertexCount <= faceVc) continue;
                    var st = new GameObject(smr.name + "_static");
                    var srcT = smr.rootBone != null ? smr.rootBone.transform : smr.transform;
                    st.transform.SetParent(head.transform, false);
                    st.layer = head.layer;
                    var mf = st.AddComponent<MeshFilter>();
                    mf.sharedMesh = smr.sharedMesh;
                    var verts = smr.sharedMesh.vertices;
                    if (verts != null && verts.Length > 0)
                    {
                        var mn = verts[0]; var mx = verts[0];
                        foreach (var v in verts) { mn = Vector3.Min(mn, v); mx = Vector3.Max(mx, v); }
                        smr.sharedMesh.bounds = new Bounds((mn + mx) * 0.5f, mx - mn);
                    }
                    var rel = head.transform.worldToLocalMatrix * srcT.localToWorldMatrix;
                    st.transform.localPosition = rel.GetColumn(3);
                    st.transform.localRotation = Quaternion.Euler(0f, 180f, 0f) * Quaternion.Euler(-90f, 0f, 0f) * Quaternion.Euler(0f, -90f, 0f) * rel.rotation * Quaternion.Euler(90f, 0f, 0f);
                    st.transform.localScale = rel.lossyScale;
                    Vector3 headW0 = st.transform.TransformPoint(mf.sharedMesh.bounds.center);
                    st.transform.localRotation = Quaternion.Euler(0f, 0f, 180f) * st.transform.localRotation;
                    Vector3 headW1 = st.transform.TransformPoint(mf.sharedMesh.bounds.center);
                    st.transform.position += headW0 - headW1;
                    var mr = st.AddComponent<MeshRenderer>();
                    mr.sharedMaterials = smr.sharedMaterials;
                    if (faceMr == null || smr.sharedMesh.vertexCount > faceVc)
                    {
                        faceMr = mr;
                        faceVc = smr.sharedMesh.vertexCount;
                    }
                    UnityEngine.Object.DestroyImmediate(smr);
                }
                if (faceMr == null) throw new Exception("no SMR convertible to static");

                var headC = faceMr.transform.TransformPoint(faceMr.GetComponent<MeshFilter>().sharedMesh.bounds.center);
                var d = faceMr.GetComponent<MeshFilter>().sharedMesh.bounds.extents.magnitude * 3.5f + 0.05f;

                var captures = new List<string>();
                foreach (var (dirDeg, tag) in new (float, string)[] { (0f, "front"), (45f, "45L"), (315f, "45R"), (90f, "side") })
                {
                    var rad = dirDeg * Mathf.Deg2Rad;
                    cam.transform.position = headC + new Vector3(Mathf.Sin(rad) * d, 0f, Mathf.Cos(rad) * d);
                    cam.transform.LookAt(headC);
                    var fn = "dash_" + tag + ".png";
                    Capture(cam, Path.Combine(outDir, fn));
                    captures.Add(fn);
                }

                var done = new StringBuilder();
                done.AppendLine("{");
                done.AppendLine("  \"ok\": true,");
                done.AppendLine("  \"face\": \"" + job.faceAssetName + "\",");
                done.AppendLine("  \"texture\": \"" + tex.name + "\",");
                done.AppendLine("  \"textureAssigned\": " + applied + ",");
                done.AppendLine("  \"captures\": [" + string.Join(",", captures.Select(c => "\"" + c + "\"")) + "]");
                done.AppendLine("}");
                File.WriteAllText(Path.Combine(outDir, "render_done.json"), done.ToString());
                File.WriteAllText(Path.Combine(outDir, "render_log.txt"), log.ToString());
                Debug.Log("[DashboardRender] OK");
            }
            catch (Exception ex)
            {
                try
                {
                    File.WriteAllText(Path.Combine(outDir, "render_done.json"),
                        "{\n  \"ok\": false,\n  \"error\": \"" + ex.Message.Replace("\"", "'") + "\"\n}");
                    File.WriteAllText(Path.Combine(outDir, "render_log.txt"), log.ToString() + "\nERROR: " + ex);
                }
                catch { /* best effort */ }
                Debug.LogError("[DashboardRender] FAILED: " + ex);
            }
            EditorApplication.Exit(0);
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
