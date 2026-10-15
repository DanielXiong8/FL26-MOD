package com.fl26mod.saveexport;

import android.app.Activity;
import android.os.Bundle;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.PrintWriter;

/**
 * TestIconActivity — write a test image to candidate EditablePlayerIcon paths.
 * Tries multiple path patterns to discover the correct one.
 */
public class TestIconActivity extends Activity {
    private PrintWriter log;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            File extRoot = getExternalFilesDir(null);
            File logFile = new File(extRoot, "test_icon_log.txt");
            log = new PrintWriter(new FileWriter(logFile));

            String dataDir = getApplicationInfo().dataDir;
            File srcImage = new File(extRoot, "save_import/test_icon.png");
            log.println("srcImage=" + srcImage.getAbsolutePath() + " exists=" + srcImage.exists() + " size=" + srcImage.length());

            if (!srcImage.exists()) {
                log.println("ERROR: source image not found");
                return;
            }

            // Candidate paths to try
            String[] candidates = {
                // Pattern 1: ProfilePic with CalculateKey
                dataDir + "/ProfilePic/50000001.png",
                // Pattern 2: ProfilePic with player_id only
                dataDir + "/ProfilePic/1.png",
                // Pattern 3: ProfilePic with detailType
                dataDir + "/ProfilePic/50000001_5.png",
                // Pattern 4: Texture/face with CalculateKey
                dataDir + "/files/Texture/face/50000001.png",
                // Pattern 5: Texture/face with player_id
                dataDir + "/files/Texture/face/1.png",
                // Pattern 6: direct in files root
                dataDir + "/files/ProfilePic/50000001.png",
                dataDir + "/files/ProfilePic/1.png",
            };

            for (String path : candidates) {
                try {
                    File dst = new File(path);
                    dst.getParentFile().mkdirs();
                    copyFile(srcImage, dst);
                    log.println("OK: " + path + " (" + dst.length() + "B)");
                } catch (Exception e) {
                    log.println("FAIL: " + path + " -> " + e.getMessage());
                }
            }
            log.println("ALL DONE");
        } catch (Exception e) {
            if (log != null) { log.println("FATAL: " + e); e.printStackTrace(log); }
        } finally {
            if (log != null) log.close();
        }
        finish();
    }

    private void copyFile(File src, File dst) throws Exception {
        FileInputStream in = new FileInputStream(src);
        FileOutputStream out = new FileOutputStream(dst);
        byte[] buf = new byte[8192];
        int len;
        while ((len = in.read(buf)) > 0) out.write(buf, 0, len);
        in.close();
        out.close();
    }
}
