# Boss 系统完整参考文档 v2.0

> 目标：给 Gemini 阅读本文档后，指导 Codex（GPT-5.5）实现一个真正的 Boss AI。
> 当前 Boss（溺尸王/Drowned）只是一个沙包——只会走近敌人平 A + 偶尔扔三叉戟。
> v2.0 新增：史诗入场动画、水牢视觉特效、纯正 2D 动态渲染、波纹式大招、系统级底线约束。


---

## 一、项目目录结构

```
my_game/
├── entity.py                  # Entity 基类 + Buff + Particle + FloatText
├── referee.py                 # 物理碰撞检测（静态方法）
├── config.py                  # get_font() 字体工厂
├── i18n.py                    # t(key) 多语言翻译
├── audio_manager.py           # 音效管理
│
├── Ditu/                      # 关卡系统
│   ├── mine_level.py          # BattleLevel 基类（对战关卡）
│   ├── boss_level.py           # BossLevel（继承 BattleLevel，Boss 专属逻辑）
│   ├── manager.py             # LevelManager（每帧驱动所有角色 update）
│   ├── map_manager.py         # MapManager（地图方块管理）
│   └── weather/               # 天气系统子模块
│       ├── speech.py          # SpeechBubble（角色头顶气泡对话框）
│       └── ...
│
├── Jue_se/                    # 角色实现
│   ├── zombie.py / skeleton.py / creeper.py / enderman.py / illusioner.py
│   ├── drowned.py             # ★ 当前 Boss（溺尸王）—— 沙包参考实现
│   ├── mao_die/               # ★ 最复杂角色参考
│   │   ├── constants.py       #   数值常量
│   │   ├── mao_die.py         #   主角色类
│   │   ├── phase2.py          #   二阶段子系统
│   │   ├── enchant_altar.py   #   附魔祭坛机制
│   │   ├── ha_qi.py           #   哈气技能
│   │   ├── meitou.py          #   没头状态
│   │   └── vfx.py             #   视觉特效
│   └── _sfx.py                # 音效播放工具
│
├── Boss/                      # Boss 资源
│   └── drowned_king/
│       ├── drowned_king.png
│       ├── trident.png
│       ├── vfx_ult/
│       ├── vfx_idle/
│       ├── vfx_fly/
│       ├── vfx_water_prison/  # ★ v2.0 水牢特效帧
│       └── sfx/
│
├── Sprites/                   # 通用精灵素材
├── SFX/                       # 通用音效素材
└── Scenes/                    # UI 场景
    ├── difficulty_select.py   # 难度选择（简单/困难/极限）
    └── boss_buff_select.py    # Boss Buff 选择（战前 3 轮）
```


## 二、Entity 基类 API（entity.py）

所有角色（包括 Boss）都继承 `Entity`。Boss 实现者必须了解以下可用接口：

```python
class Entity:
    # === 构造时必须设置 ===
    self.size          # int  碰撞体积（正方形边长 px）
    self.rect          # pygame.Rect  碰撞矩形（构造时自动生成）
    self.hp            # int  当前血量
    self.max_hp        # int  最大血量
    self.vx, self.vy   # float  当前速度向量

    # === Boss 需要自己定义 ===
    self.speed         # float  移动速度基数
    self.damage        # int    基础伤害
    self.attack_range  # int    攻击距离（px）
    self.attack_cd     # int    攻击冷却（帧）
    self.dmg_res       # float  减伤比例（0.0~1.0）
    self.kb_res        # float  击退抗性（0.0~1.0）

    # === Buff 系统 ===
    self.buffs         # list[Buff]  当前生效的增益/减益
    self.add_buff(name, value, duration=0, buff_type="buff")
    self.remove_buff(name)
    self.has_buff(name)
    self.get_buff_value(name)  # 返回 int 或 0
    self.update_buffs()        # 每帧调用，清理过期 Buff

    # === 浮动文字（伤害数字/特效文字） ===
    self.float_texts   # list[FloatText]
    # 用法: self.float_texts.append(FloatText(x, y, "-25", (255, 0, 0)))

    # === 物理 ===
    self.apply_physics(bw, bh)  # 边界弹墙，调用后自动限制速度
    self.take_damage(amount, attacker=None)  # 标准受伤（不处理减伤）
    self.trigger_damage_flash()
    self.draw_float_texts(surface)

    # === 气泡对话 ===
    self._pending_speech  # 设置为字符串，下一帧自动显示气泡
```

关键提示：`Entity.take_damage()` 不处理减伤！Boss 必须自己 override 它来计算 `actual = amount * (1.0 - dmg_res)`。


## 三、BossLevel 调用协议（boss_level.py）

BossLevel 每一帧对 Boss 的调用方式（这是必须遵守的接口契约）：

```python
# boss_level.py 第 ~117 行起
for f in mgr.fighters:
    clsname = f.__class__.__name__

    if clsname == self._boss_char:
        tridents_out = []                              # Boss 专属额外参数
        result = f.update(                             # Boss 的 update 签名
            mgr.fighters, self.width, self.height,     #    enemies, bw, bh
            tridents_out,                              #    第4参数：投射物输出列表
            weather=mgr.weather                        #    v2.0：第5参数天气
        )
        for t in tridents_out:                         # 框架负责将投射物注入
            t.shooter = f
            mgr.arrows.append(t)
        if result:                                     # 框架负责处理近战结果
            target = result.get("target")
            dmg = result.get("damage", 25)
            if target and target in mgr.fighters and target.hp > 0:
                target.take_damage(dmg, attacker=f)
```

