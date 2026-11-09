# MiMo 桌宠完整制作流程（最终版 v3）

> 目标：让 MiMo 角色**住在小米 MiMo 桌面应用窗口里面**，随 Agent 工作状态自动变脸，
> 点击弹气泡显示小米额度 / 用量，并自动贴边。
> 本文所有路径、字段、命令、事件名均在本机实测；未证实的结论一律标注「未验证」。

---

## 0. 最终结论（先看这个）

| | 路线 A：MiMo 原生 Mate | 路线 B：**住在 MiMo 窗口里的桌宠** |
|---|---|---|
| 形态 | `userData/pets/<id>/{manifest.json, spritesheet.webp}` | 独立 PySide6 进程，窗口 **owner = MiMo 主窗口** |
| 素材契约 | 官方 `mate` skill 规范 | 复用同一套素材（完全兼容） |
| 本机可用性 | ❌ 本版 App 没有桌宠运行时 | ✅ **已跑通并逐项实测** |
| 是否真在窗口内 | 未知 | ✅ 移动/缩放/最小化全部实测通过（§5.4） |
| 状态联动 | 未知 | MiMo `/v1` SSE 事件流，4 套表情全部实测通过 |
| 额度 / 用量 | 未知 | ✅ 小米平台 API 换票链打通，真实数据（§7） |

### 为什么路线 A 在本机走不通

本机装的是 **MiMo Desktop 26.1102.21158（edition: domestic）**。按 5 个独立层次扫过，结论一致：**这个版本不含任何桌宠运行时**。

| 层 | 检查对象 | 结果 |
|---|---|---|
| 1. Electron 主进程 | `app.asar` → `launch.cjs`；`main~DAq2tHkd.mjs` | 只有主窗口 + 2 个 16×16 隐藏媒体宿主；**无透明置顶窗口**；`pets`/`sprite`/`frameWidth` 字符串 **0 命中** |
| 2. 运行时主 bundle | `node~5knT2Qec.mjs`（37MB） | `spritesheet` / `frameWidth` / `pets` **只出现在内置 `mate` skill 的说明文本里**，技能区外 0 命中 |
| 3. preload 桥接 | `preload/index~r-PVyE9U.js` | **375 个 `mimo:` IPC 通道，0 个与桌宠相关**（`pluginCompanion*` 是插件伴随应用，不是桌宠） |
| 4. 渲染层 | `renderer/assets/**`（**352 个 chunk，全部本地、0 个远程加载、0 个缺失**） | 无「桌面伙伴」/「desktop pet」/`spritesheet`/`MatePage` 任何字符串；设置页导航 20 个分区**没有 Mate**；Personalization 页只有「自定义指令」；Lab 页只有 3 个开关（`evolveAgent`/`sessionChat`/`gitVersionPin`） |
| 5. 功能开关 | `feature-gates.json` | domestic / overseas 两套 payload 均无桌宠相关 gate |

旁证：官方预设 `leijun-are-you-ok` 的文件时间戳是 **2026-09-13**，而当前 exe 装于 **2026-11-02** —— 它是旧版本留下的化石。

> **但路线 A 的资源已经按官方契约装进去了**（字节级校验通过，见 §3），
> 官方哪天把 Mate 上线，点一次 Refresh 就能直接用 —— **不用重做任何东西**。

---

## 1. 路线 A：MiMo 原生 Mate 契约

### 1.1 目录结构

```
<MiMo userData>/pets/<pet-id>/
├── manifest.json      # 动画元数据（必需）
└── spritesheet.webp   # 精灵图（必需，必须带 alpha）
```

本机 userData = `C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\`

### 1.2 权威规范来源

MiMo Desktop 自带 **`mate`（Mate Pet Creator）** 内置 skill，引擎 bundle 里能挖到全文：

`C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\node~5knT2Qec.mjs`

> ⚠️ 该 .mjs 是 UTF-8，但**内置 skill 文本块是 UTF-16LE**，直接读会乱码。
> 用 `tools/extract_mate_skill.py` 抽出到 `_mimo/mate_skill_full.md`（6094 字符）。

### 1.3 manifest 字段表

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `id` | string | ✅ | 唯一标识，kebab-case。**不能撞预设**（预设 `koala`/`panda` 优先级更高） |
| `name` | string | ✅ | 设置页显示名 |
| `version` | number | ✅ | 官方约定**恒为 1** |
| `spritesheet` | string | ✅ | 精灵图文件名（相对本目录） |
| `frameWidth` / `frameHeight` | number | ✅ | 单帧尺寸 |
| `columns` | number | ✅ | 网格列数 |
| `totalFrames` | number | ✅ | 全部动画总帧数 |
| `animations` | object | ✅ | 动画名 → `{row, frames, fps, loop}`，**至少要有 `idle`** |
| `description` | string | ➖ | 设置页描述 |
| `anchorX` | number | ➖ | 水平锚点 0–1，默认 0.5 |

### 1.4 精灵图排布规则

- 帧按 **从左到右、从上到下**（row-major）排布
- 每个动画对应一行；**帧数不够一行会续到下一行**
- 所有帧尺寸必须完全一致
- **必须有 alpha 通道**（桌宠窗口无背景）
- 格式 **WebP 带透明**
- 整个文件 **< 2MB**

> ### ⚠️ 关键结论：帧是 row-major **跨行连续**的
> 官方预设 `leijun-are-you-ok` 是 `columns: 4` 但 `idle.frames: 8`，精灵图 960×480 = 4列×2行。
> 第 2 行是第 1 行的接续帧，不是另一条动画。
> 本方案让每个动画刚好占满一行（`frames == columns`），在两种解读下都成立，最稳。

### 1.5 硬性约束（官方 skill 明写）

- `idle` 必须存在，系统找不到别的动画时回落到它
- 帧尺寸一致、总文件 < 2MB
- id 唯一，与预设冲突时**预设赢**
- **禁止引用任何外部 URL**，资源必须全本地

---

## 2. 素材制作流程（路线 A / B 共用）

### Step 1 —— 角色设定

- ✅ 降维成 SD 头肩 Q 版像（当前成品是 2048² 白底立绘，**头肩构图**，缩到 220px 细节刚好）
- ✅ 三色配色（橙 / 白 / 黑）+ 粗深棕描边 + 平涂 + 单块渐变高光
- ❌ 砍掉蕾丝、缎带、腿环、金色徽章等小细节 —— 缩到 160px 就糊成噪点

### Step 2 —— 出图与抠像（4 套表情）

```powershell
# 2.1 上传参考图拿临时 URL
mcode-tools upload_temp_url 'D:\桌面宠物\assets\src\mimo-design-reference.jpg'

# 2.2 生成（args 文件必须无 BOM）
$payload = @{ requests = @( @{ prompt=$prompt; input_urls=@($url1,$url2); aspect_ratio='1:1'; resolution='2K'; output_file='mimo-idle-v2' } ) }
[System.IO.File]::WriteAllText('D:\桌面宠物\_gen_args.json', ($payload | ConvertTo-Json -Depth 10 -Compress), (New-Object System.Text.UTF8Encoding($false)))
mcode-tools connector call connector__matrix__generate_image --args-file 'D:\桌面宠物\_gen_args.json'

# 2.3 抠像（image_url 必须是 upload_temp_url 的 temp_url）
$body = @{ image_url = $tmp } | ConvertTo-Json -Compress
[System.IO.File]::WriteAllText('D:\桌面宠物\_bg.json', $body, (New-Object System.Text.UTF8Encoding($false)))
mcode-tools connector call connector__matrix__remove_image_background --args-file 'D:\桌面宠物\_bg.json'

