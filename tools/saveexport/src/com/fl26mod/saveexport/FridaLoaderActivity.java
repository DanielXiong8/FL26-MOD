package com.fl26mod.saveexport;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;

/**
 * FridaLoaderActivity — loads Frida gadget + diagnostics
 */
public class FridaLoaderActivity extends Activity {
    private static boolean gadgetLoaded = false;

    static {
        try {
            System.loadLibrary("frida-gadget");
            gadgetLoaded = true;
        } catch (Throwable t) {
            gadgetLoaded = false;
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            File extRoot = getExternalFilesDir(null);
            PrintWriter log = new PrintWriter(new FileWriter(new File(extRoot, "frida_diag.txt")));

            log.println("gadgetLoaded=" + gadgetLoaded);
            log.println("nativeLibDir=" + getApplicationInfo().nativeLibraryDir);

            // Check if config file exists
            File nativelib = new File(getApplicationInfo().nativeLibraryDir);
            if (nativelib.exists()) {
                File[] libs = nativelib.listFiles();
                if (libs != null) {
                    for (File f : libs) {
                        if (f.getName().contains("frida")) {
                            log.println("found: " + f.getName() + " " + f.length() + "B");
                        }
                    }
                }
            }

            // Check script file
            File script = new File("/data/local/tmp/frida_hook.js");
            log.println("script exists=" + script.exists() + " readable=" + script.canRead() + " size=" + script.length());

            // Check /data/local/tmp/ config
            File cfg1 = new File("/data/local/tmp/frida-gadget.config");
            log.println("/data/local/tmp/frida-gadget.config exists=" + cfg1.exists());

            // Write a test file to verify we can write
            try {
                File test = new File(extRoot, "frida_test_write.txt");
                FileWriter w = new FileWriter(test);
                w.write("test");
                w.close();
                log.println("write test OK");
            } catch (Exception e) {
                log.println("write test FAILED: " + e);
            }

            log.println("DONE");
            log.close();
        } catch (Exception e) {
            e.printStackTrace();
        }

        // Launch the game's main activity
        try {
            Intent game = new Intent();
            game.setClassName("com.football.soccer.league.mod",
                              "com.androidgamegou.androidutils.AndroidUtils");
            game.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(game);
        } catch (Exception e) {
            // fallback
        }
        // Don't finish — keep process alive
    }
}