### Boss.update() 签名约定

```python
def update(self, enemies, bw, bh, tridents_out=None, weather=None):
    """
    enemies:      list[Entity]  所有存活角色（包括自己）
    bw, bh:       int           战场宽高
    tridents_out: list           框架注入的空列表，Boss 往里 append 投射物
    weather:      WeatherSystem or None  天气系统实例（v2.0 新增）

    返回:  dict or None
        {"target": Entity, "damage": int}   → 近战命中
        None 或 不返回                         → 无事件
    """
```

### v2.0 新增：BossLevel.INTRO 状态

Boss 正式开始前，BossLevel 必须增加 INTRO 阶段（见 7.0.1 节），此时：

- `self.intro_phase = True`，不调用任何角色的 update
- BossLevel 直接控制 Intro 动画播放
- Boss 的 `self._intro_locked = True`，禁止自身 update
- INTRO 结束后设置 `self.intro_phase = False`，`boss._intro_locked = False`


## 四、普通模式（manager.py）的 update 协议对比

在非 Boss 关卡，所有角色走 `manager.py` 的通用 update：

```python
# manager.py 第 ~220 行
for f in self.fighters:
    res = f.update(self.fighters, self.width, self.height)
    # res 支持的 key:
    #   "projectile": 单个投射物 → 追加到 self.arrows
    #   "spawns":     list 子实体 → 追加到 self.fighters
    #   "push":       (px, py) 推飞某个角色
    #   "target" + "damage":           → 单段伤害
    #   "target" + "damage" + "second_damage" → 二段伤害
```

## 五、当前 Boss：溺尸王（drowned.py）完整分析

### 5.1 行为树（简单到不像话）

```
每帧 update():
  if 死亡: return None
  更新 Buff / 粒子 / 物理

  找到最近的存活敌人 → 缓慢靠近

  CD 递减 → 范围内平A → 随机扔三叉戟

  return None
```

### 5.2 为什么它是"沙包"

1. 零智能选目标 — 永远打最近的
2. 零走位 — 直线靠近不后退
3. 零技能连招 — 随机三叉戟 + 平A
4. 零状态机 — 没有蓄力→释放→后摇
5. 零战场交互 — 不利用地图、不躲避弹幕
6. 二阶段只是数值放大 — 没有新技能

### 5.3 数值面板（旧版，仅供参考对比）

| 属性 | 一阶段 | 二阶段 (HP≤50%) |
|------|:---:|:---:|
| 最大 HP | 800 × hp_mult | — |
| 近战伤害 | 25 × dmg_mult | 35 × dmg_mult |
| 三叉戟伤害 | 35（固定） | 35（固定） |
| 攻击范围 | 100 | 120 |
| 移动速度 | 1.6 × spd_mult | 2.0 × spd_mult |
| 减伤 | 10% | 18% |
| 击退抗性 | 60% | 60% |

难度倍率：简单(0.7/0.8/0.7) 困难(1.0/1.0/1.0) 极限(1.5/1.4/1.3)


## 六、BossLevel 的挑战者强化机制

所有非 Boss 角色获得以下强化（`boss_level.py` 第 ~46 行）：

| 角色 | 伤害 | HP | 特殊 |
|------|------|----|------|
| 通用 | ×(1.6+1.2×hp_m) | ×(1.15+0.7×hp_m) | — |
| Zombie | +通用 | +通用 | CD×0.75, 范围×1.15, 速度×1.25 |
| Skeleton | +通用 | +通用 | 射击间隔×0.6, 减伤=30% |
| Creeper | +通用 | +通用 | 瞬爆 |
| Enderman | +通用 | +通用 | 连击无CD, 伤害×1.15 |
| MaoDie | +通用 | +通用 | 自动找祭坛, P2伤害×(1.3+0.4×hp_m) |

Boss Buff 系统（可选战前 3 轮选牌）：atk_up, spd_up, crit_up, lifesteal, dmg_res, thorn, dmg_amp, regen, fury, barrier


---

---

# 七、溺尸王（DrownedKing）v2.0 完整技能设计规格书

> ⚠️ 以下为给 Codex 的最高执行标准。必须逐帧、逐像素强制执行。不可自行简化。

---

### 7.0 命名与文件约定

| 项目 | 值 |
|------|-----|
| 类名 | `DrownedKing` |
| 文件名 | `Jue_se/drowned_king.py` |
| 地图绑定 | `BOSS_NAME_BY_MAP = {"boss对战_平原要塞.png": "DrownedKing"}` |
| 资源目录 | `Boss/drowned_king/` |
| 继承 | `Entity`（entity.py） |
| 使用语言 | 所有文本必须通过 `i18n.t("key")` 获取，严禁硬编码字符串 |

已有资源：
- `Boss/drowned_king/drowned_king.png` — Boss 精灵（120×120 原始分辨率）
- `Boss/drowned_king/trident.png` — 三叉戟精灵（基础贴图，用于 Dropped 态）
- `Boss/drowned_king/vfx_ult/` — 4×4 雷电序列帧（1.png~16.png）
- `Boss/drowned_king/vfx_idle/` — 钉墙态帧动画（trident_fixed_0_0.png ~ trident_fixed_3_3.png）
- `Boss/drowned_king/vfx_fly/` — 飞行态帧动画（trident_fixed_0_0.png ~ trident_fixed_3_3.png）
- `Boss/drowned_king/vfx_water_prison/` — ★ v2.0 水牢特效帧动画
- `Boss/drowned_king/sfx/` — 全部音效


