# EditablePlayerIcon Pipeline

## Current Understanding

### Save Flow (EditablePlayerIcon.Save)
```
User selects image
  → Image processed (resize, normalize)
  → EditablePlayerIcon.Save(byte[] datas, Texture2D texture)
    → path = CalculateImageSavePath(Player, id, ClubPlayerIcon)
    → SaveImage(path, datas)          // writes PNG bytes to file
    → SaveToCache(texture)            // caches Texture2D in memory
    → MarkDirty()                     // triggers save
```

### Load Flow (MakeImage / LoadFromCache)
```
UI requests player icon
  → EditablePlayerIcon.LoadFromCache()
    → if cached: return cached Texture2D
    → else: load from file at CalculateImageSavePath(...)
    → cache and return
```

### Data Storage
- **Image bytes**: written as PNG file to `CalculateImageSavePath()` result
- **Texture cache**: in-memory Dictionary (WeakReference<Texture2D>)
- **NOT in SQLite**: icon data is file-based, not in player_blob/archive_blob
- **player.dat / player2.dat**: obfuscated config (ExternalDataSetting), may contain path templates

### Key Finding
The icon is stored as a **plain PNG file** on the filesystem, NOT in the SQLite database.
This means we can write the icon directly without IL2CPP injection.

### Unknown
- Exact path pattern (being tested with 7 candidates)
- Image format requirements (PNG assumed, size TBD)
- Whether the game validates image dimensions/content
