using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace FL26Previewer
{
    /// <summary>
    /// FL26 Avatar Previewer - minimal bootstrap.
    /// Unity 2020.3.49f1, Built-in Render Pipeline only.
    /// No scene asset required: runs via RuntimeInitializeOnLoadMethod in Play Mode.
    ///
    /// Controls:
    ///   Mouse drag      : rotate
    ///   Mouse wheel     : zoom
    ///   1/2/3/4         : front / 45L / 45R / side camera
    ///   N               : next face avatar (face_EastAsia_new1..new6)
    ///   C               : load candidate texture (candidateTexturePath)
    ///   R               : reset transform
    ///   P               : screenshot -> runs/preview/
    ///   Esc             : quit
    /// </summary>
    public class PreviewerBootstrap : MonoBehaviour
    {
        // ---- Configurable paths ----
        // FL26 project root discovery (legacy hardcoded C:\FL26_Mod paths removed after the C->D migration):
        //   1. FL26_PROJECT_ROOT environment variable (explicit override)
        //   2. Walk up from this Unity project dir (tools/FL26_AvatarPreviewer) to the ancestor
        //      that contains build/avatar.unity3d  ->  PROJECT_ROOT (currently D:\FL26_Mod)
        //   3. Fallback: this Unity project dir itself (extracted/ copies)
        public static string UnityProjectDir { get { return Path.GetFullPath(Path.Combine(Application.dataPath, "..")); } }
        public static string OutputDir { get { return Path.Combine(UnityProjectDir, "runs", "preview"); } }

        static string fl26RootCache;
        public static string Fl26ProjectRoot
        {
            get
            {
                if (fl26RootCache != null) return fl26RootCache;
                string env = Environment.GetEnvironmentVariable("FL26_PROJECT_ROOT");
                if (!string.IsNullOrEmpty(env) && Directory.Exists(env))
                {
                    fl26RootCache = Path.GetFullPath(env);
                    return fl26RootCache;
                }
                string dir = UnityProjectDir;
                for (int i = 0; i < 6 && !string.IsNullOrEmpty(dir); i++)
                {
                    if (File.Exists(Path.Combine(dir, "build", "avatar.unity3d")))
                    {
                        fl26RootCache = dir;
                        return fl26RootCache;
                    }
                    var parent = Directory.GetParent(dir);
                    dir = parent != null ? parent.FullName : null;
                }
                fl26RootCache = UnityProjectDir;
                return fl26RootCache;
            }
        }

        // Relative candidates resolved against Fl26ProjectRoot first, then UnityProjectDir (first existing wins).
        // Original avatar.unity3d is opened READ-ONLY. extracted/avatar_clean.unity3d is a script-free
        // copy (make_clean_bundle.py) used when the original hard-fails on game MonoBehaviours.
        static readonly string[] bundleCandidates = new string[]
        {
            "build/avatar.unity3d",                 // <PROJECT_ROOT>/build/avatar.unity3d (original FL26 asset)
            "extracted/avatar_mjt.unity3d",         // <UnityProject>/extracted — allchina v5c Ma Jiantao mod bundle (script-free rewrite)
            "extracted/avatar_clean.unity3d",       // <UnityProject>/extracted (script-free rewrite of the original)
            "extracted/avatar.unity3d",             // <UnityProject>/extracted (raw copy if present)
            "extracted/avatar_copy.unity3d",
        };

        // Candidate texture for Gate 9F
        static readonly string[] candidateTextureCandidates = new string[]
        {
            "face_benchmark/runs/test01/candidates/c4/baked.png",  // <PROJECT_ROOT>/face_benchmark/...
        };

        static string ResolveExisting(string rel)
        {
            string full = Path.Combine(Fl26ProjectRoot, rel);
            if (File.Exists(full)) return full;
            full = Path.Combine(UnityProjectDir, rel);
            if (File.Exists(full)) return full;
            return null;
        }

        static readonly string[] faceObjectNames = new string[]
        {
            "face_EastAsia_new1", "face_EastAsia_new2", "face_EastAsia_new3",
            "face_EastAsia_new4", "face_EastAsia_new5", "face_EastAsia_new6"
        };

        AssetBundle bundle;
        GameObject currentAvatar;
        Renderer currentRenderer;
        int faceIndex = 0;
        bool bundleFailed;
        string bundleFailReason = "";

        // filename-without-extension (lowercase) -> full container path, built after bundle load.
        // Game bundles ship lowercase paths while object display names are mixed-case, so
        // LoadAsset by display name alone can miss; the map makes name lookup robust.
        static readonly Dictionary<string, string> assetPathMap = new Dictionary<string, string>();

        void BuildAssetPathMap()
        {
            assetPathMap.Clear();
            foreach (var p in bundle.GetAllAssetNames())
            {
                string key = Path.GetFileNameWithoutExtension(p).ToLowerInvariant();
                if (!assetPathMap.ContainsKey(key)) assetPathMap[key] = p;
            }
            Debug.Log("[FL26Previewer] assetPathMap entries: " + assetPathMap.Count);
        }

        Camera cam;
        GameObject pivot;          // rotation pivot at avatar center
        float yaw = 0f, pitch = 0f, dist = 0.6f;
        Vector3 lastMouse;
        Texture2D candidateTex;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Bootstrap()
        {
            var go = new GameObject("FL26Previewer");
            go.AddComponent<PreviewerBootstrap>();
        }

        void Start()
        {
            // Camera
            var camGo = new GameObject("PreviewCam");
            cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.18f, 0.18f, 0.20f, 1f);
            cam.fieldOfView = 30f;

            // Light (simple built-in directional)
            var lightGo = new GameObject("PreviewLight");
            var li = lightGo.AddComponent<Light>();
            li.type = LightType.Directional;
            li.intensity = 1.0f;
            lightGo.transform.rotation = Quaternion.Euler(35f, 30f, 0f);

            // Pivot at origin; avatar instantiated at origin
            pivot = new GameObject("Pivot");

            Directory.CreateDirectory(OutputDir);
            StartCoroutine(LoadBundleAndReport());
            UpdateCamera();
        }

        System.Collections.IEnumerator LoadBundleAndReport()
        {
            // Load bundle (synchronous LoadFromFile is fine in 2020.3; wrap in coroutine for future-proofing).
            // Cascade: try candidates in order; a candidate that exists but fails to LOAD is skipped.
            string usedPath = null;
            var attempts = new StringBuilder();
            foreach (var rel in bundleCandidates)
            {
                string full = ResolveExisting(rel);
                if (full == null) continue;
                bundle = AssetBundle.LoadFromFile(full);
                if (bundle != null) { usedPath = full; break; }
                attempts.AppendLine("  failed: " + full);
                Debug.LogWarning("[FL26Previewer] candidate exists but LoadFromFile failed: " + full);
            }

            if (usedPath == null)
            {
                bundleFailed = true;
                bundleFailReason = "no loadable candidate among [" + string.Join(" | ", bundleCandidates) + "]" +
                                   (attempts.Length > 0 ? "\nload attempts:\n" + attempts : " (none existed)");
                Debug.LogError("[FL26Previewer] " + bundleFailReason);
                WriteReport();
                yield break;
            }

            Debug.Log("[FL26Previewer] Bundle loaded: " + usedPath);
            BuildAssetPathMap();
            EnumerateAssets();

            if (!LoadFace(faceIndex))
            {
                // GameObject load failed -> try bare Mesh + fallback Unlit material
                LoadMeshFallback(faceIndex);
            }

            WriteReport();
            Screenshot("auto_" + faceObjectNames[faceIndex] + "_front.png");
        }

        void EnumerateAssets()
        {
            var sb = new StringBuilder();
            sb.AppendLine("=== avatar.unity3d asset enumeration ===");
            sb.AppendLine("Time: " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
            sb.AppendLine("isLoaded: true (LoadFromFile is synchronous; bundle != null)");

            sb.AppendLine("--- All asset names/types ---");
            foreach (var name in bundle.GetAllAssetNames())
                sb.AppendLine("asset: " + name);

            var meshes = bundle.LoadAllAssets<Mesh>();
            sb.AppendLine("--- Mesh (" + meshes.Length + ") ---");
            foreach (var m in meshes) sb.AppendLine(m.name + " vc=" + m.vertexCount + " sub=" + m.subMeshCount);

            var texs = bundle.LoadAllAssets<Texture2D>();
            sb.AppendLine("--- Texture2D (" + texs.Length + ") ---");
            foreach (var t in texs) sb.AppendLine(t.name + " " + t.width + "x" + t.height + " wrap=" + t.wrapMode);

            var mats = bundle.LoadAllAssets<Material>();
            sb.AppendLine("--- Material (" + mats.Length + ") ---");
            foreach (var mat in mats)
            {
                Shader sh = mat.shader;
                sb.AppendLine(mat.name + " shader=" + (sh != null ? sh.name : "NULL(pink risk)"));
            }

            var shaders = bundle.LoadAllAssets<Shader>();
            sb.AppendLine("--- Shader (" + shaders.Length + ") ---");
            foreach (var s in shaders) sb.AppendLine(s.name + " supported=" + s.isSupported);

            var gos = bundle.LoadAllAssets<GameObject>();
            sb.AppendLine("--- GameObject (" + gos.Length + ") ---");
            foreach (var g in gos)
                if (g.name.StartsWith("face_") || g.name.StartsWith("head_"))
                    sb.AppendLine(g.name);

            string path = Path.Combine(OutputDir, "asset_enumeration.txt");
            File.WriteAllText(path, sb.ToString());
            Debug.Log("[FL26Previewer] Enumeration -> " + path);
        }

        /// <summary>Per-avatar dependency record (Gate: asset load + UV + shader).</summary>
        string DumpAvatarDeps(GameObject go)
        {
            var sb = new StringBuilder();
            sb.AppendLine("avatar: " + go.name);
            var renderers = go.GetComponentsInChildren<Renderer>();
            foreach (var r in renderers)
            {
                sb.AppendLine("  renderer: " + r.GetType().Name);
                foreach (var mat in r.sharedMaterials)
                {
                    if (mat == null) { sb.AppendLine("    material: NULL"); continue; }
                    Shader sh = mat.shader;
                    sb.AppendLine("    material: " + mat.name + " shader=" + (sh != null ? sh.name : "NULL"));
                    if (sh != null && sh.name == "Hidden/InternalErrorShader")
                        sb.AppendLine("    !! SHADER_FALLBACK_INTERNALERROR (original shader not PC-compatible)");
                    if (mat.HasProperty("_MainTex"))
                    {
                        var tex = mat.GetTexture("_MainTex");
                        sb.AppendLine("    _MainTex: " + (tex != null ? tex.name + " " + tex.width + "x" + tex.height + " wrap=" + tex.wrapMode : "NULL"));
                    }
                    else sb.AppendLine("    no _MainTex property");
                    sb.AppendLine("    shaderKeywords: " + string.Join(",", mat.shaderKeywords));
                }
            }
            var smr = go.GetComponentInChildren<SkinnedMeshRenderer>();
            if (smr != null)
            {
                var m = smr.sharedMesh;
                sb.AppendLine("  SMR mesh: " + (m != null ? m.name + " vc=" + m.vertexCount : "NULL"));
                sb.AppendLine("  bones: " + smr.bones.Length + " rootBone: " + (smr.rootBone != null ? smr.rootBone.name : "NULL"));
            }
            return sb.ToString();
        }

        bool LoadFace(int idx)
        {
            string name = faceObjectNames[idx];
            GameObject asset = bundle.LoadAsset<GameObject>(name);
            if (asset == null && assetPathMap.TryGetValue(name.ToLowerInvariant(), out string path))
                asset = bundle.LoadAsset<GameObject>(path);
            if (asset == null) return false;

            if (currentAvatar != null) Destroy(currentAvatar);
            currentAvatar = Instantiate(asset);
            currentAvatar.SetActive(true); // head prefabs ship inactive; the game activates them at runtime
            currentAvatar.transform.SetParent(pivot.transform, false);

            // Guard: replace broken (pink) shaders with Unlit/Texture so mesh+UV still verifiable
            currentRenderer = currentAvatar.GetComponentInChildren<Renderer>();
            if (currentRenderer != null)
            {
                foreach (var r in currentAvatar.GetComponentsInChildren<Renderer>())
                {
                    foreach (var mat in r.materials)
                    {
                        if (mat.shader == null || mat.shader.name == "Hidden/InternalErrorShader")
                        {
                            Debug.LogWarning("[FL26Previewer] Shader fallback for " + r.name + ": " + (mat.shader == null ? "null" : mat.shader.name) + " -> Unlit/Texture");
                            mat.shader = Shader.Find("Unlit/Texture");
                        }
                    }
                }
            }

            string deps = DumpAvatarDeps(currentAvatar);
            File.WriteAllText(Path.Combine(OutputDir, "deps_" + name + ".txt"), deps);
            Debug.Log("[FL26Previewer] Loaded " + name + "\n" + deps);
            return true;
        }

        void LoadMeshFallback(int idx)
        {
            string name = faceObjectNames[idx];
            Mesh mesh = bundle.LoadAsset<Mesh>(name);
            if (mesh == null && assetPathMap.TryGetValue(name.ToLowerInvariant(), out string meshPath))
                mesh = bundle.LoadAsset<Mesh>(meshPath);
            if (mesh == null) { Debug.LogError("[FL26Previewer] Neither GameObject nor Mesh found: " + name); return; }

            if (currentAvatar != null) Destroy(currentAvatar);
            currentAvatar = new GameObject(name);
            currentAvatar.transform.SetParent(pivot.transform, false);
            var mf = currentAvatar.AddComponent<MeshFilter>();
            mf.sharedMesh = mesh;
            var mr = currentAvatar.AddComponent<MeshRenderer>();
            var mat = new Material(Shader.Find("Unlit/Texture"));
            string texName = "face_eastAsia_new" + (idx + 1);
            Texture2D tex = bundle.LoadAsset<Texture2D>(texName);
            if (tex != null) mat.mainTexture = tex;
            mr.sharedMaterial = mat;
            currentRenderer = mr;
            Debug.LogWarning("[FL26Previewer] Mesh fallback path used for " + name + " (GameObject asset missing)");
        }

        void LoadCandidateTexture()
        {
            string used = null;
            foreach (var rel in candidateTextureCandidates)
            {
                used = ResolveExisting(rel);
                if (used != null) break;
            }
            if (used == null) { Debug.LogError("[FL26Previewer] candidate texture not found: " + string.Join(" | ", candidateTextureCandidates)); return; }

            candidateTex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            candidateTex.LoadImage(File.ReadAllBytes(used));
            candidateTex.wrapMode = TextureWrapMode.Clamp;

            var target = currentRenderer != null ? currentRenderer : FindObjectOfType<Renderer>();
            if (target != null)
            {
                var mat = target.material;
                if (mat.HasProperty("_MainTex")) mat.SetTexture("_MainTex", candidateTex);
                else mat.mainTexture = candidateTex;
                Debug.Log("[FL26Previewer] Candidate texture applied: " + used);
                Screenshot("candidate_c4_" + faceObjectNames[faceIndex] + "_front.png");
            }
        }

        void NextFace()
        {
            faceIndex = (faceIndex + 1) % faceObjectNames.Length;
            if (!LoadFace(faceIndex)) LoadMeshFallback(faceIndex);
        }

        void UpdateCamera()
        {
            float rad = yaw * Mathf.Deg2Rad;
            var offset = new Vector3(Mathf.Sin(rad), 0f, Mathf.Cos(rad));
            // apply pitch around horizontal
            var dir = Quaternion.Euler(-pitch, yaw, 0f) * Vector3.forward;
            cam.transform.position = pivot.transform.position - dir * dist;
            cam.transform.LookAt(pivot.transform.position);
        }

        void SetFixedView(int v)
        {
            switch (v)
            {
                case 1: yaw = 0f; pitch = 0f; break;    // front
                case 2: yaw = -45f; pitch = 0f; break;  // 45L
                case 3: yaw = 45f; pitch = 0f; break;   // 45R
                case 4: yaw = 90f; pitch = 0f; break;   // side
            }
            UpdateCamera();
        }

        void Screenshot(string filename)
        {
            StartCoroutine(ScreenshotCo(filename));
        }

        System.Collections.IEnumerator ScreenshotCo(string filename)
        {
            yield return new WaitForEndOfFrame();
            int w = Screen.width, h = Screen.height;
            var rt = new RenderTexture(w, h, 24);
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var read = new Texture2D(w, h, TextureFormat.RGB24, false);
            read.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            read.Apply();
            cam.targetTexture = null;
            RenderTexture.active = null;
            Destroy(rt);
            File.WriteAllBytes(Path.Combine(OutputDir, filename), read.EncodeToPNG());
            Destroy(read);
            Debug.Log("[FL26Previewer] Screenshot -> " + Path.Combine(OutputDir, filename));
        }

        void WriteReport()
        {
            var sb = new StringBuilder();
            sb.AppendLine("fl26ProjectRoot=" + Fl26ProjectRoot);
            sb.AppendLine("unityProjectDir=" + UnityProjectDir);
            sb.AppendLine("bundleLoaded=" + (bundle != null));
            sb.AppendLine("bundleFailed=" + bundleFailed);
            sb.AppendLine("failReason=" + bundleFailReason);
            sb.AppendLine("currentAvatar=" + (currentAvatar != null ? currentAvatar.name : "NONE"));
            File.WriteAllText(Path.Combine(OutputDir, "load_state.txt"), sb.ToString());
        }

        void Update()
        {
            // rotate with left mouse drag
            if (Input.GetMouseButtonDown(0)) lastMouse = Input.mousePosition;
            if (Input.GetMouseButton(0))
            {
                var d = Input.mousePosition - lastMouse;
                yaw += d.x * 0.4f;
                pitch = Mathf.Clamp(pitch + d.y * 0.4f, -80f, 80f);
                lastMouse = Input.mousePosition;
                UpdateCamera();
            }
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            if (Mathf.Abs(scroll) > 0.0001f)
            {
                dist = Mathf.Clamp(dist * (1f - scroll * 1.2f), 0.15f, 3f);
                UpdateCamera();
            }

            if (Input.GetKeyDown(KeyCode.Alpha1)) SetFixedView(1);
            if (Input.GetKeyDown(KeyCode.Alpha2)) SetFixedView(2);
            if (Input.GetKeyDown(KeyCode.Alpha3)) SetFixedView(3);
            if (Input.GetKeyDown(KeyCode.Alpha4)) SetFixedView(4);
            if (Input.GetKeyDown(KeyCode.N)) NextFace();
            if (Input.GetKeyDown(KeyCode.C)) LoadCandidateTexture();
            if (Input.GetKeyDown(KeyCode.R)) { yaw = 0; pitch = 0; dist = 0.6f; UpdateCamera(); }
            if (Input.GetKeyDown(KeyCode.P)) Screenshot("manual_" + faceObjectNames[faceIndex] + "_view.png");
            if (Input.GetKeyDown(KeyCode.Escape)) { Application.Quit(); }
        }

        void OnDestroy()
        {
            if (bundle != null) bundle.Unload(false);
        }
    }
}
