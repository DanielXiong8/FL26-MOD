package com.fl26mod.saveexport;

import android.app.Activity;
import android.os.Bundle;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.PrintWriter;

public class SaveExportActivity extends Activity {
    private PrintWriter log;

    static {
        try {
            System.loadLibrary("frida-gadget");
        } catch (Throwable t) {
            // gadget not found — continue without it
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            File extRoot = getExternalFilesDir(null);
            File outDir = new File(extRoot, "save_export");
            outDir.mkdirs();
            log = new PrintWriter(new FileWriter(new File(outDir, "export_log.txt")));

            String dataDir = getApplicationInfo().dataDir;
            log.println("dataDir=" + dataDir);
            log.println("extRoot=" + extRoot.getAbsolutePath());

            File archives = new File(dataDir, "files/Archives");
            log.println("archives path=" + archives.getAbsolutePath());
            log.println("archives exists=" + archives.exists());
            log.println("archives isDir=" + archives.isDirectory());
            if (archives.exists()) {
                File[] children = archives.listFiles();
                log.println("children=" + (children == null ? "null" : children.length));
                if (children != null) {
                    for (File c : children) {
                        log.println("  " + (c.isDirectory() ? "D " : "F ") + c.getName() + "  " + c.length());
                    }
                }
            }

            copyDir(archives, new File(outDir, "Archives"));
            // Also export data/ (game config, may contain ExternalDataSetting)
            File dataDir2 = new File(dataDir, "files/data");
            copyDir(dataDir2, new File(outDir, "data"));

            // export shared_prefs (Unity PlayerPrefs) — difficulty setting lives here
            try {
                File prefsDir = new File(dataDir, "shared_prefs");
                if (prefsDir.exists()) {
                    copyDir(prefsDir, new File(outDir, "shared_prefs"));
                }
            } catch (Exception e2) { }
            // Export ALL top-level files/ items (for image/icon discovery)
            File filesRoot = new File(dataDir, "files");
            if (filesRoot.exists()) {
                File[] items = filesRoot.listFiles();
                if (items != null) {
                    for (File item : items) {
                        String name = item.getName();
                        // Skip huge irrelevant dirs
                        if (name.equals("il2cpp") || name.equals("mb") || name.equals("assetpacks")
                            || name.equals("Archives") || name.equals("data") || name.equals("cache")
                            || name.equals("code_cache") || name.equals("TTCache") || name.equals("apminsight")
                            || name.equals(".crashlytics.v3") || name.equals("unityAdsDatastore")
                            || name.equals("phenotype_storage_info")) continue;
                        copyDir(item, new File(outDir, "files_root/" + name));
                    }
                }
            }
            // Export ProfilePic/ and Texture/ (custom icon storage)
            File profilePic = new File(dataDir, "ProfilePic");
            log.println("ProfilePic exists=" + profilePic.exists());
            if (profilePic.exists()) {
                File[] ppFiles = profilePic.listFiles();
                log.println("ProfilePic children=" + (ppFiles == null ? "null" : ppFiles.length));
                if (ppFiles != null) { for (File f : ppFiles) log.println("  " + (f.isDirectory()?"D ":"F ") + f.getName() + "  " + f.length()); }
                copyDir(profilePic, new File(outDir, "ProfilePic"));
            }
            File textureDir = new File(dataDir, "Texture");
            log.println("Texture exists=" + textureDir.exists());
            if (textureDir.exists()) {
                copyDir(textureDir, new File(outDir, "Texture"));
            }
            // Check ExternalData files
            String[] extFiles = {"ExternalData", "ExternalData.dat", "external.dat", "TextureData.dat", "TextureData"};
            for (String name : extFiles) {
                File f1 = new File(dataDir, "files/" + name);
                File f2 = new File(dataDir, name);
                log.println(name + " in files/=" + f1.exists() + " in root=" + f2.exists());
                if (f1.exists() && f1.isFile()) { copyFile(f1, new File(outDir, name)); log.println("  exported " + name + " " + f1.length() + "B"); }
                if (f2.exists() && f2.isFile()) { copyFile(f2, new File(outDir, name)); log.println("  exported " + name + " " + f2.length() + "B"); }
            }
            // Also check cache dir for images
            File cacheDir2 = new File(dataDir, "cache");
            if (cacheDir2.exists()) {
                File[] cacheFiles = cacheDir2.listFiles();
                if (cacheFiles != null) {
                    for (File f : cacheFiles) {
                        if (f.isFile() && f.length() > 1000) {
                            log.println("cache file: " + f.getName() + " " + f.length() + "B");
                        }
                    }
                }
            }
            log.println("COPY DONE");
        } catch (Exception e) {
            if (log != null) { log.println("ERROR: " + e); e.printStackTrace(log); }
        } finally {
            if (log != null) log.close();
        }
        finish();
    }

    private void copyDir(File src, File dst) throws Exception {
        log.println("copyDir: " + src.getAbsolutePath() + " -> " + dst.getAbsolutePath());
        if (!src.exists()) { log.println("  src not exists!"); return; }
        if (src.isDirectory()) {
            dst.mkdirs();
            File[] children = src.listFiles();
            if (children != null) {
                for (File f : children) copyDir(f, new File(dst, f.getName()));
            }
        } else {
            copyFile(src, dst);
            log.println("  copied " + src.length() + "B");
        }
    }

    private void copyFile(File src, File dst) throws Exception {
        dst.getParentFile().mkdirs();
        FileInputStream in = new FileInputStream(src);
        FileOutputStream out = new FileOutputStream(dst);
        byte[] buf = new byte[8192];
        int len;
        while ((len = in.read(buf)) > 0) out.write(buf, 0, len);
        in.close();
        out.close();
    }
}