# 2.4 下载
curl.exe -sL -o 'D:\桌面宠物\assets\src\mimo-idle-v2@2048.png' <download_url>
```

**生成提示词的纪律（v1 翻车换来的）**：

1. 「简化」指令必须**限定作用域** —— 只能写 "simplify the clothing"。写 "simplify the costume" 模型会把帽子零件一起砍掉（v1 就是这么丢了帽带徽章和兔耳）
2. 细节还原要**额外喂局部特写图**当第二参考图（`assets/src/_zoom-hat-front.png`，crop 250,0,470,330 → 940×660）
3. 统一白底/绿幕出图，**自己抠像**，不要让 AI 直接出透明 PNG

### Step 3 —— 编排精灵图（程序化变形动画）

```powershell
python 'D:\桌面宠物\tools\build_anim_sheet.py' --out 'D:\桌面宠物\build\mimo-witch' --gif
```

详见 §6。

### Step 4 —— 写 manifest.json

由 Step 3 自动生成：

```json
{
  "id": "mimo-witch",
  "name": "MiMo 巫女兔",
  "description": "橙白双马尾女巫帽兔耳少女 · MiMo 桌面伙伴",
  "version": 1,
  "spritesheet": "spritesheet.webp",
  "frameWidth": 256, "frameHeight": 256,
  "columns": 24, "totalFrames": 96,
  "anchorX": 0.5,
  "animations": {
    "idle":  { "row": 0, "frames": 24, "fps": 8,  "loop": true },
    "happy": { "row": 1, "frames": 24, "fps": 12, "loop": true },
    "think": { "row": 2, "frames": 24, "fps": 6,  "loop": true },
    "tired": { "row": 3, "frames": 24, "fps": 5,  "loop": true }
  }
}
```

### Step 5 —— 派生「Mate 精简版」并安装（路线 A）

主精灵图（256px × 24 帧）无损 webp 有 **6.3MB**，超了 Mate 的 2MB 上限。
用 `tools/build_mate_sheet.py` 派生一份：每行等间隔抽 12 帧 + 降到 192px + 有损 webp → **793KB**。

```powershell
python 'D:\桌面宠物\tools\build_mate_sheet.py'
python 'D:\桌面宠物\tools\install_mate_pet.py' --src 'D:\桌面宠物\build\mimo-witch-mate'
```

安装器会：定位 pets 目录 → **安装前**校验（字段完整性 / WebP RIFF 头 / 尺寸对不对得上 / alpha 有没有 / < 2MB）→ 只拷贝 `manifest.json` + `spritesheet.webp` → **安装后**再校验一次。

### Step 6 —— 在 App 里启用（路线 A，当前版本不可用）

1. 设置 → **Mate** → **Refresh** → 选中你的宠物
2. 设置 → **Personalization** → 打开 **"Avatar or desktop companion"**

> 本机版本没有第 1 步的 Mate 页签（见 §0）。资源已就位，官方上线后直接可用。

---

## 3. 路线 A 的安装结果（已落盘，已校验）

```
C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\pets\
├── leijun-are-you-ok\        ← 官方预设（2026-09-13 的化石）
│   ├── manifest.json
│   └── spritesheet.webp      323,364 B
└── mimo-witch\               ← 本次安装（Mate 精简版 793KB）
    ├── manifest.json
    └── spritesheet.webp      793,300 B
```

`tools/verify_installed.py` 的独立复核（不复用构建目录任何中间产物）全部通过：
目录存在且只含契约必需的 2 个文件 / manifest 无 BOM / 9 个必需字段齐全 /
WebP 头合法 / alpha 范围 `0..255` / 尺寸与 manifest 一致 / 每帧都有像素 /
与构建产物 sha256 完全一致。

---

## 4. 路线 B：把桌宠塞进 MiMo 窗口里（核心难点）

### 4.1 三种承载方案与实测结果

| 方案 | 做法 | 结果 |
|---|---|---|
| A. `SetParent` | 把桌宠窗口变成 MiMo 主窗口的**子窗口** | ❌ **实测失败**。MiMo 主窗口只有一个子窗口 `Intermediate D3D Window`（DirectComposition 渲染层，rect=(580,98,1856,983)），SetParent 进去的子窗口被**完全盖住**。用洋红像素检测验证：命中数 0 |
| B. **owner 窗口** ✅ | `SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, miMo_hwnd)`，把桌宠变成 MiMo 的 **owned window** | ✅ **可行**。owned window 永远浮在 owner 之上；owner 最小化/隐藏时一起隐藏；owner 被别的窗口压住时桌宠跟着被压住 |
| C. 独立置顶浮窗 | 纯顶层窗口，每帧跟随 MiMo 矩形 | ✅ 能用，但**不是"在窗口里"**，用户明确不接受 |

> **不要再尝试 SetParent**。Chromium/Electron 的 DirectComposition 渲染层永远盖在普通子窗口之上。

### 4.2 位置语义：MiMo 客户区坐标

桌宠的位置**不是屏幕坐标**，而是 **MiMo 客户区坐标**：

```
屏幕位置 = ClientToScreen(MiMo主窗口, 客户区坐标)
```

每 33ms 重算一次（`_sync_position()`），并强制夹在客户区内：

```python
self.cx = max(0, min(self.cx, cw - self.pet_size))
self.cy = max(0, min(self.cy, ch - self.pet_size))
```

好处：MiMo 窗口移动/缩放时桌宠自动跟随，且**几何上不可能跑出 MiMo 窗口**。

### 4.3 ⚠️ 坑：Qt 的 `show()` 会清掉 owner 指针

这是本轮最隐蔽的坑。实测（`tools/probe_owner.py`）：

```
1 winId (未 show)      : 0xe0092e
2 set owner 后          : 0x4a0926      ← 设置成功
3 show 后               : owner 0x0     ← ★ show() 把它清掉了
4 raise_ 后             : owner 0x0
6 再 show 后            : owner 0x0
```

Qt 在 `show()` 过程中会重置顶层窗口的 parent/owner。

**正确的做法**：把绑定写成**「读实际指针 → 缺了就补」的幂等形式**，并且在 `show()` **之后**执行：

```python
def _apply_owner(self):
    if self.window.isVisible():
        hwnd = int(self.window.winId())
        cur = H.user32.GetWindowLongPtrW(hwnd, H.GWLP_HWNDPARENT) or 0
        if cur != self.host_hwnd:
            H.user32.SetWindowLongPtrW(hwnd, H.GWLP_HWNDPARENT, self.host_hwnd)
```

并且 `_tick()` 里的顺序必须是 **先 `_sync_position()`（可能触发 show）→ 再 `_apply_owner()`**。
气泡同理：`pop_in()` 之后立刻补一次 owner。

### 4.4 气泡也要绑定 owner

气泡是独立顶层窗口（`Qt.Tool` + `WindowDoesNotAcceptFocus`），同样 `GWLP_HWNDPARENT = MiMo hwnd`，
这样它会跟 MiMo 一起被遮挡 / 最小化，z-order 也不会跑到 MiMo 后面。

### 4.5 MiMo 收进托盘时的处理

MiMo 收进托盘时主窗口 `IsWindowVisible=False`。此时桌宠找不到可见宿主会自己隐藏。
要把 MiMo 唤回来：

```powershell
python 'D:\桌面宠物\pet\show_mimo.py'    # ShowWindow(SW_SHOW)
```

桌宠每 33ms 调一次 `attach_host()`，MiMo 一回来就自动重挂。

---

## 5. 路线 B 整体架构

```
┌────────────────────────────────────────────────────────────┐
│  MiMo Desktop 主窗口  (Chrome_WidgetWin_1 / "Xiaomi MiMo") │
│    └─ Intermediate D3D Window  ← DirectComposition 渲染层 │
│                          ▲                                  │
│                          │ SetWindowLongPtrW(GWLP_HWNDPARENT)
│            ┌─────────────┴──────────────┐                 │
│            │  MiMo 桌宠 (owned window)  │  气泡 (owned)    │
│            │  位置 = MiMo 客户区坐标     │                 │
│            └────────────────────────────┘                 │
└────────────────────────────────────────────────────────────┘
        ▲ SSE /v1/sessions/<id>/events        │
        │ busy / text-partial / idle /        │
        │ ui(kind=error|usage)                 ▼
   ┌──────────────┐                    ┌─────────────────┐
   │ mimo_link.py │                    │  mimo_quota.py  │
   │ 事件→表情状态机│                    │ 小米额度换票链   │
   └──────────────┘                    └─────────────────┘
```

| 文件 | 作用 |
|---|---|
| `pet/mimo_host.py` | Win32 宿主层：枚举/定位 MiMo 窗口、owner 绑定、客户区↔屏幕坐标换算、DPI |
| `pet/mimo_bubble.py` | 气泡控件（QPainter 手绘，橙白黑三色，QPropertyAnimation + OutBack 过冲） |
| `pet/mimo_quota.py` | 小米额度客户端（Chromium cookie 解密 + SSO 换票链 + 缓存） |
| `pet/mimo_link.py` | MiMo 本地 API 客户端 + 事件→表情状态机（纯标准库，可单测） |
| `pet/mimo_pet.py` | 桌宠主程序（窗口 + 动画 + 气泡 + 贴边 + 托盘 + 菜单） |
| `tools/pet_control.py` | 控制 CLI |
| `tools/shot_mimo.py` | 截图取证（打印 owner 指针 / rect / 是否在窗口内） |
| `tools/test_follow.py` | 跟随性实测（移动 / 缩放 / 最小化 / 恢复） |
| `tools/diff_anim.py` | 动画活跃度量化（帧间差分） |

### 5.1 MiMo 本地 API 契约

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/v1/health` | `{"ok":true,"api":1,"app":"...","engine":"ready"}` |
| GET | `/v1/sessions?limit=N` | 会话列表，含 `time.updated` |
| GET | `/v1/sessions/<sid>/messages` | 消息历史 |
| GET | `/v1/sessions/<sid>/events` | **SSE 事件流** |
| POST | `/v1/sessions/<sid>/turns` | 发起一轮对话 |

**坑**：路由前缀是 `/v1`（不带前缀一律 404）；必须带 `Authorization: Bearer <token>`；
`Host` 头必须是 `127.0.0.1:<port>` 或 `localhost:<port>`，否则 403 `forbidden-host`；
token 会随 MiMo 重启变化，每次连接重新读 `desktop-api.json`。

