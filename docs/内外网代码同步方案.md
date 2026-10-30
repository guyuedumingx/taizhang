# 内外网代码同步方案（netsync）

**日期**：2026-10-26
**适用场景**：内网与外网代码差异大、历史不同源；**内网→外网只能人工复制粘贴文本**；**外网→内网可由同事捎带文件**。内网为 Windows + Python3 + git，代码体积 5MB 以内，低频（周/节点）同步。

---

## 一、总体架构

```
        外网（本机，git 仓库）                    内网（Windows，git 仓库）
  ┌────────────────────────────┐          ┌────────────────────────────┐
  │  feature 分支（日常开发）    │          │  内网分支（内网真实状态）     │
  │          ↓ cherry-pick/合并 │          │          ↓ git commit       │
  │  intranet 桥接分支（镜像内网）│◄─文本────│  netsync pack（全量/增量）   │
  │  （所有冲突在这里解决）       │  剪贴板   │  netsync/netsync.py        │
  └────────────┬───────────────┘          └────────────▲───────────────┘
               │ git bundle 文件                        │ git fetch bundle + merge
               └──────────────► 🧑‍🏫 捎带进内网 ──────────┘
```

两条原则：

1. **所有"聪明活"在外网做**：桥接分支永远等价于"内网最新状态 + 外网要送进去的改动"，冲突在外网解决完，内网拿到的总是接近快进的合并。
2. **内网只做"傻瓜操作"**：双击 .bat 打包 / 双击确认；收 bundle 后两条 git 命令。

工具：`netsync/netsync.py`（纯标准库，内外网同用，无需安装任何依赖）。

---

## 二、首次部署（一次性）

1. 🧑‍🏫 把 `netsync/` 文件夹（含 netsync.py + 3 个 .bat）拷到**内网代码仓库根目录**下。
2. 内网仓库 `.gitignore` 追加两行（防止内部文件污染提交）：
   ```gitignore
   .netsync-state.json
   out_sync/
   ```
3. 建议此时先 `git add -A && git commit`，把内网工作区收拾干净（增量协议要求，见下）。

---

## 三、场景 A：初始全量对齐（第一次把内网代码发出来）

**内网**（仓库根目录）：

```bat
双击 netsync\pack_full.bat        （= python netsync\netsync.py pack --full --out out_sync）
```

生成 `out_sync/000_manifest.txt + 001_chunk.txt …`（约 3~7 个文件，5MB 代码压缩后约 2~4 趟粘贴）。

**体积守卫（防"一次打出几百个块"）**：全量产物默认上限 25MB，超过会**中止并列出体积最大的 20 个文件与顶层目录合计**，按提示用 `--add-exclude 目录,.扩展名` 裁剪后重试（确实全要带加 `--yes`）。另有单文件上限 10MB（`--max-file-mb` 调整）。**想先看会打包什么**，运行：

```bash
python netsync/netsync.py analyze          # 只报告清单/体积/块数估计，不生成文件
```

> 2026-10-26 内网实录：首次运行打出了 290 个块（约 150MB）——原因是仓库里混入了不在默认排除名单内的大目录。守卫上线后此类情况会被拦在生成文件之前，并直接告诉你大头是谁。

**人工带出（iPhone 通道）**：逐个 txt → 全选复制 → 另存为同名 txt，全部放进外网一个文件夹（如 `pasted/`）。要点：

- **顺序与文件名都不重要**——外网按内容 sha256 匹配拼装，名字乱了、多保存了"副本 2"都不影响；
- 内容是纯 ASCII（base64），iPhone 上不会出现乱码/自动替换；尾随空行无所谓，会自动清掉；
- 唯一硬要求：**一个块一次复制完**，别分两次复制同一个块（内容对不上会精确报出是哪块）；
- **块大小可调**：打包加 `--chunk-kb <数值>`（默认 200，即每块约 200KB 文本）。手机 app 打开/全选卡顿就调小（如 100）；嫌每个文件一整套"打开→全选→另存"太费手就调大（如 400~700，块数随之减少）。**同一次打包的数据量固定：块更短必然块数更多，二者不可兼得**——想真正减少复制量，靠的是增量同步（diff 通常一个块）和 `--add-exclude` 裁剪，不是调块大小。
- **压缩已用 xz(LZMA)**（2026-10-26 起）：同样的数据比早期 gzip 版少约 25~30% 粘贴量（本仓库实测 3.87MB 源码：gzip 路线 2.80MB → xz 路线 2.02MB）。旧版产出的 gzip 包外网仍可正常解开（按数据头自动识别）。注意：**块 txt 本身无法"二次压缩"**——里面是已压缩数据的 base64，呈随机态，任何压缩器都压不动。

**外网**（本仓库根目录）：

```bash
python3 netsync/netsync.py unpack --indir pasted --dest /tmp/intranet_snapshot
```

脚本逐块 sha256 校验：哪块坏了/缺了会点名（如"块 2/5 需重拷"），**只需重拷那一块**。

**建桥接分支**（外网仓库，一次性）：

