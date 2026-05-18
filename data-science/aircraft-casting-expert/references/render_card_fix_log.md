# render_card.py 修正记录

## 根因

`_render_inspection()` 函数中的检验规则描述是**手写字符串**，没有从 `knowledge/hb5480.yaml` 检索。
导致两个问题：

1. X射线抽样表号写反（III类→表9应为→表8；II类10批后→表8原文正确但描述含糊）
2. 单铸试棒力学性能标准漏了 ZL205A 应符合 HB 962 的关键区别

## 正确做法（已在修正版中实现）

```python
def _render_inspection(result: dict) -> str:
    import yaml, os

    # 始终从 hb5480.yaml 加载，不再手写字符串
    skill_dir = os.path.dirname(os.path.abspath(__file__))
    hb5480_path = os.path.join(skill_dir, "knowledge", "hb5480.yaml")
    with open(hb5480_path, encoding="utf-8") as f:
        hb = yaml.safe_load(f)

    sampling = hb.get("sampling", {})
    xray = sampling.get("xray", {})
    mechanical = sampling.get("mechanical", {})
    ...
```

所有检验规则（荧光/X射线/力学性能/晶间腐蚀）必须从 YAML 检索，禁止手写硬编码字符串。

## 教训

- 知识库（YAML）是对的，渲染层（render_card.py）写了硬编码
- `_render_inspection` 属于"容易手滑出错"的函数类型，正确的架构是"渲染器只负责格式，知识数据全从YAML取"
- 修正后的 `render_card.py` 已写入技能目录 `/root/.hermes/skills/data-science/aircraft-casting-expert/render_card.py`，需用 terminal 工具覆盖源文件（skill_manage 无法操作 .py 文件）