### 5.2 事件 → 表情映射（实测）

| 事件 | 表情 | 说明 |
|---|---|---|
| `busy` | **think** | 一轮任务开始 |
| `text-partial` | **think** | 流式输出中 |
| `ui` / `ui.kind == "usage"` | **happy** | 本轮 token 结算 = 任务完成 |
| `idle`（紧跟 busy 之后） | **happy** | 任务干完了；持续 2.6 秒后自动回落 idle |
| `ui` / `ui.kind == "error"` | **tired** | 报错 |
| `permission*` | **tired** | 等用户授权 |
| 连续 busy > 150 秒 | **tired** | 疑似卡住 |

### 5.3 交互

| 操作 | 效果 |
|---|---|
| **左键单击** | **弹额度气泡**（状态 + 小米额度 + 用量）；若当前是贴纸气泡则**切回额度气泡**去看用量 |
| **左键双击** | **弹表情包贴纸气泡**（彩蛋，见 §8.5） |
| **左键三击** | **只换表情**（临时切一个，4 秒后自动回到「跟随 MiMo」，**不出贴纸**） |
| 左键拖拽 | 移动位置（客户区坐标落盘），松手自动贴边 |
| 右键 | 菜单：表情（含「轮换表情」）/ 位置 / 贴边开关 / 溜达开关 / 跟随开关 / 查看额度气泡 / **彩蛋表情包** / 显示隐藏 / 重新加载素材 / 开机自启 / 关于 / 退出 |
| 托盘图标 | 左键弹气泡，右键同菜单 |

### 5.4 跟随性实测结果（`tools/test_follow.py`）

```
初始 MiMo rect=(572, 98, 1864, 991)  桌宠相对客户区=(1040, 649)
移动到 rect=(312, 188, 1604, 1081)  桌宠相对客户区=(1040, 649)
  -> 窗口移动了: 是 ; 桌宠相对位置不变: 是 ✓
缩放后 MiMo rect=(312, 188, 1284, 961) client=956x765  桌宠 rect=(1056, 733, 1276, 953)
  -> 桌宠仍在客户区内: 是 ✓
MiMo 最小化后: host visible=1  桌宠 visible=0
  -> 桌宠跟着隐藏: 是 ✓
MiMo 恢复后: 桌宠 visible=1  owner=0x4a0926 (MiMo=0x4a0926)
  -> 桌宠自动回来且仍绑定: 是 ✓

全部通过 ✓
```

---

## 6. 动画：程序化分层变形（不烧 AI 出图额度）

### 6.1 思路

4 张静态立绘 → 96 帧，靠**位移场（displacement field）**做分层形变，不用 AI 逐帧重绘，
保证 4 套表情造型完全一致。

| 层 | 做法 |
|---|---|
| 身体呼吸 | 下半身绕脖颈纵向微缩放 + 横向微扩（squash & stretch） |
| 发丝剪切 | 两侧长发水平剪切，**振幅随高度递增、相位随高度滞后** → 发梢晚于身体到位 |
| 头部轻摆 | 整颗头绕脖颈点做 ±1.7°~2.6° 摆动 |
| 耳 / 帽尖 | 兔耳、帽冠尖端、呆毛**各自独立摆动**（羽化椭圆遮罩） |
| 眨眼 | 眼部压成闭合缝 + 脸颊肤色补齐 + **深棕弧线**（保证任何画风都看得出闭眼） |
| 情绪附加 | happy 弹跳 + 落地挤压；tired 下沉 + 叹气；think 歪头 |

### 6.2 幅度按「显示尺寸」标定（关键）

第一版幅度是拍脑袋定的，结果**帧间几乎看不出差别**，用户评价"僵硬"。

修正做法：**所有幅度都以桌宠实际显示尺寸 220px 反推**：

```
显示缩放比 ≈ 240 / 1974 ≈ 0.1216   （精灵帧 256，内容宽 240）
目标显示像素 -> 全分辨率像素 = 目标 / 0.1216
```

| 部位 | 目标显示位移 | 全分辨率 |
|---|---|---|
| 发丝摆动 | 5px | 44px |
| 兔耳摆动 | 3px | 26px |
| 帽冠尖端 | 2.5px | 20px |
| 整体浮动 | 2.4px | 20px |
| happy 跳跃 | 15.8px | 130px |

### 6.3 遮罩：羽化椭圆（不能用连通域）

兔耳和帽体在 **alpha 上是连通的**（`connectedComponentsWithStats` 只返回 1 个连通域，2.2M 像素），
所以没法自动分离部件。

改用**羽化椭圆遮罩 + 位移衰减**：

```python
def _ellipse_w(X, Y, ell):
    cx, cy, rx, ry = ell
    d = ((X-cx)/rx)**2 + ((Y-cy)/ry)**2
    return np.clip(1.0 - d, 0.0, 1.0)     # 中心 1，边缘 0
```

边缘位移自然归零 → **不会撕开接缝**。

部件坐标（union 坐标系，用 `tools/grid_parts.py` 打网格人工核对）：

| 部件 | 椭圆 (cx, cy, rx, ry) |
|---|---|
| 左兔耳 | (635, 240, 175, 225) |
| 右兔耳 | (1340, 460, 125, 200) |
| 帽冠尖端 | (1805, 610, 140, 180) |
| 呆毛 | (1310, 235, 90, 80) |

### 6.4 活跃度量化（`tools/diff_anim.py`）

不靠感觉，用帧间差分客观衡量：

```
表情      平均帧差   最大帧差   活跃像素%   垂直位移px
idle        10.82     236.50      24.4         3.65
happy       15.21     255.00      28.8        18.83
think       13.48     255.00      25.8         1.55
tired        9.18     234.50      23.1         3.83
```

### 6.5 重采样

用 OpenCV `cv2.remap`（比 `scipy.ndimage.map_coordinates` 快一个量级），形变分辨率 55%。
采样前做 **alpha 预乘**，避免透明区颜色渗出。

> ⚠️ `np.tile(A, reps)` 是按维度逐块平铺，不是"复制行"；要复制行用 `np.broadcast_to` / `np.repeat`。

### 6.6 眨眼算法（重写版 v5）

用户原话：**「眼皮动、睫毛不动，一点都不灵动」**。
根因不是渲染，是模型：旧版只改"眼皮"那块肤色，睫毛带原地不动，于是上下两层各动各的。

重写后的模型：

1. **睑缘 = 睫毛带下沿**（不是虹膜上沿）。眨眼时睫毛带**整段平移** `d` 行，
   下沿锚在新睑缘上 —— 弧线、粗细、纹理全部来自原画，不会走形。
2. **填充区 = [旧睫毛顶, 新睫毛顶)**，用睫毛正上方那条「眼皮条」**纵向拉长**填。
   不能用一块平涂肤色：256px 精灵帧里平涂色会读成一条白板。
3. **下压量** `d = level × (眼球下沿 − 睑缘) × 羽化权重`；左右端用 16 列 smoothstep 收到 0。

判定「睫毛」的关键色度事实（2048px 原画实测）：

| 部件 | RGB | V | 饱和度判别 `(R−B) > 0.55R` |
|---|---|---|---|
| 睫毛 | `(62,19,14)` | ~63 | ✓ 命中 |
| 虹膜暗轮廓 | `(94,34,18)` | ~95 | ✓ **也会命中** |
| 眉毛 | `(121,75,78)` | ~121 | ✗ 排除（靠饱和度） |
| 发丝描边 | `(138,85,84)` | ~138 | ✗ 排除 |

⇒ 睫毛只能靠**饱和度**跟眉毛/发丝分开；**分不开虹膜暗轮廓**（它跟睫毛会粘成一坨，
实测厚度从真实的 12px 虚增到 52px）。

踩过的坑（每个都对应一次返工）：

- ⚠️ **只信睫毛的上沿**。下沿会被虹膜暗轮廓污染，所以下沿由「上沿 + 厚度」推出来，
  厚度单独插值并 clip 到 `[6,40]`；上下沿各自插值会把厚度拉飞。
- ⚠️ **眼白必须做「连通域面积 ≥150」+「贴着虹膜」双重过滤**。
  眉毛上方那块纯白反光面积够大，算进「眼球」会把上沿顶到眉毛上去，
  于是「睫毛在眼球上方」永远不成立 —— 工作区被截掉一半，眼睛只眨一半。
- ⚠️ **gap 阈值放宽到 56px**，并且**跨 ≤14 列的缺口用插值补**。
  虹膜暗轮廓不算进虹膜圆盘，上沿会偏低十几像素，卡太紧工作区就断了。
- ⚠️ **填充取样基准是睫毛上沿那一行 `lt−1`**，不是下沿 `lb−1`。
  用下沿会取到睫毛本体，填充区直接变成一条深棕竖条。
- ⚠️ **填充色只压到 ×0.98**。压到 ×0.90 会比脸皮暗一大截，读成一块灰砖；
  不压又太亮。最终靠「贴脸皮色 + 靠近睫毛的 14% 投影」来区分。