```bash
git checkout --orphan intranet
git rm -rf --quiet .          # 清掉 index（工作区文件不受影响）
# 用快照内容替换工作区后：
git add -A && git commit -m "intranet baseline 对齐"
```

**回内网确认基线**：双击 `netsync\sync_ok.bat`。此后才能走增量。

> 若内网当时工作区不干净：全量照常能发，但脚本会提示"无法记增量基线"——先内网 commit 后重新 `pack_full` 一次即可。

---

## 四、场景 B：日常同步——内网改动发出来（增量）

**内网**：

```bash
git add -A && git commit -m "本阶段改动"     # 1) 先提交（增量协议要求干净工作区）
```
```bat
双击 netsync\pack_delta.bat                  # 2) 打增量包（diff 自上次基线 + 新文件）
```

**人工带出** → **外网**（在 intranet 桥接分支的工作区）：

```bash
git checkout intranet
python3 netsync/netsync.py unpack --indir pasted --dest .
git add -A && git commit -m "sync: 内网 <日期> 增量"
```

**回内网双击 `sync_ok.bat`** —— 这一步推进增量基线，**不做的话下次会把本轮内容重发**（外网会拦截并提示先 ok）。

### 确认协议（为什么要有 sync_ok）

打包时不知道外网是否应用成功，所以基线只在**外网 unpack 成功后、由内网确认**才推进。三种意外都有兜底：

| 意外 | 表现 | 恢复 |
|------|------|------|
| 忘了 sync_ok 又打包 | 外网应用报"已应用过"，提示先 ok | 内网 ok → 重新打包 |
| 外网应用失败（桥接分支不对） | 明确报错，不改代码 | 切到正确分支重试，或让对方改发 --full |
| 块损坏/缺失 | 点名哪一块 | 只重拷该块 |

---

## 五、场景 C：外网改动送进内网（git bundle 文件）

**外网**（把要送的功能落到桥接分支，冲突在这里解决）：

```bash
git checkout intranet
git cherry-pick <feature 分支的相关提交>     # 或 merge；冲突此时此地解决
git add -A && git commit
git bundle create to_intranet.bundle intranet
```

`to_intranet.bundle` 交给 🧑‍🏫 捎进内网（放到内网仓库目录）。

**内网**：

```bash
git fetch to_intranet.bundle intranet:from-external
git merge from-external
```

首次合并不同源历史时 git 会拒绝，加 `--allow-unrelated-histories`。若内网自己也有改动触及相同文件，此步会出现冲突——在**内网**解决一次（这是唯一可能要在内网解决冲突的地方，尽量通过"外网先吸收内网最新增量再出 bundle"来避免）。

> 退化方案：内网同事不熟 git 时，可改为外网直接把**改动后的完整文件**打进 zip 捎进去，用 Beyond Compare 之类目录对比工具手工覆盖。

---

## 六、数据与安全

- `.env`、`*.db`、`*.log`、`venv/`、`node_modules/`、`.git/` 默认**不打包**；确需带 `.env` 加 `--include-env`（内网真实凭据出网前请确认合规）。
- 每块带 sha256、整包带总校验，剪贴板截断/换行污染（CRLF）均已免疫（已测试）。
- 代码离开内网需遵守公司规定，本方案只解决技术通道。

---

## 七、速查

| 动作 | 内网 | 外网 |
|------|------|------|
| 看会打包什么 | `python netsync\netsync.py analyze` | — |
| 全量 | `pack_full.bat` → 复制 out_sync 全部 txt | `unpack --indir pasted --dest 快照目录` → 建桥接分支 |
| 增量出 | commit → `pack_delta.bat` → 复制 txt | （intranet 分支）`unpack --indir pasted --dest .` → commit |
| 确认 | `sync_ok.bat` | — |
| 送进 | `git fetch bundle … && git merge` | cherry-pick 到 intranet → `git bundle create …` |

已验证：全量/增量往返逐字节一致、中文文件名、二进制、CRLF 污染、块截断/缺块/头丢失精确报错、忘记 ok 的重发拦截（共 13 项回归）。

---

## 八、bat 闪退排查

历史教训：首批 .bat 是在 macOS 上生成的 **LF 行尾**，Windows cmd 解析会直接失败退出（窗口一闪而过，连 pause 都到不了）。2026-10-26 已修复为 CRLF + 扁平标签逻辑，并把失败路径都加了 pause 与明确报错（找不到 .git / 找不到 Python / 找不到 netsync.py 均会停住显示原因）。

替换新版 bat 后如果仍然闪退，按此定位真实报错：

1. `Win+R` 输入 `cmd` 回车，**先开住一个黑窗口**；
2. 把 bat 文件直接拖进该窗口，回车执行——窗口不会自动关闭，报错会留在屏幕上；
3. 常见报错对照：
   - `不是内部或外部命令 python/py` → 内网机没装 Python 或不在 PATH（bat 会给出同样提示）；
   - `[ERROR] No .git found` → netsync 文件夹没放进代码仓库里；
   - 安全软件拦截提示 → 加白名单后重试；
   - 其余报错原文抄出来，外网侧分析。
