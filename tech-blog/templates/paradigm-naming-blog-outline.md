# 范式/概念命名类博客大纲模板

> 来源:2026-06 Loop Engineering 博客实战(已发布飞书: HGtVdsZ4YoxsVLxYvrjcJcs5nPg)
> 适用场景:某新概念/范式/术语被权威方命名后的系统性中文解读
> 预期产出:5000-20000 字深度长文

## 适用判断

满足以下 ≥3 条,使用本模板:

- [ ] 概念有明确的命名博客/白皮书/RFC 一手来源
- [ ] 命名方是行业头部公司/工程师(如 Addy Osmani, Boris Cherny)
- [ ] 概念涉及"X Engineering"或"X Loop"这类工程范式命名
- [ ] 一周内出现 ≥2 个不同来源的引用或讨论
- [ ] 概念层级关系清晰(在已有范式之上叠加,而非完全替代)

## 章节骨架(10 章 + 附录)

### 1. 为什么是这一周(Why Now)

- 锚定时间窗口(精确到周/天)
- 列出 2-3 个**同一时间窗**内的权威发声
- 区分"概念被发明"vs"概念被命名"——后者是更准的叙事起点
- 引用一手数据源,标注"一手/二手/工程化解读"三级

### 2. 过去 N 个月的范式演进(Evolution)

- 用**时间轴**或**层级图**展示概念在范式链条中的位置
- 4 个范式为典型结构(Prompt → Context → Harness → Loop)
- 每一层回答不同的问题——表格化展示

### 3. 定义(Definition)

- 引用命名者的**两段英文原文** + 中文翻译
- 拆出 3 个关键要素(Replace yourself / Recursive goal / Iterates until complete)
- **专门一节**澄清最易混淆的边界(本例:agent while loop vs Loop Engineering)

### 4. 五大原语 + 一个状态层(Anatomy)

- **核心交付物**:跨产品映射表(Codex vs Claude Code)
- 表格设计原则:行=原语,列=角色/Codex/Claude Code
- 展开讲解 2-3 个最关键的原语
- 加一张 Mermaid 层级图(注意:飞书不渲染,需手动补 PNG)

### 5. 两个易混命令/概念(Common Confusion)

- 用对比表回答"它们解决的是不同问题"
- 一句话定位 + 完整对比表 + 组合使用示例
- 末尾加"反直觉的点"——避免读者误用

### 6. 完整形态(End-to-End Example)

- **Mermaid sequenceDiagram** 展示一个完整的 loop 跑起来的样子
- 配合伪代码化文字描述
- 强调"你做了什么":只设计了一次,后续都是 loop 跑

### 7. 最小起步(Minimal Start)

- 6 步路径(步骤数 5-7 为佳)
- 每步配具体可操作内容(配置示例 / schema / prompt 模板)
- **必须包含**:verifier sub-agent prompt 模板、state 文件 JSON schema
- 步骤 6 永远是"保留人工 review 节点"——这是硬约束

### 8. 反方观点(Counter-Points)

- **5 个子节**是合理的密度
- 覆盖:同 loop 两种结局 / 认知债 / 认知投降 / token 成本 / 命名风险
- 加**量化锚点**:token 估算公式 + 回本点 + 预警信号
- 反方观点是**差异化竞争力**——比正方更难写,但读者印象最深

### 9. 给不同角色的具体建议(Role-Based Action)

- 3 个角色为佳:AI 工程师 / 技术决策者 / 产品或创业者
- 每角色 3-4 条**时间维度行动**:今天/下个月/季度
- 避免抽象建议(否则被读者打 0 分)

### 10. 回到原话(Callback)

- 用最精准的一句原话结尾
- 提炼一句金句(自创,贯穿全文)

### 附录

- 数据源表格(标注一手/二手)
- 写作日期
- 术语说明(英文为主,中文括号)

## 关键写作约束

### 引用规范

- 英文原话保留 ASCII 双引号 `"..."`
- 中文行文用中文引号 `"..."`
- 命名者原话在文章中**完整出现 2 次**(开头+结尾),中间引用可节选

### 反方观点密度

- 5 角色反馈中,资深工程师+商业决策者会**主动要求**反方观点
- 反方观点章节应占总字数 20-25%

### 配图策略

- Mermaid 图:**至少 2 张**(层级图 + 时序图)
- 表格:**5-7 张**为合理密度
- 飞书发布时 Mermaid 需手动补 PNG

## 已知发布陷阱

1. **飞书不渲染 Mermaid**——必须用 mermaid.live 导出 PNG 手动上传
2. **首行必须 `# 标题`**——lark-cli 从首行自动提取,无 `--title` 参数
3. **`--new-title` 在当前 lark-cli v2 不存在**——旧文档误传

## 复刻本模板的命令

```bash
# 1. 复制本模板
cp templates/paradigm-naming-blog-outline.md <new-blog-outline>.md

# 2. 按骨架填空
# - 阶段 1:填章节 1(为什么是这一周) + 数据源附录
# - 阶段 3:填章节 2-10 标题和子节

# 3. 写完后发布
cd /Users/xiesg/workspace
lark-cli docs +create --api-version v2 --doc-format markdown --content @./<new-blog>.md
```

## 本模板的来源实证

- Loop Engineering 博客 2026-06-13 发布,飞书 ID: HGtVdsZ4YoxsVLxYvrjcJcs5nPg
- 总字数:约 18,000 字
- 5 角色反馈综合评分:资深工程师 3.5/5,普通读者 2.3/5(经 P0+P1 优化后)
- 主要数据源:Osmani 命名博客(一手) + The New Stack 报道(二手) + MindStudio 工程化解读