- ⚠️ **最大闭合度压到 0.66**，`BLINK_LEVEL = {0:0.42, 1:0.62, 2:0.22}`。
  闭死会让整只眼睛变成一片空白，256px 下像「脸少了一块」；眯着反而更像眨眼。
- ⚠️ **睫毛带加粗系数只能到 0.12**。试过 0.85，直接变成一根黑杠糊住眼睛。
- ⚠️ **验收必须按最终 256px 精灵帧看**。7 倍放大的眼部图会把正常的眼皮填充
  看成「白板」，3 倍全分辨率放大又会把形变场的影响误判成渲染 bug。

本轮为此写的诊断工具（都在 `tools/`）：

| 工具 | 作用 |
|---|---|
| `eye_geom.py` | 打印解出的眼睛几何（睑缘/下沿/睫顶/睫底/厚度） |
| `eye_cols.py` | **逐列**打印原始测量值和有效性判定（定位工作区为什么被截断） |
| `blink_plan.py` | 打印 make_blink 每一列的决策值（d / 新睑缘 / 填充区） |
| `blink_cols.py` | 打印 2048 空间里 make_blink 输出的逐列色块剖面 |
| `blink_diff.py` | 两个档位在 256px 帧上的像素差分 + 掩膜 |
| `frame_cols.py` | 256px 帧眼部的逐列色块剖面（并排多档位） |
| `blink_strip.py` | **按精灵图最终 256px 拼一条动画带 —— 这才是验收视图** |
| `blink_frame.py` | 存出单帧 256px（`--nowarp` 可分离「渲染」和「形变」） |
| `eye_crops.py` / `frame_eye_zoom.py` | 眼部放大图 |

---

## 7. 小米额度 / 用量（完整逆向链路）

### 7.1 接口

base = `https://platform.xiaomimimo.com`，路径**必须带 `/api/v1`**（少了就是 openresty 404）：

| 接口 | 给出什么 | 实测值 |
|---|---|---|
| `/api/v1/usage` | 累计 token、花费、TPM 上限 | `totalToken=122,288,227`、`totalCost=71.98`、`tpm=3,000,000` |
| `/api/v1/tokenPlan/usage` | 本月套餐已用比例 / 总额 / 限额 | `percent=0.90`（已用）、`used=9,900,429,509` / `limit=11,000,000,000` |
| `/api/v1/tokenPlan/detail` | 套餐名、周期结束 | `planCode=standard`、`currentPeriodEnd=2026-11-11 23:59:59` |
| `/api/v1/balance` | 账户余额 | `19.37 CNY` |
| `/api/v1/userProfile` | 账号 id / 手机号 | `userId=3113399232`、`+86 131****8325` |

其它 base 都不是额度接口：`https://api.xiaomimimo.com/v1`、`https://token-plan-cn.xiaomimimo.com/v1`、`https://mimo-server-cn.xiaomimimo.com`。

### 7.2 鉴权：小米 SSO 换票链

直接带 `Cookie: passToken=…; userId=…; cUserId=…` 会 **401**，正确链路：

```
1. GET https://platform.xiaomimimo.com/api/v1/usage   -> 401，响应体带 loginUrl
2. GET <loginUrl>
     account.xiaomi.com/pass/serviceLogin
       ?callback=https://platform.xiaomimimo.com/sts?sign=..&followup=..
       &sid=api-platform&_group=DEFAULT
3. 跟随重定向 -> /sts 下发 cookie：
     api-platform_serviceToken / api-platform_slh / api-platform_ph / userId
     （域 .platform.xiaomimimo.com）
4. 回到 followup -> 直接拿到 JSON 数据
```

> ⚠️ `http.cookiejar.Cookie` 手工构造时必须补齐
> `version=0, port, port_specified, domain_specified, domain_initial_dot, path_specified, rest, comment, comment_url`，
> 否则报 `'RawCookie' object has no attribute 'version'`。

### 7.3 凭据从哪来

- 账号 cookie 在 Chromium session partition **`persist:xiaomi-account`**
  → `%APPDATA%\Xiaomi MiMo\Partitions\xiaomi-account\Network\Cookies`
- 需要 `passToken` / `userId` / `cUserId`（`buildCookieHeader` 证实）
- cookie 值是 Chromium v10/v11 **AES-256-GCM**，密钥来自 `Local State.os_crypt.encrypted_key`
  （Windows 下这层是 DPAPI，`CryptUnprotectData` 可自行解开）

### 7.4 ⚠️ cookie 库被排他锁

MiMo 运行时 Chromium 对 `Network\Cookies`、`Partitions\xiaomi-account\Network\Cookies`、
`Partitions\rp-browser\Network\Cookies` **全部 WinError 32**。
`shutil.copyfile` 和 `CreateFileW(FILE_SHARE_READ|WRITE|DELETE)` 都失败。

**解决**：桌宠在「MiMo 没跑」时（开机自启、或 MiMo 退出/重启的瞬间）抓一次，
缓存到 `pet/quota_cred.json`（含换来的 `platform_cookies`）。之后用缓存也能正常换票出数。

实测：MiMo 运行状态下用缓存凭据**照样能拿到真实额度数据**（§7.1 那张表）。

---

## 8. 气泡对话框

`pet/mimo_bubble.py`，QPainter 手绘，严格橙 / 白 / 黑三色：

- 暖白底 + 橙边（2px）+ 圆角 13px + padding 14×11
- 尾巴：从主体边缘长出来的小三角，**根部被主体描边盖住**，视觉上无缝
- 阴影：6 层递减 alpha 模拟柔化
- 弹出：`QPropertyAnimation` + `QEasingCurve.OutBack`（过冲 → 可爱），220ms
- **默认 5 秒后自动淡出**（配置 `bubble_timeout`，设 0 = 永不自动收起）；
  再点一次桌宠也可以立刻收起

### 8.1 ⚠️ 坑：尾巴被主体完全盖住

第一版把尾巴画在主体**之前**，且尾巴中心点在 `body.bottom() - s/2`（**在主体内部**），
结果尾巴 100% 被主体挡住，截图里根本看不到。

修正三处：

1. **几何**：尾巴整体落在主体轮廓**之外**（底边贴着 `body.bottom()`，尖端伸出 `TAIL_LEN`）
2. **预留空间**：`setFixedSize` 时按尾巴方向加边距，否则会被 widget 边界裁掉
3. **描边顺序**：影子 → 尾巴填充 → 主体（盖住尾巴根部）→ 尾巴外沿描边

### 8.2 尾巴方向要跟着气泡位置翻

气泡默认放桌宠正上方（尾巴朝**下**指桌宠）；空间不够翻到下方时，尾巴要朝**上**。
`place_bubble()` 现在返回 `(x, y, tail_side, tail_x)`，`tail_x` 让尾巴对准桌宠中心。

### 8.3 自定义属性要声明

```python
alpha = Property(float, alpha, setAlpha)      # 不声明 QPropertyAnimation 会报
                                          # "non-existing property alpha"
```

### 8.4 气泡显示的内容

| 行 | 来源 |
|---|---|
| 状态行 `✦ 待机中` / `★ 任务完成啦！` / `… 正在思考…` / `✖ 出错了` | `PetBrain` 状态 |
| 额度剩余 %（带进度条，<20% 变红） | 平台 API |
| 本月已用 % | 平台 API |
| 账户余额 ¥ | 平台 API |
| 套餐 | 平台 API |
| 额度重置（11-11） | 平台 API |
| 本轮消耗 xxx tok | SSE `ui(kind=usage)` 事件里的 token 数 |
| MiMo 连接 | 本地 API 连通性 |

底层报错会翻译成人话（"需要小米账号会话" / "账号会话已过期" / "cookie 被占用" / "网络不通"）。

### 8.5 彩蛋：双击出表情包

用户需求演进：
1. 最初：「多点几十气泡的话，它会出现一些其他的气泡，比如做一些其他表情包之类的」
2. 后续：「单击还是会出现那个额度正常的额度卡片，只不过是多点的时候就是双击或者是三击
   就会出现这个表情包。」
3. **2026-11-09 修订（本节当前规则）**：
   「默认的话，是根据那个应用的状态，自己切换表情，然后三连击的彩蛋给去掉，
   三连击的话是直接换表情，两连击是那个弹出那个对话框，
   有表情包单击是查看」

即最终规则：

| 手势 | 语义 |
|---|---|
| 单击 | 额度气泡；**贴纸亮着时单击 = 切回额度气泡**（"查看"用量） |
| 双击 | 表情包贴纸（彩蛋） |
| 三击 | **只换表情**，不出贴纸；临时切一下，4 秒后自动回到「跟随 MiMo」 |
| 默认 | 跟随 MiMo 状态自动切换表情（busy→think / usage→happy / error→tired） |

实现拆成三块：

**① 贴纸素材**（`tools/build_stickers.py`）

参考图本身就是「白底 + 角色 + 橙色描边大字」的表情包版式，**不做抠图**，
直接缩放成统一尺寸的卡片，交给气泡做圆角裁切。

