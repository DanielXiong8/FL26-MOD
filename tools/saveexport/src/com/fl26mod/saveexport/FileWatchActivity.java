package com.fl26mod.saveexport;

import android.app.Activity;
import android.os.Bundle;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;

/**
 * FileWatchActivity — recursively list ALL files in the app's data directory
 * with timestamps, to find recently created/modified files.
 */
public class FileWatchActivity extends Activity {
    private PrintWriter log;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            File extRoot = getExternalFilesDir(null);
            File logFile = new File(extRoot, "filewatch_log.txt");
            log = new PrintWriter(new FileWriter(logFile));

            String dataDir = getApplicationInfo().dataDir;
            log.println("dataDir=" + dataDir);
            log.println("time=" + System.currentTimeMillis());
            log.println("---");

            // List ALL files recursively, sorted by modification time
            listRecursive(new File(dataDir), "", 0);

            log.println("---END---");
        } catch (Exception e) {
            if (log != null) { log.println("ERROR: " + e); e.printStackTrace(log); }
        } finally {
            if (log != null) log.close();
        }
        finish();
    }

    private void listRecursive(File f, String prefix, int depth) {
        if (depth > 8) return;
        if (!f.exists()) return;

        if (f.isFile()) {
            // Only log files that might be images or recently modified
            long mod = f.lastModified();
            long now = System.currentTimeMillis();
            long ageHours = (now - mod) / (1000 * 60 * 60);
            String name = f.getName().toLowerCase();
            boolean isImage = name.endsWith(".png") || name.endsWith(".jpg") || 
                             name.endsWith(".jpeg") || name.endsWith(".webp") ||
                             name.endsWith(".bmp") || name.endsWith(".gif");
            boolean isRecent = ageHours < 24;
            boolean isSmall = f.length() < 1024 * 1024; // < 1MB

            if (isImage || (isRecent && isSmall)) {
                log.println(prefix + "F " + f.getAbsolutePath().substring(f.getAbsolutePath().indexOf("com.football")) + 
                           "  " + f.length() + "B  mod=" + mod + "  age=" + ageHours + "h");
            }
            return;
        }

        // Directory
        File[] children = f.listFiles();
        if (children == null) return;
        String dirName = f.getName();
        // Skip huge system dirs
        if (dirName.equals("il2cpp") || dirName.equals("mb") || dirName.equals("cache") || 
            dirName.equals("code_cache") || dirName.equals("no_backup") ||
            dirName.equals("app_textures") || dirName.equals("app_webview")) {
            return;
        }
        for (File child : children) {
            listRecursive(child, prefix + "  ", depth + 1);
        }
    }
}
