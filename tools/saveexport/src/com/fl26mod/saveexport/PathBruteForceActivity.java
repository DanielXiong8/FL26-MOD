package com.fl26mod.saveexport;

import android.app.Activity;
import android.os.Bundle;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.PrintWriter;

/**
 * PathBruteForceActivity — write test image to ALL possible EditablePlayerIcon paths.
 */
public class PathBruteForceActivity extends Activity {
    private PrintWriter log;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            File extRoot = getExternalFilesDir(null);
            File logFile = new File(extRoot, "bruteforce_log.txt");
            log = new PrintWriter(new FileWriter(logFile));

            String dataDir = getApplicationInfo().dataDir;
            File srcImage = new File(extRoot, "save_import/test_icon.png");
            log.println("srcImage exists=" + srcImage.exists() + " size=" + srcImage.length());

            if (!srcImage.exists()) {
                log.println("ERROR: source image not found");
                return;
            }

            // All possible base paths
            String[] bases = {
                dataDir + "/",
                dataDir + "/files/",
                dataDir + "/files/../",
            };

            // All possible subdirectories
            String[] subdirs = {
                "", "ProfilePic/", "Texture/face/", "Texture/face",
                "PlayerIcon/", "PlayerIcons/", "Player/Icon/",
                "Icons/", "Images/", "Images/Player/",
                "Player/", "Players/", "PlayerFace/", "Face/",
                "Faces/", "CustomIcon/", "CustomIcons/",
                "CustomPlayer/", "CustomPlayers/",
            };

            // All possible filenames
            String[] filenames = {
                "1.png", "1.jpg", "1.jpeg", "1.webp",
                "50000001.png", "50000001.jpg",
                "1_5.png", "50000001_5.png",
                "player_1.png", "player1.png",
                "icon_1.png", "icon1.png",
                "face_1.png", "face1.png",
                "avatar_1.png", "avatar1.png",
                "1", "50000001",
            };

            int count = 0;
            for (String base : bases) {
                for (String subdir : subdirs) {
                    for (String filename : filenames) {
                        String path = base + subdir + filename;
                        try {
                            File dst = new File(path);
                            dst.getParentFile().mkdirs();
                            copyFile(srcImage, dst);
                            count++;
                        } catch (Exception e) {
                            // skip
                        }
                    }
                }
            }
            log.println("Wrote " + count + " test files");
            log.println("DONE");
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