- 源图：`assets/stickers/src/*.jpg`（1080×1080）
- 输出：`assets/stickers/sticker-NN.png`（360×360）+ `index.json`
- `index.json` 每项带 `label`（台词）/ `mood`（联动表情）/ `dark`（是否深色底）
- `dark` 由四角亮度自动判定（<170 算深色），深色贴纸配深色气泡，
  免得白气泡套深色图显得割裂

**② 点击计数与解锁**（`pet/mimo_egg.py`）

| 环节 | 规则 |
|---|---|
| 计数 | `tap()` 只计数、不返贴纸。**按物理点击计**（不是按手势计）：单击 +1、双击 +2、三击 +3 |
| 阈值 | 30 次解锁（`EggTracker.UNLOCK_AT`） |
| 提示 | 距解锁 ≤5 次时，额度气泡底部显示「再点 N 下试试？」 |
| 贴纸轮换 | 优先抽没弹过的；9 张全收过一轮后从头循环 |
| 持久化 | `pet/egg_state.json`，重启不清零（取贴纸后立刻落盘） |
| **计数与手势解耦** | 计数在 `_register_click()`（事件层，每次物理点击 +1），手势语义在 `_resolve_gesture()`（结算层）。**必须解耦** —— 否则连点解锁时会被判成多击，计数只按手势结算一次，解锁遥遥无期 |

**③ 贴纸气泡**（`pet/mimo_bubble.py` 的 `set_sticker()`）

气泡新增「贴纸模式」：图片等比缩到 200px 居中，圆角裁切 + 细描边，
下方接状态行和收起提示。外壳、尾巴、动画跟普通气泡完全一致，
所以 owner 绑定 / 5 秒自动收起 / 再点收起都不用改。

贴纸自带超大标题（「罢工」「困了」「划水摸鱼」），所以气泡里**不再重复标题**，
只放状态行 —— 避免同一个词出现两次。

尺寸：贴纸气泡**固定 228×270**；额度气泡**宽度随内容变**（最小 214，实机实测 301）、**高度随额度行数变**（当前无订阅 → 172；最多 8 行 → 274）。

#### 交互表（2026-11-09 现行）

| 手势 | 未解锁 | 已解锁 |
|---|---|---|
| 单击 | 弹/收额度气泡 | 弹/收额度气泡；**贴纸气泡开着时单击 = 切回额度气泡**（查看用量），不换贴纸 |
| 双击 | toast「还差 N 次」 | 弹一张表情包贴纸 + 桌宠切到对应表情；**贴纸已经开着时双击 = 换下一张** |
| 三击 | 切表情（临时） | **只切表情，不出贴纸**；4 秒后自动回到「跟随 MiMo」 |

> **双击的贴纸是延迟弹出的**（`TRIPLE_WAIT_MS` = 260ms）。
> 因为三击 = 只换表情：如果双击就立刻弹贴纸，三击时贴纸已经亮着，
> 用户会看到「三击也出贴纸」。所以双击先排队，等三击窗口过去、
> 确定没有第三次点击再弹。
> 排队期间 `_bubble_mode` 立刻占位成 `sticker`，
> 否则额度刷新会把气泡重绘成额度卡片，贴纸永远弹不出来。

> 实机验证：`python tools/test_gesture_live.py`（真实鼠标，12 项断言全过）
> + `python tools/test_gesture.py`（纯逻辑，穷举各种事件序列）。

#### ⚠️ 坑 1（2026-11-09 重写）：dblclick 事件不可靠，判定只能数 release

**旧结论（已作废）**：多击判定必须用 Qt 原生 `mouseDoubleClickEvent`。

**新结论**：这个环境下 `WM_LBUTTONDBLCLK` **根本不发生**。

实测过程（三个探针）：

1. `tools/probe_style.py` —— 查窗口 class style，发现 Qt 的 class
   （`Qt683QWindowToolSaveBits`）已经带 `CS_DBLCLKS`（0x08），
   所以**不是** class style 缺标志的问题
2. `tools/probe_dbl4.py` —— 最小复现窗口（普通顶层 / 桌宠同款），
   用 `mouse_event` 注入双击，**press/release/dblclick 一个都收不到**
3. `tools/probe_dbl5.py` —— 真实鼠标双击桌宠，计数确实 +2，
   但 `mouseDoubleClickEvent` 从不触发

结论：Windows 的 DBLCLK 由**鼠标输入队列**合成，注入事件和某些
环境下根本不产生。老版本「双击出贴纸」其实**从来没真正生效过**
（测试用 PostMessage 注入，绕过了 Windows 的合成，一直是假象）。

**新判定模型：只数 release**

```
单击：press -> release                        -> 1 次 release -> 单击
双击：press -> release -> dblclick -> release  -> 2 次 release -> 双击
三击：… -> press -> release                   -> 3 次 release -> 三击
```

这个模型在「dblclick 到达」和「dblclick 不到达」两种环境下结果一致：

- dblclick **到达**时：Qt 仍会派发第 2 次点击的 release，
  所以 dblclick 里要**计 1 次**，同时抑制紧随其后的那个 release
  （否则双击会被数成 3 次 -> 误判三击）
- dblclick **不到达**时：正常 release 各计 1 次，结果不变

关键实现（`pet/mimo_pet.py` 的 `PetWindow`）：

| 成员 | 作用 |
|---|---|
| `_register_click()` | 记一次物理点击 + 调 `on_tap()`（彩蛋计数）|
| `_resolve_gesture()` | 按计数派发 single / double / triple |
| `_suppress_release` | dblclick 后面那个 release 不重复计数 |
| `_gesture_timer` | 单击挂起 `GESTURE_WAIT_MS`（500ms，等后续点击）|
| `GESTURE_WAIT_MS = 500` | **= 系统 `GetDoubleClickTime()` 默认值** |
| `GESTURE_WINDOW_MS = 700` | 间隔超过这个算新的一串（慢速点击互不串台）|

> **为什么等待窗口要 500ms**：只有 >= 系统双击间隔，
> 慢一点的真人双击（300ms 间隔）才能被识别成双击而不是两次单击。
> 代价是单击响应有 500ms 延迟 —— 这是双击识别的固有代价，
> 气泡弹出动画本身 220ms，感知上还能接受。

> **为什么计数必须与手势解耦**：彩蛋解锁要连点 30 次，
> 如果计数跟着手势走，连点会被判成多击、一次只 +1，
> 解锁遥遥无期。所以 `on_tap()` 在事件层（每次物理点击 +1），
> 手势语义在结算层。
#### ⚠️ 坑 2：贴纸气泡和额度气泡共用一个窗口，必须显式互斥

两者都走同一个 `BubbleWindow`，`set_content()` 一调用就把 `_sticker` 清空。
三个地方会抢：

| 抢气泡的路径 | 触发条件 | 处理 |
|---|---|---|
| `_refresh_bubble_content()` | 额度后台拉完 → `_quota_dirty` | 加 `_bubble_mode != "sticker"` 守卫 |
| `_apply_state()` | MiMo 发来 `happy` 事件 → `show_bubble()` | 加 `_bubble_mode != "sticker"` 守卫 |
| `shot_mimo.py` | 截图脚本自己会发 `{"action":"bubble"}` | 加 `--keep` 参数跳过 |

根因是「切表情 → MiMo SSE 回 happy → 抢回额度气泡」这条回环。

#### ⚠️ 坑 3：单击不能把贴纸盖掉，但也不能换贴纸

解锁后如果单击直接 `show_bubble()`，用户双击看到的贴纸一下就没了。
所以 `on_click` 里要先判断当前是不是贴纸气泡。

但**不能**在单击里换贴纸 —— 换贴纸只认双击（见 §8.5 交互表）。
单击在贴纸模式下只做一件事：收起气泡，而且要延迟 350ms 确认不是双击。

#### ⚠️ 坑 4：实机点击有命中率，不是 100%

桌宠窗口是 220×220 方形，但角色实体只占帧内 y=24..247，裙摆/帽尖处是镂空的，
点空了会**穿透**到 MiMo 底下的窗口。

实测命中率约 87%（30 次计数需要约 35–40 次物理点击）。
`tools/find_pet_hit.py` 用 alpha 掩膜算出实体的实心区域，
推荐点击点是**帧内 (135, 69)**（脸/胸），换算到 220px 窗口 = **(116, 59)**，
不要盲点窗口正中 (110, 110)。

> ⚠ **2026-11-09 实测修正**：`(116, 59)` 这个点在某些帧上是**镂空的**
> （脸部中央），点下去会穿透到 MiMo，桌宠收不到。稳妥做法是像
> `tools/test_sticker_switch.py` 那样：先 PrintWindow 抓当前帧，
> 找出非背景像素的**角色中心**（实测约窗口内 `(110, 126)`），点那里。
> 角色实心包围盒实测 x 8..208、y 22..210。

#### ⚠️ 坑 5：验收要看窗口尺寸，不能只看像素颜色