### 7.0.1 ★ v2.0 史诗级入场动画（Cinematic Intro）

> 在 `boss_level.py` 中实现，不放在 DrownedKing 类内部。

#### 状态定义

新增 `BossLevel._intro_state` 字段，取值：

```
"cinematic_start" → "trident_1" → "trident_2" → "trident_3" → "trident_4" → "boss_fall" → "trident_fusion" → "done"
```

#### 逐帧流程（总时长：约 180 帧 = 3 秒）

| 阶段 | 持续 | 行为 |
|------|:---:|------|
| **cinematic_start** | 30 帧 | 全员冻结（不调用任何 update），画面逐渐变暗（黑色 overlay alpha 0→160）；镜头缓慢 zoom in 1.0→1.15 |
| **trident_1** | 15 帧 | 第 1 把带电三叉戟（`vfx_ult/` 帧动画）从屏幕外 Y=-200 极速砸入 (bw×0.2, bh×0.3)，触发 `screen_shake(amplitude=12, duration=20)`，播放 `trident_explode.mp3`。三叉戟 Pinned 在落点 |
| **trident_2** | 15 帧 | 第 2 把砸入 (bw×0.8, bh×0.25)，触发 `screen_shake(amplitude=14, duration=22)`，播放 `trident_explode.mp3` |
| **trident_3** | 15 帧 | 第 3 把砸入 (bw×0.15, bh×0.7)，触发 `screen_shake(amplitude=16, duration=24)`，播放 `trident_explode.mp3` |
| **trident_4** | 15 帧 | 第 4 把砸入 (bw×0.85, bh×0.75)，触发 `screen_shake(amplitude=18, duration=26)`，播放 `trident_explode.mp3` |
| **boss_fall** | 30 帧 | 溺尸王从 Y=-300 极速坠落至 (bw//2, bh//2)；屏幕剧烈震动 `screen_shake(amplitude=30, duration=40)`；播放 `Riptide_III.ogg.mp3`；全屏白闪 3 帧 |
| **trident_fusion** | 40 帧 | 4 把钉墙三叉戟依次化为雷电粒子（`vfx_ult/`），沿贝塞尔曲线汇聚到 Boss 手中；Boss 双手合十，生成一把巨型带电三叉戟（scale=2.5× 叠加在 Boss 精灵上），全屏闪电闪烁 |
| **done** | — | 移除巨型三叉戟特效，恢复摄像机，画面恢复正常；`intro_phase = False`，战斗正式开始 |

#### screen_shake 实现标准

```python
def apply_screen_shake(amplitude, duration):
    # 在 boss_level 中维护：
    # self._shake_amplitude = amplitude（每帧衰减）
    # self._shake_duration = duration
    # 每帧 offset_x += random.randint(-amp, amp)
    #        offset_y += random.randint(-amp, amp)
    # shake 衰减公式: amplitude *= 0.85 每帧
```

#### INTRO 阶段的安全锁

- 所有角色的 `update()` 不被调用
- 天气系统暂停（`weather.paused = True`）
- INTRO 结束后 `weather.paused = False` 恢复


### 7.0.2 ★ v2.0 水牢机制（Water Prison）

> 将原本"穿透减速 Buff"升级为完整视觉机制。

#### 触发条件

Trident（Flying 状态）每穿透命中一个敌人时：

1. 对该敌人附加减速 Buff：`speed *= 0.6`，持续 **90 帧**（不受 CD 倍率影响）
2. 同时在该敌人身上叠加 **水牢 Visual**

#### 水牢 Visual 实现

```python
class WaterPrisonVFX:
    def __init__(self, target_entity):
        self.target = target_entity       # 被水牢困住的 Entity 引用
        self.life = 90                    # 与水牢 Buff 同步
        self.frames = []                  # 加载 vfx_water_prison/ 帧动画
        self.frame_index = 0
        self.bubble_particles = []        # 气泡粒子（冒泡上升）

    def update(self):
        self.life -= 1
        self.frame_index = (self.frame_index + 0.15) % len(self.frames)
        # 每 5 帧生成一个气泡粒子向上飘
        if self.life % 5 == 0:
            self.bubble_particles.append(...)

    def draw(self, surface):
        # 以 target 的 rect 为中心，绘制比 target 大 1.3 倍的水泡层
        frame = self.frames[int(self.frame_index)]
        frame = pygame.transform.scale(frame, (int(target.size * 1.3), int(target.size * 1.3)))
        surface.blit(frame, target.rect.topleft 偏移居中)
        for bp in self.bubble_particles:
            bp.draw(surface)
```

#### 渲染时机

水牢 VFX 必须在 `boss_level.py` 的 `draw()` 中，于 **角色精灵之上、天气层之下** 绘制，确保视觉上覆盖在角色表面。

#### 生命周期

- 水牢 VFX 的 `life` 与减速 Buff 的 `duration` 绑定为 **90 帧**
- 当减速 Buff 过期时，水牢 VFX 立即销毁（带一个 5 帧的爆裂粒子消散效果）
- 如果敌人在水牢期间死亡，水牢 VFX 也随之销毁


### 7.0.3 ★ v2.0 系统级底线约束（防 Bug 铁律）

> 以下规则优先级高于一切技能设计。任何违反都将导致 Codex 输出被拒绝。

#### 约束 1：资源加载防蓝块

所有图片加载必须遵循以下模式，严禁出现蓝色/白色占位方块：

```python
def _safe_load_image(path, fallback_color=None, scale=None):
    try:
        if not os.path.exists(path):
            raise FileNotFoundError(f"missing: {path}")
        img = pygame.image.load(path).convert_alpha()
        if scale:
            img = pygame.transform.scale(img, scale)
        return img
    except Exception as e:
        print(f"[DrownedKing] load failed: {path} -> {e}")
        if fallback_color:
            surf = pygame.Surface(scale or (64, 64), pygame.SRCALPHA)
            surf.fill(fallback_color)
            return surf
        return None
```

**强制规则**：
- 每个 `pygame.image.load` 调用必须放在 try/except 中
- 路径必须用 `os.path.join(base, sub, filename)` 拼接，严禁用字符串 `"/"` 拼接
- `base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Boss", "drowned_king")`
- 若加载失败：打印明确的路径日志，返回 `None`（draw 方法中检查 None 直接 return）

#### 约束 2：i18n 硬性规定

- **严禁**在 `drowned_king.py` 的任何位置出现 `""` 包裹的中文/英文硬编码台词字符串
- **必须**使用 `from i18n import t`，台词写为 `t("dk_skill_throw")` 等 key
- **台词冷却**：`self._speech_cooldown` 最小值为 **300 帧**（约 5 秒），同一场战斗同一句台词不可重复使用

```python
# 正确
self._pending_speech = t("dk_skill_throw")     # i18n key

# 错误（绝对禁止）
self._pending_speech = "深海之怒！"             # 硬编码中文
```

#### 约束 3：CD 全面延长 2.5 倍

v1.0 的所有技能 CD 值 × 2.5（向上取整），防止技能狂丢：

| 技能 | v1.0 CD | v2.0 CD |
|------|:---:|:---:|
| 近战连击频率 | 120 / 80 | 300 / 200 |
| 投掷 CD | 90 / 50 | 225 / 125 |
| 雷霆充能 CD | 300 / 180 | 750 / 450 |
| 大招 CD | 600 / 360 | 1500 / 900 |
| 武器唤回检测间隔 | 每帧 | 每 30 帧 |
| 台词冷却 | 未设 | 300 帧 |

#### 约束 4：边界检测精度

Trident 的边界判定必须像素级精确：

```python
# Trident.update() 中
# 屏幕边界用 <= 和 >= 确保永远不穿透边界
if self.x <= 0 or self.x >= bw or self.y <= 0 or self.y >= bh:
    self.x = max(0, min(bw, self.x))
    self.y = max(0, min(bh, self.y))
    self.state = "pinned"
    return []
```

- `self.rect` 每帧同步更新: `self.rect.center = (int(self.x), int(self.y))`
- 障碍物碰撞使用 `self.rect.colliderect(block.rect)`，不用坐标近似

---

### 7.1 Trident 投掷物类

#### 7.1.1 状态机

```
飞行中(Flying) ──撞墙/撞障碍──→ 钉墙(Pinned) ──被雷霆充能──→ 通电(Electrified)
    │                                  │
    └──动能耗尽(未撞墙)──→ 掉落(Dropped)  （不可被充能）
```

#### 7.1.2 各状态行为

| 状态 | 碰撞 | 渲染 | 伤害行为 |
|------|------|------|---------|
| **Flying** | 每帧检测地图方块/屏幕边界精确碰撞；穿透所有敌人 | ★ v2.0 动态旋转渲染（见 7.1.6） | 穿透敌人造成伤害 + 附加水牢减速 |
| **Pinned** | 静止，不参与战斗碰撞 | `vfx_idle/` 帧动画 | 无直接伤害，可被大招引爆 + 可被 Thunder Charge 充能 |
| **Dropped** | 躺地，静止 | `trident.png` 原图旋转 90° 平躺 | 无伤害，不可充能，可被大招引爆 |
| **Electrified** | 静止（Pinned 位置），周期性闪烁 | `vfx_ult/` 帧动画 | 每 30 帧对周围 80px 敌人造成 8 点雷伤 + 播放 `lightning_strike.mp3.mp3` |

#### 7.1.3 Trident 类必需属性与方法

```python
class Trident:
    def __init__(self, x, y, vx, vy, damage, shooter):
        self.state = "flying"
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.damage = damage
        self.shooter = shooter
        self.life = 120
        self.size = 14
        self.rect = pygame.Rect(int(x)-7, int(y)-7, 14, 14)
        self.hit_enemies = set()
        self.slow_duration = 90
        self.slow_amount = 0.4
        self.electrified_timer = 0

        # ★ v2.0 动态渲染
        self.angle = math.atan2(-vy, vx)       # 弧度（取反使尖端朝运动方向）
        self.trail_positions = []              # [(x, y, alpha), ...] 残影
        self.trail_max = 8                     # 残影数量

        # ★ v2.0 水牢
        self.water_prisons = [] # WaterPrisonVFX 列表（穿透命中时追加）

        self._load_assets()

    def update(self, bw, bh, blocks):
        ...

    def draw(self, surface): ...
    def is_dead(self): ...
    def electrify(self): ...
```

#### 7.1.4 物理碰撞判定逻辑

```
每帧 update(bw, bh, blocks):

  if state != "flying": return []

  # ★ v2.0 残影记录
  self.trail_positions.append((self.x, self.y, 255))
  if len(self.trail_positions) > self.trail_max:
      self.trail_positions.pop(0)
  # 残影逐帧衰减
  for i in range(len(self.trail_positions)):
      self.trail_positions[i] = (..., alpha - 32)

  移动: x += vx, y += vy
  life -= 1
  self.rect.center = (int(x), int(y))  # ★ 每帧同步

  # ★ 像素级边界检测
  if self.x <= 0 or self.x >= bw or self.y <= 0 or self.y >= bh:
      self.x = max(0.0, min(float(bw), self.x))
      self.y = max(0.0, min(float(bh), self.y))
      self.state = "pinned"
      播放 trident_explode.mp3
      return []

  # 障碍物碰撞
  for block in blocks:
      if block.active and self.rect.colliderect(block.rect):
          self.state = "pinned"
          播放 trident_explode.mp3
          return []

  # 动能耗尽
  if life <= 0:
      self.state = "dropped"
      随机播放 trident_drop_1/2/3.mp3
      return []

  return []
```

#### 7.1.5 音效映射

| 事件 | 音效文件 |
|------|---------|
| 投掷时 | `trident_throw.mp3` |
| 飞行穿透命中敌人 | `trident_pierce_1/2/3.mp3`（随机三选一） |
| 钉墙 | `trident_explode.mp3` |
| 掉落 | `trident_drop_1/2/3.mp3`（随机三选一） |
| 电击脉冲伤害 | `lightning_strike.mp3.mp3` |
| 大招启动 | `Riptide_III.ogg.mp3` |

#### 7.1.6 ★ v2.0 动态投掷视觉（核心渲染要求）

> 这是 Codex 必须逐行实现的最高优先级视觉规范。

```
Trident.draw(surface):

  if state == "flying":
      1. 计算角度: angle = math.degrees(math.atan2(-vy, vx))
         （atan2 取 y 分量负值，使三叉戟尖端朝向飞行方向）

      2. 绘制残影（先画残影，再画本体）:
         for i, (tx, ty, alpha) in enumerate(self.trail_positions):
             trail_img = vfx_fly 当前帧.copy()
             ratio = alpha / 255.0
             trail_img.set_alpha(int(alpha))
             rotated = pygame.transform.rotate(trail_img, angle)
             surface.blit(rotated, ...)
         （残影从旧到新绘制，旧的 alpha 更低更透明）

      3. 绘制本体（旋转后的 vfx_fly 帧动画）:
         current_frame = self.fly_frames[self.fly_frame_index]
         rotated = pygame.transform.rotate(current_frame, angle)
         r = rotated.get_rect(center=(int(self.x), int(self.y)))
         surface.blit(rotated, r)

      4. 帧动画更新:
         self.fly_frame_index = (self.fly_frame_index + 0.2) % len(self.fly_frames)

  if state == "pinned":
      # vfx_idle 帧动画，不旋转，钉在墙上
      ...

  if state == "dropped":
      # trident.png 旋转 90° 平躺在地
      ...

  if state == "electrified":
      # vfx_ult 帧动画，不旋转，周期性闪烁（每 15 帧 toggle alpha 255↔128）
      ...
```

**禁止事项**：
- 严禁使用静态贴图！必须 `pygame.transform.rotate` 实时旋转
- 严禁省略残影！残影是区分"沙包项目"和"商业项目"的核心标志
- 残影数量固定为 8，alpha 从 255 线性递减到 0

---

### 7.2 Boss 状态机（FSM）

```
                    ┌──────────────────────────────────┐
                    │         WEAPON_RECALL            │ ← 被动：场上 Pinned+Dropped ≥ 20
                    │   （打断当前动作，0.5s后回收）      │
                    └──────────────────────────────────┘
                                    ↑ 任意状态可被中断
                                    
IDLE ──→ CHASE ──→ MELEE_COMBO ──→ THROW ──→ THUNDER_CHARGE ──→ ULTIMATE ──→ COOLDOWN
  ↑        ↑           ↑               ↑              ↑                ↑            │
  │        │           │               │              │                │            │
  └────────┴───────────┴───────────────┴──────────────┴────────────────┴────────────┘
```

#### 7.2.1 v2.0 状态详情（CD 已 ×2.5）

| 状态 | 持续 | 进入条件 | 行为 |
|------|:---:|------|------|
| **IDLE** | 75~150 帧 | 开局 / 冷却结束 | 原地待机，呼吸动画（scale 1.0↔1.02 正弦波） |
| **CHASE** | 持续 | 有目标且距离 > 攻击范围 | 向目标移动，速度 2.0；每 30 帧检测状态切换 |
| **MELEE_COMBO** | ~60 帧 | 目标在 120px 内 且 CD=0 | 随机三连击（见 7.3）+ v2.0 VFX |
| **THROW** | ~65 帧 | 目标 150~400px 且 CD=0 | 深渊贯穿（见 7.4） |
| **THUNDER_CHARGE** | ~80 帧 | Pinned≥3 且 CD=0 | 雷霆充能（见 7.6） |
| **ULTIMATE** | ~170 帧 | Pinned+Dropped≥8 且 CD=0 | 波纹式三叉戟狂欢（见 7.7） |
| **WEAPON_RECALL** | ~45 帧 | Pinned+Dropped≥20（被动最高优先） | 武器唤回（见 7.5） |
| **COOLDOWN** | 100~200 帧 | 技能释放完毕 | 后撤 60px，后摇僵直，返回 IDLE |

#### 7.2.2 v2.0 二阶段（HP ≤ 50%）行为变化（CD 已 ×2.5）

| 变化项 | 一阶段 | 二阶段 |
|--------|--------|--------|
| 近战连击频率 | 每 300 帧 | 每 200 帧 |
| 投掷 CD | 225 帧 | 125 帧 |
| 雷霆充能 CD | 750 帧 | 450 帧 |
| 大招 CD | 1500 帧 | 900 帧 |
| 武器唤回触发阈值 | ≥20 把 | ≥15 把 |
| 三叉戟飞行速度 | 7 px/帧 | 10 px/帧 |
| 移动速度 | 2.0 | 2.5 |
| 减伤 | 10% | 20% |
| 新特性 | — | 雷霆充能后可立即接大招（combo，跳过 COOLDOWN） |

---

### 7.3 ★ v2.0 近战三连击（含完整视觉规格）

在 MELEE_COMBO 状态下，从以下 3 种攻击中随机选择一种执行：

| 攻击 | 伤害 | 范围 | 位移 | v2.0 VFX 规格 |
|------|:---:|:---:|------|------|
| **短突刺** | 28 | 前方 100×60 矩形 | 自身向前 60px | ★ 武器贴图瞬间 scale 1.0→1.2（5 帧内回到 1.0）；身后生成 6 个 DustParticle |
| **小横斩** | 22 | 半径 100 扇形（120°） | 无 | ★ 绘制 120° 扇形电光剑气：`pygame.draw.arc` 粗线宽 6px + 外层光晕宽 12px alpha=80；滞留 5 帧后消散 |
| **大横斩** | 35 + 击退 8px | 半径 140 扇形（180°） | 无 | ★ Boss 原地以 `self.rect.center` 为轴 360° 极速旋转（rot_speed=24°/帧，持续 10 帧）；在旋转结束时生成半径 150px 全圆剑气（`pygame.draw.circle` 线宽 8px 亮蓝白光 + 外圈线宽 16px alpha=60）；滞留 8 帧后消散 |

#### 扇形剑气绘制伪代码（小横斩用）

```python
def draw_slash_arc(surface, cx, cy, radius, start_angle, end_angle, color):
    # 外层光晕
    for t in range(3):
        glow_alpha = 80 - t * 25
        pygame.draw.arc(surface, (*color, glow_alpha),
                        (cx-radius-t*3, cy-radius-t*3, (radius+t*3)*2, (radius+t*3)*2),
                        start_angle, end_angle, width=12-t*3)
    # 主体
    pygame.draw.arc(surface, color,
                    (cx-radius, cy-radius, radius*2, radius*2),
                    start_angle, end_angle, width=6)
```

#### 360 度圆形剑气绘制（大横斩用）

```python
def draw_full_circle_slash(surface, cx, cy, radius, color, alpha):
    glow = pygame.Surface((radius*2+40, radius*2+40), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*color, alpha//2), (radius+20, radius+20), radius, width=16)
    pygame.draw.circle(glow, (*color, alpha), (radius+20, radius+20), radius, width=8)
    surface.blit(glow, (cx-radius-20, cy-radius-20))
```

#### 返回格式

```python
result = {
    "target": target,
    "damage": damage,
    "melee_type": "thrust"|"slash_small"|"slash_big",
    "knockback": (px, py),  # 仅大横斩
}
```

---

### 7.4 技能1：深渊贯穿（Abyss Pierce）

**进入条件**：THROW 状态，目标在 150~400px 距离。

**行为**：
1. 前摇 15 帧：Boss 举叉蓄力，手部生成蓝色粒子环（Particle ×12 环绕蓄力）
2. 释放：生成 `Trident` 实例，瞄准目标当前位置
3. 后摇 10 帧

**Trident 参数**：
- damage = 35
- life = 120 帧
- speed = 7 px/帧（二阶段 10）

**台词**（随机，必须 i18n）：
- `t("dk_skill_throw_1")`
- `t("dk_skill_throw_2")`

---

### 7.5 技能2：武器唤回（Weapon Recall）—— 被动触发

**触发条件**：场上 Pinned+Dropped ≥ 20（二阶段 ≥15），每 30 帧检测一次。

**行为**：
1. **强制打断**当前所有动作（FSM → WEAPON_RECALL，不可被任何其他状态中断）
2. 前摇 15 帧：Boss 张开双臂，播放 `Riptide_III.ogg.mp3`
3. 场上所有 Trident（全部状态）化为蓝色粒子飞向 Boss，每把回收回复 **15 HP**
4. 后摇 15 帧 → IDLE

**台词**：`t("dk_recall")`

**实现方式**：Boss 设置 `self._recall_flag = True`，由 `boss_level.py` 检测并执行全局回收。

---

### 7.6 技能3：雷霆充能（Thunder Charge）

**进入条件**：THUNDER_CHARGE 状态，场上 Pinned ≥ 3，CD=750/450。

**行为**：
1. 前摇 20 帧：Boss 高举三叉戟，天空闪白（叠加半透明白色 overlay）
2. 释放：所有 Pinned 三叉戟切换为 Electrified
3. 充能持续 **300 帧**，之后自动回 Pinned
4. 电击脉冲：每 30 帧对 80px 内敌人造成 8 点雷伤
5. 后摇 10 帧

**天气联动**：雨天/雷暴 → 充能范围 +30px，伤害 +3。

**台词**：`t("dk_thunder")`

---

### 7.7 ★ v2.0 终极大招（Ripple Detonation）

**进入条件**：ULTIMATE 状态，场上 Pinned+Dropped+Electrified ≥ 8，CD=1500/900。

#### 波纹式引爆流程（约 170 帧）

| 阶段 | 持续 | 行为 |
|------|:---:|------|
| **pre_ult** | 30 帧 | 全屏播放 `vfx_ult/` 雷电序列帧（4×4，全屏铺满）；所有角色静止；画面色调偏蓝（叠加蓝色 overlay alpha=60） |
| **ripple_sort** | 5 帧 | 收集场上所有 Trident，按与 Boss 的欧氏距离升序排序 |
| **ripple_detonate** | ~60 帧 | 从最近的 Trident 开始，每隔 8 帧引爆一个：① 该 Trident 位置生成冲天光柱特效（见下方）→ ② 以该 Trident 为中心 120px 半径雷爆伤害 → ③ 下一把继续，间隔 8 帧，形成由内向外扩散的波纹 |
| **light_pillar** | 每把 20 帧 | 光柱：宽 12px、高从 0 生长到 200px 的金色/白色竖线 + 顶部闪烁圆点 + 粒子碎屑向四周飞散 |
| **post_ult** | 20 帧 | 清空所有 Trident；Boss 后摇；画面恢复正常 |

#### 光柱绘制伪代码

```python
def draw_light_pillar(surface, x, y, progress):
    # progress: 0.0 → 1.0
    height = int(200 * progress)
    alpha = int(200 * (1.0 - progress * 0.6))

    pillar = pygame.Surface((20, height), pygame.SRCALPHA)
    # 中心亮线
    pygame.draw.line(pillar, (255, 255, 200, alpha), (10, 0), (10, height), 4)
    # 外层光晕
    pygame.draw.line(pillar, (255, 220, 100, alpha//2), (13, 0), (13, height), 8)
    pygame.draw.line(pillar, (255, 255, 255, alpha//3), (7, 0), (7, height), 12)

    rect = pillar.get_rect(midbottom=(int(x), int(y)))
    surface.blit(pillar, rect)

    # 顶部闪光圆点
    top_y = rect.top
    pygame.draw.circle(surface, (255, 255, 255, alpha),
                       (int(x), int(top_y)), int(6 + 3 * (1-progress)))
```

#### 伤害结算

- 每把 Trident 的雷爆半径：120px（雨天/雷暴 → 160px）
- 每把基础伤害：18
- 总伤害 = `18 × trident_count × (0.8 + 雨天加成 0.3)`
- 同一敌人被多个雷爆命中则伤害叠加

**台词**：`t("dk_ult")`

**波纹完成后**：清空场上所有 Trident。

---

### 7.8 环境联动接口（Environment Sync）

```python
def update(self, enemies, bw, bh, tridents_out=None, weather=None):
    is_storm = False
    if weather and weather.enabled:
        from Ditu.weather.constants import WeatherType
        if weather.current_weather in (
            WeatherType.THUNDERSTORM, WeatherType.LIGHT_RAIN,
            WeatherType.MODERATE_RAIN, WeatherType.HEAVY_RAIN
        ):
            is_storm = True

    if is_storm:
        self.speed_bonus = 0.3
        self.thunder_range_bonus = 30
        self.thunder_dmg_bonus = 3
    else:
        self.speed_bonus = 0
        self.thunder_range_bonus = 0
        self.thunder_dmg_bonus = 0
```

---

### 7.9 目标选择策略（v2.0 增强）

```python
def _select_target(self, enemies):
    """
    优先级（从高到低）：
    1. 仇恨目标（上一帧谁打了我，或谁打我最疼）
    2. 水牢中的敌人（已被减速，优先追击扩大优势）
    3. 血量 < 25% 的敌人（斩杀优先）
    4. 远程角色（Skeleton > Illusioner > 其他）
    5. 最近的敌人
    """
```

---

### 7.10 走位策略（v2.0 增强）

- **CHASE**：直线靠近 + ±15° 随机偏移 + 每 60 帧重新随机偏角
- **后撤**：每次近战连击完成后，后退 40~60px
- **横移**：THROW 投掷后横向走 2 步
- **弹幕检测**：每 20 帧扫描箭矢，若 3+ 在 200px 内，横移加速至 1.5× speed
- ★ **v2.0 水牢追击**：若有敌人处于水牢中，优先向其移动（速度 ×1.1），扩大水牢威胁


### 7.11 前摇/后摇与可读性汇总（v2.0）

| 技能 | 前摇 | 可打断？ | 后摇 | v2.0 VFX |
|------|:---:|:---:|:---:|------|
| 短突刺 | 8 帧蓄力粒子 | 否 | 20 帧 | 武器 scale 1.0→1.2 |
| 小横斩 | 6 帧闪烁 | 否 | 16 帧 | 120° 扇形电光滞留5帧 |
| 大横斩 | 15 帧举叉 | 否 | 30 帧 | Boss 360° 自转+圆形剑气滞留8帧 |
| 深渊贯穿 | 15 帧蓝色蓄力环 | 是 | 10 帧 | 12 粒子环环绕蓄力 |
| 武器唤回 | 15 帧双臂展开 | **否** | 15 帧 | 所有 Trident 化为蓝粒子飞回 |
| 雷霆充能 | 20 帧天空闪白 | 是 | 10 帧 | 全屏白色 overlay |
| 波纹引爆 | 30 帧雷电序列帧 | 否 | 20 帧 | 波纹排序引爆+光柱 |


## 八、实现步骤模板（v2.0 更新）

### Step 1：文件创建

| 文件 | 内容 |
|------|------|
| `Jue_se/drowned_king.py` | `DrownedKing` 类 + `Trident` 类 + `WaterPrisonVFX` 类 |
| 修改 `Ditu/boss_level.py` | ★ 新增 INTRO 动画系统 + 全局 Trident 管理 + 水牢列表 + 光柱列表 + screen_shake |
| 修改 `Ditu/manager.py` | 注册 `DrownedKing` |

### Step 2：资源就绪

```
Boss/drowned_king/（已有）：
├── drowned_king.png
├── trident.png
├── vfx_ult/         (1.png~16.png, 4×4 序列帧)
├── vfx_idle/        (trident_fixed_0_0.png ~ 3_3.png)
├── vfx_fly/         (trident_fixed_0_0.png ~ 3_3.png)
├── vfx_water_prison/ (★ v2.0 水牢帧动画)
└── sfx/
    ├── Riptide_III.ogg.mp3
    ├── trident_throw.mp3
    ├── trident_drop_1/2/3.mp3
    ├── trident_explode.mp3
    ├── trident_pierce_1/2/3.mp3
    ├── lightning_strike.mp3.mp3
    ├── drowned_stab.mp3
    └── drowned_slash.mp3
```

### Step 3：boss_level.py 修改清单

```
BossLevel.__init__():
  + self.intro_phase = True               # 立即进入 INTRO
  + self._intro_state = "cinematic_start"
  + self._intro_timer = 0
  + self._intro_tridents = [None]*4       # 4 把 INTRO 三叉戟
  + self._shake_amplitude = 0
  + self._shake_duration = 0
  + self.trident_list = []                # 全局 Trident 管理
  + self.water_prisons = []               # 水牢 VFX 列表
  + self.light_pillars = []               # 光柱 VFX 列表
  + self._screen_offset_x = 0             # screen_shake offset
  + self._screen_offset_y = 0

BossLevel.update():
  + if self.intro_phase: self._update_intro(); return

BossLevel._update_intro():
  # 按 7.0.1 流程逐帧推进
  # 每个阶段计时 → 触发 screen_shake → 切换下一阶段
  # 最后 intro_phase = False

BossLevel.draw():
  # 应用 screen_shake offset 到 game_surf 的 blit 位置
  # INTRO 阶段画特殊覆盖层
```

### Step 4：i18n Key 清单

需要新增的 i18n key（中文供参考，实际翻译由 i18n.py 管理）：

```
dk_intro_title
dk_skill_throw_1, dk_skill_throw_2
dk_recall
dk_thunder
dk_ult
dk_p2_trigger
dk_melee_stab, dk_melee_slash_small, dk_melee_slash_big
```


## 九、框架提供的"免费功能"（Boss 不需要自己写的）

| 功能 | 来源 |
|------|------|
| 物理碰撞（弹墙） | `self.apply_physics(bw, bh)` |
| 角色间碰撞 | `referee.py` `Referee.process_collision()` |
| Buff 系统 | `self.buffs` + `update_buffs()` |
| 浮动伤害数字 | `self.float_texts.append(FloatText(...))` |
| 气泡对话 | `self._pending_speech = t("key")` |
| 天气效果 | `weather/` 子系统 |
| 血条渲染 | `boss_level.py` `_draw_boss_hp_bar()` |
| 多语言 | `from i18n import t` |


## 十、推荐参考的角色复杂度阶梯

1. **Zombie** (`Jue_se/zombie.py`) — 最简
2. **Skeleton** (`Jue_se/skeleton.py`) — 远程射击
3. **Enderman** (`Jue_se/enderman.py`) — 瞬移、连击
4. **Illusioner** (`Jue_se/illusioner.py`) — 分身术、弹幕
5. **MaoDie** (`Jue_se/mao_die/`) — 最复杂多文件


## 十一、给 Gemini 的最终 Prompt（v2.0 直接复制使用）

---

请根据以上完整文档 v2.0（第七章是核心），告诉 Codex（GPT-5.5）实现名为 `DrownedKing`（溺尸王）的 Boss。

v2.0 关键新增（与原 v1.0 的区别）：
1. 必须实现 7.0.1 史诗入场动画（INTRO 状态 + screen_shake + 4 把三叉戟天降 + Boss 坠落 + 融合）
2. 必须实现 7.0.2 水牢机制（WaterPrisonVFX 类，蓝色水泡覆盖减速敌人）
3. 必须实现 7.1.6 动态投掷视觉（实时旋转、8 个残影、帧动画）
4. 必须实现 7.3 近战三连击 VFX（武器放大/扇形电光/360° 圆形剑气）
5. 必须实现 7.7 波纹式大招引爆（按距离排序、间隔 8 帧依次引爆、光柱特效）
6. 必须遵守 7.0.3 系统约束（防蓝块图片加载、i18n 严禁硬编码、CD×2.5、像素级边界检测）

其他强制要求：
- 类名 `DrownedKing`，文件 `Jue_se/drowned_king.py`，继承 `Entity`
- `Trident` 独立类（4 状态机 + 水牢 + 残影）
- 严格按 7.2 FSM 实现 8 状态
- 按 7.8 接入天气联动
- 修改 boss_level.py 的 update() 来管理 INTRO + Trident + 水牢 + 光柱
- 修改 manager.py 注册 DrownedKing
- 代码不要注释，风格与原项目一致
- result dict 兼容 boss_level.py 逻辑
- 通过 `tridents_out` 输出 Trident，不直接操作 mgr.arrows
