package com.fl26mod.saveexport;

import android.app.Activity;
import android.os.Bundle;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.PrintWriter;

public class SaveImportActivity extends Activity {
    private PrintWriter log;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            File extRoot = getExternalFilesDir(null);
            File logFile = new File(extRoot, "save_import/import_log.txt");
            logFile.getParentFile().mkdirs();
            log = new PrintWriter(new FileWriter(logFile));

            String dataDir = getApplicationInfo().dataDir;
            File importDir = new File(extRoot, "save_import/Archives");
            log.println("dataDir=" + dataDir);
            log.println("importDir=" + importDir.getAbsolutePath());
            log.println("importDir exists=" + importDir.exists());

            if (importDir.exists()) {
                File targetDir = new File(dataDir, "files/Archives");
                log.println("targetDir=" + targetDir.getAbsolutePath());
                copyDir(importDir, targetDir);
                log.println("IMPORT DONE");
            } else {
                log.println("NOTHING TO IMPORT (Archives)");
            }

            // restore top-level files (player.dat etc) from save_import/files_root
            File filesRoot = new File(extRoot, "save_import/files_root");
            if (filesRoot.exists()) {
                File targetDir = new File(dataDir, "files");
                log.println("files_root import -> " + targetDir.getAbsolutePath());
                copyDir(filesRoot, targetDir);
                log.println("FILES_ROOT IMPORT DONE");
            }

            // single-file convenience: save_import_files/player.dat
            File single = new File(extRoot, "save_import_files/player.dat");
            if (single.exists()) {
                File target = new File(dataDir, "files/player.dat");
                copyFile(single, target);
                log.println("player.dat imported, " + single.length() + "B");
            }
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