气泡是半透明的，`PrintWindow` 抓到的像素会被 MiMo 深色背景污染
（额度气泡的非白占比也有 94.8%），靠颜色占比判断贴纸/额度会误判。
**用桌宠内部状态区分最可靠**：`pet_status.json` 的 `egg.sticker_mode`（= 气泡控件的 `_sticker` 字段）。窗口尺寸只作兜底：贴纸固定 228×270，额度当前 301×172（宽度随内容变、高度随行数变）。

#### ⚠️ 坑 6：`drag_to()` 必须放在位移阈值判断**里面**

`mouseMoveEvent` 原来长这样：

```python
if (gp - self.press_pos).manhattanLength() > 6:
    self.moved = True
self.controller.drag_to(gp)      # ← 在 if 外面！
```

阈值判断只用来置 `moved` 标志，`drag_to()` 却是**无条件**调用的。
后果：按住鼠标时哪怕只有 1 像素抖动，桌宠也会被拽到光标处。
而「点击前 `SetCursorPos`」产生的 `WM_MOUSEMOVE` 可能在按下之后才送达，
于是**「连点 30 次解锁」的过程中桌宠会一路乱跑**，后面的点击全打空
（实测计数一直是 0）。

改成：

```python
if self.moved or (gp - self.press_pos).manhattanLength() > 6:
    self.moved = True
    self.controller.drag_to(gp)
```

一旦真的开始拖就继续跟随，没超过阈值则完全不动。

#### ⚠️ 坑 7：测试脚本要先让桌宠回到确定状态

贴纸模式下单击 = 收起气泡（不换贴纸）。如果上一轮测试留下了一张贴纸气泡，
下一轮的「单击应弹额度气泡」就会变成「单击把贴纸收起来」→ 断言必挂。

解决：给桌宠加一个 `{"action": "hidebubble"}` 指令（收起气泡并把模式归位到
「额度」），测试开头先发一次，再发 `{"action":"egg","what":"reset"}`。
顺序不能反 —— 收起气泡的那一下单击也会把计数 +1，所以要「先收起、后重置」。

同理，真实鼠标那一节要把 MiMo 提到最前
（`SetWindowPos(TOPMOST)` → `SetForegroundWindow` → `SetWindowPos(NOTOPMOST)`），
否则同时开着的浏览器盖在 MiMo 上面，点击全落在浏览器身上。

#### ⚠️ 坑 8：真实鼠标事件链路里，QTimer 不可靠（改用轮询）

双击的贴纸要延迟 `TRIPLE_WAIT_MS` 才弹（避免三击时贴纸先亮）。
第一版用 `QTimer(self.app)`，实测 **timeout 永远不触发**：

```
debug = 'pending active=True'    # 定时器是活的，但就是不来
```

换成 `QTimer.singleShot()` 同样不触发。

原因不明（可能是真实鼠标事件的回调链路与主事件循环的定时器不兼容），
但结论明确：**这种延迟不要用 QTimer**。

改成在 `Controller._tick()` 里轮询时间戳（每 33ms 一次，一定在主线程）：

```python
if self._sticker_pending and time.time() >= self._sticker_due:
    self._show_next_sticker()
```

立刻就稳定了。`QTimer.singleShot` 无法取消，所以配套用
`_sticker_pending` 标志位判断是否已被三击 / `hidebubble` 取消。

#### ⚠️ 坑 9：贴纸延迟弹出期间，额度刷新会抢气泡

贴纸延迟 260ms 弹出，这段时间里 `_bubble_mode` 如果还是 `quota`，
`_refresh_bubble_content()` 在额度数据回来时会 `_render_bubble()`，
把气泡重绘成额度卡片 —— 贴纸就**永远弹不出来**（实测气泡尺寸一直是 301×172）。

解决：双击排队时**立刻**把 `_bubble_mode` 占位成 `sticker`，
并用 `_sticker_pending` 标志让 `_refresh_bubble_content()` 和
`_apply_state()` 在这段窗口内都不许重绘气泡。

#### ⚠️ 坑 10：PostMessage 测不了双击（延迟 0.5~1 秒）

`tools/test_egg_live.py` 原来用 PostMessage 发点击，实测每次点击要
**0.5~1 秒**才被 Qt 收到（状态文件每秒刷一次，掩盖了真实时序）。
两次点击的间隔因此远超任何合理的双击判定窗口 -> **永远测不出双击**。

结论：**测双击必须用真实鼠标**（`mouse_event` + `SetCursorPos`），
且先把 MiMo 提到最前，否则点击会被别的应用抢走。
`tools/test_gesture_live.py` 就是这么写的（真实鼠标 + 多候选命中点）。

另外 `pet_status.json` 是**每秒**刷新的，用它做时序断言会引入
最多 1 秒的误差 —— 精确时序要在桌宠内部记录（见 `_click_log`）。

---

## 9. 自动贴边

`Controller.snap_position()`：

- 候选：四角 + 四边（保持另一轴坐标）
- 阈值 34px（角用 34×1.6 的欧氏距离），取最近的一个
- 没到阈值就只夹进客户区，不吸附

另有**空闲自动溜达**（`wander`）：50–120 秒随机走向某个角，6px/帧平滑移动。

配置里有 `layout_version: 2` —— v1 是「桌面浮窗的屏幕坐标」，v2 是「MiMo 客户区坐标」，
语义变了会自动重置位置，避免老配置把桌宠甩到屏幕外。

---

## 10. 可复现命令清单

```powershell
# ---- 素材 ----
python 'D:\桌面宠物\tools\grid_parts.py'                                  # 打网格核对部件坐标
python 'D:\桌面宠物\tools\build_anim_sheet.py' --out 'D:\桌面宠物\build\mimo-witch' --gif
python 'D:\桌面宠物\tools\diff_anim.py'                                    # 动画活跃度量化
python 'D:\桌面宠物\tools\build_mate_sheet.py'                             # 派生 Mate 精简版

# ---- 路线 A：装进 MiMo 原生 pets 目录 ----
python 'D:\桌面宠物\tools\install_mate_pet.py' --src 'D:\桌面宠物\build\mimo-witch-mate' --dry-run
python 'D:\桌面宠物\tools\install_mate_pet.py' --src 'D:\桌面宠物\build\mimo-witch-mate'
python 'D:\桌面宠物\tools\verify_installed.py'                             # 从安装位置独立字节级复核

# ---- 路线 B：桌宠 ----
python 'D:\桌面宠物\tools\pet_control.py' start
python 'D:\桌面宠物\tools\pet_control.py' status
python 'D:\桌面宠物\tools\pet_control.py' bubble
python 'D:\桌面宠物\tools\pet_control.py' quota
python 'D:\桌面宠物\tools\pet_control.py' corner br
python 'D:\桌面宠物\tools\pet_control.py' set think
python 'D:\桌面宠物\tools\pet_control.py' auto
python 'D:\桌面宠物\tools\pet_control.py' stop

# ---- 验证取证 ----
python 'D:\桌面宠物\pet\show_mimo.py'          # 把 MiMo 从托盘唤出来
python 'D:\桌面宠物\tools\shot_mimo.py'         # 截图 + 打印 owner / rect / 是否在窗口内
python 'D:\桌面宠物\tools\test_follow.py'      # 移动 / 缩放 / 最小化 / 恢复 全套跟随性
python 'D:\桌面宠物\pet\mimo_quota.py'         # 额度快照 + cookie 库可读性
python 'D:\桌面宠物\tools\probe_owner.py'      # 复现「Qt show() 清 owner」

# ---- 眨眼调试（见 §6.6）----
python 'D:\桌面宠物\tools\blink_strip.py' idle  '_mimo\strip-idle.png' --scale 1   # 验收视图：256px 动画带
python 'D:\桌面宠物\tools\blink_final.py' think EYE_L '_mimo\bf-think.png'          # 眼部六档放大
python 'D:\桌面宠物\tools\eye_geom.py'  think EYE_L 10                             # 眼睛几何
python 'D:\桌面宠物\tools\eye_cols.py'  think EYE_L 640 700                        # 逐列原始测量 + 有效性
python 'D:\桌面宠物\tools\blink_plan.py' idle 0.6 EYE_L                            # 每列决策值
python 'D:\桌面宠物\tools\blink_cols.py' idle 0.6 700 730 985 1170 6               # 2048 空间逐列剖面
python 'D:\桌面宠物\tools\blink_diff.py' think 0.0 0.6 '_mimo\d.png' --nowarp      # 256px 像素差分
python 'D:\桌面宠物\tools\frame_cols.py' think 0.0,0.6 --nowarp                    # 256px 逐列剖面
python 'D:\桌面宠物\tools\blink_frame.py' think 0.6 '_mimo\f.png' --nowarp         # 存单帧 256px
```

