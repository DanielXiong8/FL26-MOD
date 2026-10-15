# -*- coding: utf-8 -*-
"""axml_add_activity_aligned.py - same manifest+dex injection as
scripts/axml_add_activity.py but sourced from the ALIGNED build
(fl26_pl_align.apk), declaring only the two live tool activities.
Output: build/_tmp_align_tools_raw.apk (to be zipaligned + signed afterwards).
"""
import os, sys
sys.path.insert(0, r'D:\FL26_Mod\scripts')
import axml_add_activity as A

A.SRC = r'D:\FL26_Mod\build\fl26_pl_align.apk'
A.DST = r'D:\FL26_Mod\build\_tmp_align_tools_raw.apk'
A.DEX_SRC = r'D:\FL26_Mod\tools\saveexport\dex\classes.dex'
A.ACTIVITIES = [
    'com.fl26mod.saveexport.SaveExportActivity',
    'com.fl26mod.saveexport.SaveImportActivity',
]
sys.exit(A.main())
