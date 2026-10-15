// Frida hook script for FL26 Mod — intercept CalculateImageSavePath
// to discover the actual icon save path

console.log("[*] FL26 Frida hook starting...");

// Find libil2cpp.so base address
var il2cpp = Process.findModuleByName("libil2cpp.so");
if (!il2cpp) {
    console.log("[!] libil2cpp.so not found, waiting...");
    setTimeout(function() {
        il2cpp = Process.findModuleByName("libil2cpp.so");
        if (il2cpp) {
            console.log("[+] libil2cpp.so found at " + il2cpp.base);
            hookMethods(il2cpp.base);
        } else {
            console.log("[!] still not found");
        }
    }, 3000);
} else {
    console.log("[+] libil2cpp.so at " + il2cpp.base);
    hookMethods(il2cpp.base);
}

function hookMethods(base) {
    // RVA from dump.cs
    var RVA_CalculateImageSavePath_Archives = 0xD65A58;
    var RVA_CalculateImageSavePath_Agent = 0xD63750;
    var RVA_CalculateKey = 0xD659E8;
    var RVA_EditablePlayerIcon_Save = 0x11FE79C;
    var RVA_EditablePlayerIcon_IsCustom = 0x11FE830; // approximate
    var RVA_LoadFromFile = 0xD65248;

    // Helper to read IL2CPP string (System.String)
    function readIl2CppString(ptr) {
        if (ptr.isNull()) return "null";
        try {
            var len = ptr.add(0x10).readS32();  // String.length at offset 0x10
            var chars = ptr.add(0x14);           // String.chars at offset 0x14
            return chars.readUtf16String(len);
        } catch(e) {
            return "<error: " + e + ">";
        }
    }

    // Hook CalculateImageSavePath (ExternalDataArchives version)
    var addr1 = base.add(RVA_CalculateImageSavePath_Archives);
    console.log("[*] Hooking CalculateImageSavePath(Archives) at " + addr1);
    Interceptor.attach(addr1, {
        onEnter: function(args) {
            this.type = args[0].toInt32();
            this.id = args[1].toInt32();
            this.detailType = args[2].toInt32();
            console.log("[CalculateImageSavePath] type=" + this.type + " id=" + this.id + " detailType=" + this.detailType);
        },
        onLeave: function(retval) {
            var path = readIl2CppString(retval);
            console.log("[CalculateImageSavePath] RETURN: " + path);
            console.log("[CalculateImageSavePath] type=" + this.type + " id=" + this.id + " => " + path);
        }
    });

    // Hook CalculateImageSavePath (ExternalDataAgent version)
    var addr2 = base.add(RVA_CalculateImageSavePath_Agent);
    console.log("[*] Hooking CalculateImageSavePath(Agent) at " + addr2);
    Interceptor.attach(addr2, {
        onEnter: function(args) {
            this.type = args[0].toInt32();
            this.id = args[1].toInt32();
            this.detailType = args[2].toInt32();
            console.log("[Agent.CalculateImageSavePath] type=" + this.type + " id=" + this.id + " detailType=" + this.detailType);
        },
        onLeave: function(retval) {
            var path = readIl2CppString(retval);
            console.log("[Agent.CalculateImageSavePath] RETURN: " + path);
        }
    });

    // Hook CalculateKey
    var addr3 = base.add(RVA_CalculateKey);
    console.log("[*] Hooking CalculateKey at " + addr3);
    Interceptor.attach(addr3, {
        onEnter: function(args) {
            this.type = args[0].toInt32();
            this.id = args[1].toInt32();
            console.log("[CalculateKey] type=" + this.type + " id=" + this.id);
        },
        onLeave: function(retval) {
            console.log("[CalculateKey] RETURN: " + retval.toInt32());
        }
    });

    // Hook EditablePlayerIcon.Save
    var addr4 = base.add(RVA_EditablePlayerIcon_Save);
    console.log("[*] Hooking EditablePlayerIcon.Save at " + addr4);
    Interceptor.attach(addr4, {
        onEnter: function(args) {
            console.log("[EditablePlayerIcon.Save] called!");
            // args[0] = this, args[1] = byte[] datas, args[2] = Texture2D
            if (!args[1].isNull()) {
                try {
                    var len = args[1].add(0x18).readS32();  // Array.length
                    console.log("[EditablePlayerIcon.Save] data length=" + len);
                } catch(e) {}
            }
        }
    });

    // Hook LoadFromFile (to find setting file path)
    var addr5 = base.add(RVA_LoadFromFile);
    console.log("[*] Hooking LoadFromFile at " + addr5);
    Interceptor.attach(addr5, {
        onEnter: function(args) {
            // args[0] = this, args[1] = path string
            if (!args[1].isNull()) {
                var path = readIl2CppString(args[1]);
                console.log("[LoadFromFile] path=" + path);
            }
        }
    });

    console.log("[*] All hooks installed");
}