```powershell
# ---- 彩蛋表情包（见 §8.5）----
python 'D:\桌面宠物\tools\build_stickers.py'          # 生成贴纸卡片 + index.json
python 'D:\桌面宠物\tools\render_eggs.py'             # 渲染 9 张贴纸气泡 + 汇总图
python 'D:\桌面宠物\tools\test_egg.py'                # 彩蛋逻辑自测（计数/解锁/轮换/持久化）
python 'D:\桌面宠物\tools\test_egg_live.py' 30        # 实机全流程（单击/解锁/双击/三击 + owner）
python 'D:\桌面宠物\tools\test_sticker_switch.py'     # 实机验证贴纸点击规则（双击出/换，单击只收起）
python 'D:\桌面宠物\tools\find_pet_hit.py' idle       # 算桌宠实体的实心点击点
python 'D:\桌面宠物\tools\probe_place.py'             # 算贴纸气泡在客户区内的摆位
python 'D:\桌面宠物\tools\probe_live_bubble.py'       # 读实机气泡窗口几何
python 'D:\桌面宠物\tools\pet_control.py' egg sticker # 抽一张贴纸
python 'D:\桌面宠物\tools\pet_control.py' egg unlock  # 直接解锁并弹一张
python 'D:\桌面宠物\tools\pet_control.py' egg reset   # 重置彩蛋进度
python 'D:\桌面宠物\tools\shot_mimo.py' --keep        # 截图但不动气泡（保住贴纸气泡）
```

---

## 11. 排错表

| 症状 | 原因 / 处理 |
|---|---|
| MiMo 设置里找不到 Mate | **本版就没有这个功能**（见 §0），走路线 B |
| 桌宠不在 MiMo 窗口里 | `shot_mimo.py` 看 owner 指针；不是 MiMo hwnd 就是没绑上（检查 `show()` 后是否重置） |
| MiMo 收进托盘后桌宠也消失 | **预期行为**；`python 'D:\桌面宠物\pet\show_mimo.py'` 唤回 |
| 桌宠跟着 MiMo 跑但位置不对 | `layout_version` 被改过；把它改回 2 或删掉 `pet_config.json` 里的 x/y |
| 桌宠不跟着变脸 | `pet_control.py status` 看「事件连接」；未连接说明 MiMo 没开或 token 变了，重启桌宠 |
| `最近事件` 停在 `idle` | MiMo 当前没有活动会话；在 MiMo 里发一句话即可 |
| 气泡额度取不到 | 首次需要 MiMo 未运行时抓 cookie；跑 `pet_mimo_quota.py` 单独确认 |
| 桌宠空白 | 素材目录不对；跑 `pet_control.py selftest` |
| 点不到桌宠 | 桌宠裙摆/帽尖是镂空的，点空会穿透；用 `find_pet_hit.py` 算实心点 |
| 桌宠启动后立刻退出 | `pet_cmd.json` 残留 `quit`；`pet_control.py stop` 会清理，启动时也会忽略旧指令 |
| MiMo API 全 404 | 少了 `/v1` 前缀 |
| MiMo API 403 forbidden-host | `Host` 头不是 `127.0.0.1:<port>` |
| 平台 API 404 | 少了 `/api/v1` 前缀 |
| 眨眼时眼睛变成一条竖直白条 | 虹膜高光被当成眼白搬下去了；见 §6.6「填充取样基准」 |
| 眨眼时眼睛变成一块白板 | 填充色太亮 / 闭合度太高；见 §6.6「填充色」和「最大闭合度」 |
| 眨眼时睫毛断成两截 | 工作区被截断了（眼白污染上沿 / gap 太严）；见 §6.6 |
| 眨眼时眼睛只剩一根黑杠 | 睫毛带加粗系数太大（别超过 0.12） |
| `verify_installed.py` 报「sha256 与构建产物不一致」 | 比对目录应是 `build\mimo-witch-mate`（装进去的是 Mate 精简版），不是 `build\mimo-witch` |
| `verify_installed.py` 报「帧尺寸与官方预设不一致」 | 官方预设用 240×240，我们用 192×192；契约允许（`frameWidth` 由 manifest 自声明），已改成提示 |
| 连点几十次也不出彩蛋 | **双击**才出贴纸，单击永远是额度卡片；没到 30 次会 toast「再多点几下试试？还差 N 次」 |
| 一直点不出单击 | 多击判定用「release 计数 + 500ms 挂起窗口」，**不靠 dblclick 事件**（这个环境下 DBLCLK 根本不合成）；见 §8.5 坑 1 |
| 单击把贴纸气泡盖掉了 | 现在的行为：贴纸模式下单击**切回额度气泡**（查看用量），不换贴纸；换贴纸只认双击；见 §8.5 坑 3 |
| 三击也弹出贴纸了 | 双击的贴纸是**延迟 260ms** 弹的（等三击窗口过去）；如果看到三击出贴纸，检查 `_sticker_pending` / `_bubble_mode` 占位逻辑；见 §8.5 坑 9 |
| 双击没反应（真实鼠标） | 先确认点击命中了角色实体（桌宠是 layered window，镂空处会穿透）；再确认两次点击间隔 < 500ms（= 系统双击间隔）；见 §8.5 坑 1、坑 4 |
| 贴纸延迟弹不出来 | 用 QTimer 做延迟在这项目里不触发，改用 `_tick` 轮询时间戳；见 §8.5 坑 8 |
| 贴纸弹出来又变回额度气泡 | MiMo 的 happy 事件抢气泡；`_apply_state` / `_refresh_bubble_content` 都要加 `_bubble_mode != "sticker"` 守卫；见 §8.5 坑 2 |
| 截图里看不到贴纸 | `shot_mimo.py` 自己会发 `bubble` 指令覆盖掉；加 `--keep` |
| 贴纸气泡跑到屏幕外（rect ≈ -32000） | MiMo 被最小化了，owned 窗口跟着隐藏；先 `force_front.py` |
| 贴纸气泡位置不对 / 超界 | 贴纸气泡固定 228×270，比额度气泡（当前 301×172，宽度随内容变）大不少；`place_bubble` 会夹进客户区，先看 `probe_place.py` |
| 判断不出是贴纸还是额度气泡 | **看 `pet_status.json` 的 `egg.sticker_mode`**（100% 可靠）；窗口尺寸只作兜底（贴纸固定 228×270，额度当前 172 但高度随行数变、宽度随内容变）。别看像素颜色：气泡半透明，PrintWindow 会被 MiMo 深色背景污染；见 §8.5 坑 5 |
| 实机连点只有一半命中 | 桌宠裙摆/帽尖处是镂空的，点空会穿透；用 `find_pet_hit.py` 算实心点，别点窗口正中 |

---

## 12. 与 DSH 鲸鱼挂件的路线差异

| 维度 | DSH 鲸鱼挂件 | MiMo 原生 Mate | 本文路线 B |
|---|---|---|---|
| 形态 | cordis 插件 bundle | 静态资源目录 | 独立进程 + owned window |
| 分发 | `cordis.patch.yml` + `lib/` + `assets/` | 一个文件夹两个文件 | 一个 Python 程序 |
| 数据 | 26 个 `/dsh-whale/*` 路由 + `$DSH_HOME/.dshw-*.json` | 无状态 | 无状态 |
| 动效 | CSS transform 驱动单张 PNG | 精灵图逐帧播放 | 精灵图逐帧播放（Qt 定时器） |
| 形象 | 单张 610×610 cut-out PNG | WebP 精灵图 + manifest | 同左 |
| 状态绑定 | 自己实现状态机 | 未知 | MiMo `/v1` SSE |

### 从 DSH 借来的可复用参数

- 2.5 头身 Q 版；呼吸/摆动幅度**极小**（translateY −3px/3.4s、rotate ±1.2°/6s、transform-origin 50% 90%）
- 过冲缓动统一 `cubic-bezier(.34,1.4,.64,1)`
- 圆角 ≥10px；气泡 10–12px 圆角 + 8–12px padding + 过冲弹出
- 「忙」用发光不用变色；随机眨眼 3–9s；随机换朝向 10–25s

参考图已下载到 `D:\桌面宠物\_reference\dsh\`（81 文件 / 23MB）。

---

## 13. 启动与守护（路线 B 的运行方式）

> 2026-11-08 补。前面的 §5~§10 讲的是「桌宠怎么工作」，这一节讲「桌宠怎么被拉起来」——
> 这是两件完全不同的事，也是最容易踩坑的地方。

### 13.1 坑：桌宠和 MiMo 是两个完全独立的进程

| 方向 | 有没有 | 说明 |
|---|---|---|
| 桌宠 → MiMo | ✅ 有 | `launch_mimo: true` 时，桌宠启动发现 MiMo 没跑就把它带起来（带 `--remote-debugging-port`）|
| MiMo → 桌宠 | ❌ **没有** | **手动开 MiMo 不会带出桌宠** |

工程里唯一让两者同时起来的途径是**开机自启脚本**（开机执行一次）。
用户中途手动点 MiMo 图标，桌宠不会出现 —— 除非桌宠本来就在跑。

桌宠一旦退出（崩溃 / 被关掉），也**没有任何东西会把它拉回来**。

### 13.2 现在的启动结构：MiMo 联动（2026-11-09 定案）

用户要求：**不用桌面快捷方式，只要 MiMo 开启就联动唤醒桌宠、MiMo 关闭就关闭桌宠**。

```
注册表 Run（登录自启，静默 pythonw，无控制台窗口）
     │
     └─→ tools\launch_mimo_pet.py --watch      ← 常驻 watcher
              ├─ MiMo 在跑 且 桌宠没跑 → 拉起桌宠
              └─ MiMo 不在 → 什么都不做（桌宠自己会退）
                          │
                          ▼
                 pet\mimo_pet.py  桌宠
                   ├─ attach_host() 找到 MiMo 窗口 → 挂上去显示
                   └─ 找不到 MiMo 持续 exit_grace 秒 → 退出进程
