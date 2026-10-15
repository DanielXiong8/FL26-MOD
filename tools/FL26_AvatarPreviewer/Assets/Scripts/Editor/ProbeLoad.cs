using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace FL26Previewer.EditorTools
{
    /// <summary>One-shot diagnostic: which bundles can this editor actually load?</summary>
    public static class ProbeLoad
    {
        public static void Run()
        {
            var log = new System.Text.StringBuilder();
            log.AppendLine("=== ProbeLoad " + DateTime.Now + " ===");
            log.AppendLine("activeBuildTarget=" + EditorUserBuildSettings.activeBuildTarget);

            // 1) Build a tiny bundle with THIS editor (Android target) and load it back.
            try
            {
                string tempDir = "Assets/ProbeBuild";
                if (!Directory.Exists(tempDir)) Directory.CreateDirectory(tempDir);
                var mat = new Material(Shader.Find("Unlit/Texture")) { name = "probeMat" };
                AssetDatabase.CreateAsset(mat, tempDir + "/probeMat.asset");
                AssetDatabase.SaveAssets();
                var opts = new BuildAssetBundleOptions();
                string outPath = Path.Combine(tempDir, "probebundle.android");
                BuildPipeline.BuildAssetBundles(Path.GetFullPath(tempDir), opts, BuildTarget.Android);
                log.AppendLine("editorBuiltBundleExists=" + File.Exists(Path.GetFullPath(tempDir + "/probebundle.android")));
                TryLoad(Path.GetFullPath(tempDir + "/probebundle.android"), "editor-built(android)", log);
            }
            catch (Exception ex) { log.AppendLine("editor-build probe FAILED: " + ex.Message); }

            // 2) Native game bundles (straight from APK).
            TryLoad(@"D:\FL26_Mod\build\gamedata.unity3d", "gamedata(native)", log);
            TryLoad(@"D:\FL26_Mod\build\avatar.unity3d", "avatar(native)", log);

            // 3) UnityPy-rewritten clean copy.
            TryLoad(@"D:\FL26_Mod\tools\FL26_AvatarPreviewer\extracted\avatar_clean.unity3d", "avatar_clean(rewritten)", log);

            File.WriteAllText(@"D:\FL26_Mod\tools\FL26_AvatarPreviewer\probe_result.txt", log.ToString());
            Debug.Log("[ProbeLoad]\n" + log);
            EditorApplication.Exit(0);
        }

        static void TryLoad(string path, string label, System.Text.StringBuilder log)
        {
            try
            {
                if (!File.Exists(path)) { log.AppendLine(label + ": FILE MISSING " + path); return; }
                var ab = AssetBundle.LoadFromFile(path);
                if (ab == null) { log.AppendLine(label + ": LOAD FAILED"); return; }
                var names = ab.GetAllAssetNames();
                log.AppendLine(label + ": LOADED, assets=" + names.Length + " first=" + string.Join(",", names.Take(3)));
                ab.Unload(true);
            }
            catch (Exception ex)
            {
                log.AppendLine(label + ": EXCEPTION " + ex.Message);
            }
        }
    }
}
