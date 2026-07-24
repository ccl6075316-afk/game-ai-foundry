# 工程 Spec：production 逻辑布局 v1

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：req
- **Created**：2026-07-24
- **Updated**：2026-07-24（你已确认）
- **Confirmed By**：user「确认」
- **Source Of Truth Until**：确认 plan 之后以 plan 为准
- **Requirements Source**：场景积木讨论；布局放 production（B）；regions+placements（B）；derive 用规则填（A）；user「确认」
- **Background Inputs**：已落地的 content_class / view / 稀疏背景策略；现有 `production derive`
- **Compounded Knowledge**：不默认用「看背景图再摆放」

## 用大白话说要做什么

玩家看到的场景，不靠一张超满的背景图画完，而是：

1. 背景尽量空一点（氛围）  
2. 码头、柜子、地砖等是**积木**（已经能按类型出图）  
3. 还要一份**摆放说明书**：哪个积木放在屏幕大概哪个位置  

这份说明书放在 **`production.json`** 里（施工图纸），**不**塞进 brief（产品说明已经够多了）。

坐标用 **0～1**：比如 `0.5, 0.5` 表示画面正中附近，不绑某一张背景 PNG 的像素。

## 目标

1. 在 `production_doc` 增加可选对象 **`layout`**：  
   - **`regions`**：有名字的区域（如水面、岸、可玩区），带简单形状（矩形或上下带宽）  
   - **`placements`**：每条写明 `asset`（brief 里已有的资产 id/name）+ 归一化位置 `xy_norm`，可选挂到某个 region  
2. 跑 **`production derive`** 时，用**规则**自动生成一版 layout（按游戏类型、`project.view`、资产的 `content_class`）。  
3. **校验**：placement 引用的资产必须在 brief 里；坐标要在合理范围；坏数据要报错。  
4. 文档/程序员 skill：说明「按 layout 摆节点」，但**本期不必**自动改 Godot 场景文件或强塞 godot_tasks。  
5. 旧 production 没有 `layout`：仍然合法（可选字段）。

## 不做（本期）

- 用 AI「看」生成好的背景再猜位置  
- 用 LLM 精修坐标  
- 自动写一整套 Godot 放置任务（可下期）  
- 把 layout 写进 brief  

## 已拍板

| 项 | 选择 |
|----|------|
| 放哪 | 只在 production |
| 内容 | 区域 + 摆放列表 |
| 怎么生成 | derive 规则自动填 |
| 背景 vision | 不做默认路径 |

## 怎样算做成

1. 示例 brief derive 后，production 里能看到 `layout.regions` 和若干 `placements`。  
2. 故意写错资产名 → validate 报错。  
3. 无 layout 的旧文件 → validate 仍通过。  
4. 文档里写清程序员怎么读这份布局。

## 大概要动哪里

- `cli/production.py`（生成 + 校验）  
- 单测  
- godot-developer / AI-HANDOFF 短说明  

## Resume

代码已落地（未提交）。下一步：review / 提交。