```

| 层 | 频率 | 作用 |
|---|---|---|
| 注册表 Run 项 | 登录一次 | 用 `pythonw.exe` 静默拉起 watcher，**全程无控制台窗口** |
| `launch_mimo_pet.py --watch` | 每 2 秒 | MiMo 在跑且桌宠没跑 → 拉起桌宠 |
| 桌宠 `_maybe_exit_with_mimo()` | 每 33ms | 找不到 MiMo 持续 `exit_grace`（默认 8s）→ 退出进程 |

| 配置项 | 默认 | 含义 |
|---|---|---|
| `link_mimo` | `true` | 联动开关：MiMo 关 → 桌宠退 |
| `exit_grace` | `8.0` | 找不到 MiMo 多少秒后退出（给 MiMo 冷启动留宽限）|
| `launch_mimo` | `false` | 桌宠**不再**主动把 MiMo 带起来 |

**为什么不用计划任务**：原方案有 `MiMoPetGuard`（每分钟）→ `guard_task.cmd`，
cmd.exe 会闪一个黑框，用户明确要求去掉。注册表 Run 项用 `pythonw.exe`，无窗口。

**实测（2026-11-09）**：MiMo 在跑 → watcher 起来后桌宠约 12 秒自动出现；
关掉 MiMo → 4 秒时还在（宽限期）、18 秒后进程已退出；重开 MiMo → 桌宠自动回来。

**用户右键「退出」桌宠**写 `pet\pet_disabled` 标记，watcher 尊重它；
联动退出（MiMo 关）**不写**该标记，所以 MiMo 再开时桌宠会回来。

### 13.3 常用命令

```powershell
# 一键启动（等价于双击桌面快捷方式）
python 'D:\桌面宠物\tools\launch_mimo_pet.py'

# 安装 / 撤掉三处入口
python 'D:\桌面宠物\tools\setup_launcher.py'
python 'D:\桌面宠物\tools\setup_launcher.py' --uninstall

# 原来的控制 CLI 仍然可用
python 'D:\桌面宠物\tools\pet_control.py' status
```

日志：`pet\pet_watchdog.log`（守护动作）、`pet\launcher.log`（每次启动器运行），
都封顶 512KB。

### 13.4 实现时踩到的坑

1. **拉子进程必须把 stdio 重定向到 DEVNULL**。不重定向的话，子进程会继承
   父进程的管道句柄，父进程一退出句柄就失效 → 子进程**启动即死**
   （表现：日志只有「watchdog 启动」那几行，进程却不在）。
2. **不能用「命令行里含脚本名」判断进程在不在**。任何一条 shell 命令提到这个
   文件名都会被误判成「它已经在跑」——包括 `grep` 和你自己的检查命令。
   要按**参数精确匹配**（basename 相等）并排除 shell / grep。
3. **「桌宠在跑」的判定不能和状态文件里的 pid 比对**。psutil 的进程迭代顺序
   不保证，`find_by_script` 返回的第一个可能不是状态文件里那个 → 误判成
   「没跑」→ **无限拉起重复实例**（实测同时最多 4 个）。
   正确做法：存在任一 `mimo_pet.py` 进程即算在跑，并顺手清掉多余的。
4. **计划任务用 `schtasks` 而不是 `Register-ScheduledTask`**：后者在非管理员
   会话里报「拒绝访问」。而且 `schtasks` 直接执行 GUI 程序（`pyw.exe`）实测
   不生效，要套一层 `.cmd` 包装；包装脚本必须是 **GBK**（cmd.exe 按 ANSI 936 读）。
5. **从 shell 调 `schtasks` 会把中文路径弄坏**，要从 Python 里调
   （`subprocess` 走 `CreateProcessW`，Unicode 参数原样送达）。
6. **MiMo 重启会换端口和 token**（实测 52848 → 56551）。SSE 流断开走的是
   `stream_events`，不经过 `_request` 的异常清理路径，缓存的旧凭据会留着 →
   下一轮请求打在一个没人听的端口上，要等 10 秒超时才恢复。
   现在重连时主动 `refresh_creds()`，实测重连耗时 **12 秒 → 4.1 秒**。

7. **加了守护层之后，用户就再也关不掉桌宠了**。watchdog 每 10 秒、
   计划任务每 1 分钟都会把桌宠拉回来，用户点右键「退出」11 秒后它又出现了。
   解法：退出时写一个「已停用」标记文件 `pet\pet_disabled`，
   watchdog 和**后台模式**（`--auto`）的启动器都尊重它；
   手动跑启动器 / `pet_control.py start` 则清掉标记。
   区分「用户主动关」和「意外崩溃」靠的就是这个标记。
8. **从计划任务启动 MiMo，窗口可能是隐藏的**（进程在、窗口不在）。
   用户看到的是「MiMo 开着但什么都没有」—— 而桌宠是 owned window，
   owner 隐藏它也跟着隐藏，等于两头都看不见。
   现在启动器 / 桌宠自己拉起 MiMo 后都会调 `mimo_host.show_mimo_window()`
   主动 `ShowWindow(SW_SHOW)`。
   ⚠️ `ShowWindow` 的第一个参数是 HWND（指针宽），**不声明 argtypes 的话
   ctypes 默认按 c_int 传，64 位下句柄被截断，调用直接没效果**。
9. **桌宠可能比 MiMo 先起来**（watchdog / 计划任务都是这样）。
   这时 MiMo 还没跑，客户区尺寸是 0，算出来的坐标是垃圾，
   桌宠会被**永久钉在 MiMo 的左上角**。更糟的是退出时 `quit()` → `_save_pos()`
   会把这个退化的 `(0,0)` 写回配置，把用户记住的位置冲掉。
   解法：位置算不出来时标记 `_pos_deferred`，等 `attach_host()` 挂上宿主后
   再按记忆的角落贴位；`_save_pos()` 在 `_pos_deferred` 期间**不落盘**。
10. **贴边的「边」标签（l/r/t/b）必须能被 `corner_pos()` 认**。
    `snap_position()` 会产出这四种标签并存进 `cfg["corner"]`；
    如果 `corner_pos()` 只认四个角，`table.get(corner, table["br"])` 会把边标签
    静默吞成「右下角」—— 用户把桌宠拖到右边贴住，重启后它自己跳到右下角。

### 13.5 排错补充

| 症状 | 原因 / 处理 |
|---|---|
| MiMo 开着但没有桌宠 | 桌宠进程没在跑：`pet_control.py status` 看「运行中」；`tasklist` 里应有 pythonw.exe |
| 桌宠进程在但 MiMo 开着也不挂上去 | 看 `pet_status.json` 的 `hosted`；为 false 说明没找到 MiMo 宿主窗口 |
| 有好几个桌宠 | 老版本 watchdog 的判定 bug（§13.4 第 3 条）；现在会自动清理，手动 `taskkill` 多余的也行 |
| 桌宠不跟着变脸 | 看 `last_error`；MiMo 刚重启的话等几秒，端口/token 会自动刷新 |
| 额度气泡报「未以调试端口启动」 | 当前 MiMo 没带 `--remote-debugging-port=9333`；桌宠右键菜单 →「重启 MiMo（启用额度读取）」|
| 额度显示「无有效订阅（套餐已到期）」 | 小米账号的套餐真的到期了（`plan_status: EXPIRED`），不是代码问题 |
| 桌宠退出后过一会儿又自己出现 | 用户主动退出时应该写 `pet\pet_disabled` 标记；标记在就说明退出路径没走到（桌宠被强杀）。删掉标记 + `pet_control.py start` 即可 |
| 桌宠重启后跑到 MiMo 左上角 | 老 bug：桌宠先于 MiMo 启动时坐标退化成 (0,0) 且被写回配置。见 §13.4 第 9 条；把 `pet_config.json` 的 `x`/`y` 改回想要的值 |
| 桌宠拖到右边贴住，重启后跳到右下角 | 老 bug：`corner_pos()` 认不了 l/r/t/b 边标签。见 §13.4 第 10 条 |
| MiMo 开着但窗口看不见、桌宠也不见 | MiMo 进程在但窗口是隐藏的；跑 `python 'D:\桌面宠物\pet\show_mimo.py'` 唤出来（启动器现在会自动处理） |
| 桌宠被拖到屏幕外 | `pet_config.json` 的 `x`/`y` 是 MiMo 客户区坐标；直接改这两个值，或右键菜单 →「位置」选个角 |
