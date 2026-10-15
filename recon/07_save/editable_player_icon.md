# EditablePlayerIcon API Analysis

## Class: EditablePlayerIcon : EditableData

### Fields
- `ArchivesDetailType DetailType` — ClubPlayerIcon(5) or NationalPlayerIcon(6)
- `static Dictionary<...> Cache` — texture cache
- `ClubPlayer clubPlayer` — associated player

### Methods (from IL2CPP dump)

| Method | Signature | RVA | Notes |
|--------|-----------|-----|-------|
| .ctor | `EditablePlayerIcon(int id)` | 0x11FE334 | Takes player ID |
| Save | `void Save(byte[] datas, Texture2D myTexture)` | 0x11FE79C | **Key API** |
| IsCustom | `bool IsCustom()` | 0x11FE98C | Check if custom icon |
| MakeImage | `bool MakeImage(Action<Texture, Rect> action)` | 0x11FEA10 | Generate image from texture |
| LoadFromCache | `Texture2D LoadFromCache()` | 0x11FEE54 | Load from texture cache |
| SaveToCache | `void SaveToCache(Texture2D myTexture)` | 0x11FE558 | Save to texture cache |
| ClearCache | `static void ClearCache()` | 0x11FF070 | Clear all cached textures |
| Reset | `override void Reset()` | 0x11FF070 | Reset to default |

### Storage Flow

```
EditablePlayerIcon.Save(byte[] datas, Texture2D myTexture)
  → ExternalDataAgent.CalculateImageSavePath(ArchivesType.Player, id, detailType)
  → SaveImage(path, datas)  [Utility class]
  → SaveToCache(myTexture)
```

### Path Pattern (inferred)

String literals found in binary:
- `./Texture/face/` — relative to persistentDataPath
- `/../ProfilePic/` — one level up from persistentDataPath

Candidate paths being tested:
1. `/data/user/0/<pkg>/ProfilePic/50000001.png` (CalculateKey: Player+1)
2. `/data/user/0/<pkg>/ProfilePic/1.png` (player_id only)
3. `/data/user/0/<pkg>/ProfilePic/50000001_5.png` (with detailType)
4. `/data/user/0/<pkg>/files/Texture/face/50000001.png`
5. `/data/user/0/<pkg>/files/Texture/face/1.png`
6. `/data/user/0/<pkg>/files/ProfilePic/50000001.png`
7. `/data/user/0/<pkg>/files/ProfilePic/1.png`

### Related Classes

- `EditableTexture2d : EditableData` — generic texture editing
- `ExternalDataAgent` — file I/O for save data
- `ExternalDataArchives` — static archive manager
- `ExternalDataSetting` — protobuf config with path templates
