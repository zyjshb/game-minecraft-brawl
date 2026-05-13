<div align="center">
  <!-- 建议将这里的 src 替换为你游戏的真实 Logo 或主视觉图链接 -->
  <img src="D:\海梅\beifen\DreamHoser.png" width="150" alt="Minecraft Brawl Logo">

  <h1>🎮 Minecraft Brawl (我的世界 - 乱斗)</h1>

  <p align="center">
    <a href="https://github.com/zyjshb/game-minecraft-brawl/releases">
      <img src="https://img.shields.io/badge/Release-v1.0.0-0078d4.svg?style=for-the-badge&logo=windows" alt="Download">
    </a>
    <a href="https://dreamhorse.itch.io/minecraft-brawl">
      <img src="https://img.shields.io/badge/Available_on-itch.io-fa5c5c.svg?style=for-the-badge&logo=itch.io" alt="itch.io">
    </a>
    <img src="https://img.shields.io/badge/License-MIT-407bff.svg?style=for-the-badge" alt="License">
    <img src="https://img.shields.io/badge/Python-Pygame-ffd343.svg?style=for-the-badge&logo=python" alt="Python">
  </p>

  <p align="center">
    <strong>「 极致方块美学 · 硬核像素乱斗 」</strong><br>
    一款基于 Python 开发的严谨体素风格（Voxel）2D 竞技动作游戏，原生支持 Windows 与 Linux。
  </p>
</div>

---

### 📌 快速导航 (TOC)
* [🚀 核心特色](#-核心特色)
* [📸 游戏演示](#-游戏演示)
* [⌨️ 操作指南](#-操作指南)
* [🛠️ 安装与运行](#-安装与运行)
* [📘 架构文档](#-架构文档)
* [🎁 下载体验](#-下载体验)

---

### 🚀 核心特色

*   **🧱 严谨体素美学:** 拒绝妥协的次世代 2D 像素表达，严格遵循 Minecraft 风格的方块物理与视觉反馈。
*   **⚔️ 流畅竞技体验:** 专为乱斗设计的底层逻辑，打击感扎实，支持高强度的本地对战。
*   **🐧 全平台兼容:** 无论是 Windows 玩家，还是 Linux 等极客开发者，都能获得一致的流畅体验。
*   **🪶 轻量级引擎:** 基于纯粹的 Pygame 架构打造，代码结构清晰，极易上手进行二次开发与 Mod 制作。

---

### 📸 游戏演示 (Screenshots)

*(💡 建议：将你在 itch.io 上的实际游戏对战截图链接替换到这里)*

<div align="center">
  <img src="C:\Users\djnio\Videos\5月12日.gif" width="45%" alt="Gameplay 1">
  <img src="C:\Users\djnio\Videos\5月12日(1).gif" width="45%" alt="Gameplay 2">
</div>

---

### ⌨️ 操作指南 (Controls)

| 动作 | 玩家 1 (Player 1) | 玩家 2 (Player 2) |
| :--- | :--- | :--- |
| **移动 (Move)** | `W` `A` `S` `D` | `↑` `↓` `←` `→` |
| **跳跃 (Jump)** | `Space` (空格) | `Numpad 0` (小键盘0) |
| **攻击 (Attack)** | `J` | `Numpad 1` |
| **技能 (Skill)** | `K` | `Numpad 2` |
| **暂停/菜单** | `Esc` | - |

*(按键配置可在游戏内的设置菜单或 `settings.json` 中自定义修改)*

---

### 🛠️ 安装与运行 (Installation)

#### 方法一：使用一键启动脚本 (推荐普通玩家)
仓库内已经提供了双端启动脚本，克隆或下载源码后，直接双击运行即可：
*   **Windows 用户:** 双击运行 `在 Windows 上启动游戏.bat`
*   **Linux 用户:** 在终端运行 `./在 Linux.sh 启动游戏` (请确保已赋予执行权限 `chmod +x`)

#### 方法二：面向开发者 (Python 环境)

```bash
# 1. 克隆游戏仓库
git clone [https://github.com/zyjshb/game-minecraft-brawl.git](https://github.com/zyjshb/game-minecraft-brawl.git)

# 2. 进入项目目录
cd game-minecraft-brawl

# 3. 安装必要的依赖库
pip install pygame

# 4. 启动游戏
python main.py