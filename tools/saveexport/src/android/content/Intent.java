package android.content;

public class Intent {
    public static final int FLAG_ACTIVITY_NEW_TASK = 0x10000000;
    public Intent() {}
    public Intent setClassName(String pkg, String cls) { return this; }
    public Intent addFlags(int flags) { return this; }
    public Intent setAction(String action) { return this; }
    public Intent setData(android.net.Uri uri) { return this; }
    public Intent setType(String type) { return this; }
    public Intent putExtra(String key, String value) { return this; }
    public String getAction() { return null; }
    public android.net.Uri getData() { return null; }
}
