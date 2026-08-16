# 喃喃 AI 应用工程增强路线

> 文档状态：Draft v1.0  
> 基线版本：MVP Phase 0-10  
> 适用范围：MVP 上线后的 AI、记忆、检索、阶段回顾与相关产品能力演进

## 1. 文档目标

本文将 `TECH_SPEC.md` 中简略的 V1.1-V1.4 AI 增强路线展开为可执行的工程计划，明确：

- 每个阶段解决什么用户问题；
- 数据如何产生、保存、检索和删除；
- 何时需要 LLM、Embedding、Vector Store 和 Rerank；
- API、任务、状态机与数据模型如何演进；
- 如何评价准确性、安全性、成本与产品价值；
- 每个阶段的进入条件、退出标准和回滚策略。

本文不替代 PRD。PRD 决定产品是否上线某项能力，本文定义对应 AI 能力如何可靠实现。

## 2. 版本命名约定

当前文档存在两套版本含义：

| 来源 | V1.2 含义 | V1.3 含义 | V1.4 含义 |
| --- | --- | --- | --- |
| `TECH_SPEC.md` AI 工程路线 | Memory Extraction | Personal Memory Retrieval | Personal Memory RAG |
| `PRD.md` 产品路线 | 关系计量器 | 第三人称视角 | 30/100 天/年度阶段摘要 |

为避免冲突，后续统一使用：

- `AI-E1`、`AI-E2`：AI 工程里程碑；
- `P-V1.1`、`P-V1.2`：用户可见产品版本；
- Prompt、Extractor、Embedding 分别独立版本化，例如 `reflection_v2`、`memory_extract_v1`、`embedding_v1`。

产品版本可以组合多个已稳定的 AI 工程能力，但不能反向要求尚未通过质量门禁的 AI 能力直接上线。

## 3. 当前基线

MVP 已具备：

- 私密日记、图片、情绪值和时间轴；
- 日记保存后异步生成一次 AI 回响；
- Provider Adapter、Prompt 版本化和 Pydantic 结构化输出；
- 输入危机识别、输出 Guardrail、失败兜底和有限重试；
- Redis 分布式锁、请求幂等、限流和结构化日志；
- 规则关键词生成的 TimelineMarker；
- 用户级数据隔离、单篇删除和账户全量删除。

当前回响只使用本篇日记文字，不使用历史日记、情绪值或图片，不具备长期记忆。

## 4. 总体原则

### 4.1 原文不可变

任何抽取、摘要、第三人称转换或记忆融合都只能生成派生数据，不得覆盖 `DiaryEntry.content`。用户删除日记时，所有关联派生数据必须进入同一删除闭环。

### 4.2 先确定性能力，后概率性能力

演进顺序固定为：

```text
确定性日期查询
  -> 结构化记忆抽取
  -> 关系型数据库检索
  -> 检索增强回响
  -> Embedding / Hybrid Retrieval
  -> Rerank / 阶段摘要
```

在 SQL、时间、类型和关键词检索足以验证价值前，不引入向量数据库。

### 4.3 证据可追溯

每一条 MemoryItem 必须关联来源日记和证据片段。任何个性化回响都应能在内部追踪到使用了哪些历史记忆，禁止模型把推测写成用户事实。

### 4.4 私密与最小化

- 只抽取实现当前功能所需的字段；
- 不构建心理画像、疾病标签、人格评分或幸福指数；
- 日记、Memory、Embedding 和检索日志均按 `user_id` 隔离；
- 不在日志、监控标签或错误信息中记录正文和证据片段；
- 默认不使用图片做多模态分析，除非产品重新完成隐私评审与用户授权。

### 4.5 AI 失败不阻断记录

所有增强任务继续采用异步派生模式。抽取、Embedding、检索或摘要失败不能回滚日记，也不能阻止用户查看原文。

### 4.6 单向陪伴边界不变

长期记忆用于生成更具体的单向回响与回顾，不演变为开放式多轮聊天，不提供心理诊断、治疗建议和强结论性判断。

## 5. 路线总览

| 里程碑 | 用户能力 | 核心技术 | 是否调用 LLM | 建议依赖 |
| --- | --- | --- | --- | --- |
| AI-E1 | 历史上的今天 | 日期查询、轻量召回 | 否 | MVP 稳定运行 |
| AI-E2 | 结构化个人记忆 | 异步抽取、证据定位 | 是 | AI-E1 |
| AI-E3 | 个性化历史检索 | SQL/关键词/时间检索、Context Builder | 回响阶段调用 | AI-E2 质量达标 |
| AI-E4 | Personal Memory RAG | Embedding、Hybrid Retrieval、Rerank | 是 | AI-E3 证明用户价值 |
| AI-E5 | 阶段摘要 | Map-Reduce 摘要、增量聚合 | 是 | AI-E3 或 AI-E4 |
| AI-E6 | 关系锚点与生活阶段 | Memory Link、用户确认 | 可选 | AI-E2 |
| AI-E7 | 第三人称回顾与分享 | 受控改写、脱敏检查 | 是 | AI-E2、安全评审 |

## 6. AI-E1：历史上的今天

### 6.1 用户价值

让用户在不增加输入负担的情况下重新遇见过去的记录，验证“回看”是否能提升留存。无历史记录时不展示空入口、不发送通知。

### 6.2 召回规则

优先级建议：

1. 同月同日的往年记录；
2. 30 天前记录；
3. 100 天前记录；
4. 365 天前记录。

每次最多返回 3 条，按时间距离与记录完整度排序。默认只展示日期、情绪和文字摘要；图片必须经过用户点击后再加载。

### 6.3 工程实现

- 为 `DiaryEntry(user_id, created_at)` 保持可用索引；
- 使用用户时区计算“今天”，不能直接使用服务器 UTC 日期；
- 新增查询服务，不复制日记数据；
- 复用现有权限校验与私有图片下载链路；
- 可缓存“用户 + 本地日期”结果，日记增删后主动失效。

建议接口：

```http
GET /api/v1/memories/on-this-day?timezone=Asia/Shanghai
```

### 6.4 验收标准

- 跨年、闰年、时区边界测试通过；
- 不返回其他用户、软删除日记或未授权图片；
- 无结果时接口返回空数组，客户端不制造打扰；
- P95 数据库查询低于 150ms；
- 不引入 LLM 成本。

## 7. AI-E2：Memory Extraction

### 7.1 目标

将每篇日记抽取为可检索、可追溯的结构化记忆，类型包括：

- `person`：人物；
- `event`：事件；
- `place`：地点；
- `achievement`：成就；
- `relationship`：关系锚点；
- `life_stage`：生活阶段线索。

抽取结果是派生事实候选，不代表系统对用户做出的确定判断。

### 7.2 输出契约

建议 Prompt：`memory_extract_v1`。

```json
{
  "items": [
    {
      "type": "achievement",
      "label": "完成毕业答辩",
      "normalizedValue": "毕业答辩",
      "evidence": "今天终于完成了毕业答辩",
      "startOffset": 0,
      "endOffset": 12,
      "confidence": 0.96,
      "occurredOn": "2026-06-18",
      "attributes": {}
    }
  ]
}
```

约束：

- `evidence` 必须是原文连续子串；
- offset 必须能反向校验；
- 不允许根据常识补全姓名、地点或关系；
- 不抽取疾病、人格、政治倾向等高敏感推断；
- 低于置信阈值的结果不进入在线检索；
- 单篇日记限制条目数，例如最多 12 条。

### 7.3 数据模型建议

```text
MemoryExtraction
  id
  diary_entry_id
  user_id
  status                 pending|processing|success|failed|blocked
  extractor_version
  source_content_hash
  model_name
  attempt_count
  latency_ms
  token_usage
  error_code
  created_at / updated_at

MemoryItem
  id
  extraction_id
  diary_entry_id
  user_id
  type
  label
  normalized_value
  evidence_text
  evidence_start
  evidence_end
  confidence
  occurred_on
  attributes_json
  review_status           auto|confirmed|rejected
  created_at / updated_at
```

关键索引：

- `(user_id, type, occurred_on)`；
- `(user_id, normalized_value)`；
- `(diary_entry_id, extractor_version)` 唯一约束；
- 删除日记时对 Extraction、Item 执行级联删除。

### 7.4 任务流程

```text
Diary saved
  -> create pending extraction
  -> distributed lock
  -> source hash validation
  -> input safety/minimum-content check
  -> LLM structured extraction
  -> schema validation
  -> evidence span validation
  -> sensitive inference filter
  -> transactional replace of MemoryItems
  -> success / failed / blocked
```

重新抽取必须使用“新版本先写入、校验成功后切换”的方式，不能先删除当前可用结果。

### 7.5 回填策略

- 新日记实时进入队列；
- 历史日记按用户分批回填，设置每日 token 与并发预算；
- 优先回填最近 90 天，再扩展到完整历史；
- 记录 `source_content_hash`，内容未变化且版本一致时跳过；
- 删除请求优先级高于回填任务，已删除数据不得重新生成。

### 7.6 质量门禁

构建脱敏人工标注集，至少覆盖 300 篇不同长度和表达方式的中文日记。核心指标：

- Evidence Span 有效率 >= 98%；
- 人物/事件/地点宏平均 Precision >= 90%；
- 高敏感错误推断率 < 0.5%；
- JSON/Schema 首次成功率 >= 97%；
- 单篇 P95 处理时延与成本符合预算；
- 删除日记后派生数据残留为 0。

Precision 优先于 Recall。宁可少抽取，也不能制造错误人生事实。

## 8. AI-E3：Personal Memory Retrieval

### 8.1 目标

在不引入向量数据库的前提下，用结构化记忆为当前日记检索少量相关历史，生成更具体但不冒犯的回响。

### 8.2 检索流程

```text
Current Diary
  -> Query Analyzer
  -> time/type/keyword candidates
  -> user-scoped retrieval
  -> deterministic scoring
  -> diversity and sensitivity filter
  -> Context Builder
  -> reflection_v2
  -> output validation and attribution audit
```

候选来源：

- 当前日记的 MemoryItem 类型与 normalized value；
- 规则关键词；
- 时间邻近记录；
- “历史上的今天”；
- 用户确认过的关系锚点。

### 8.3 初始评分建议

```text
score =
  0.35 * keyword_overlap
  + 0.25 * type_match
  + 0.20 * time_relevance
  + 0.15 * confidence
  + 0.05 * user_confirmed_bonus
```

这不是长期固定公式。所有权重必须配置化并通过离线评估调整。

### 8.4 Context Builder

Context Builder 负责把数据库结果转成最小必要上下文，而不是把历史日记全文直接拼入 Prompt。

建议预算：

- 最多 3 条历史记忆；
- 每条包含日期、类型、规范化标签和短证据；
- 历史上下文总字符数不超过 600；
- 当前日记始终占主要权重；
- 同一来源日记最多 2 条 MemoryItem；
- 对低落、危机、关系破裂等敏感主题使用更严格阈值。

Prompt 必须明确：历史记忆仅用于温和关联，不能声称用户“总是”“从来”“一定”，不能把过去状态当作当前事实。

### 8.5 可观测性

新增 `RetrievalRun` 或等价审计记录：

```text
request_id
user_id
diary_id
retriever_version
candidate_count
selected_memory_ids
latency_ms
status
```

生产日志不得写入 Memory 文本。`selected_memory_ids` 仅保存于受控数据库审计字段，不进入普通日志标签。

### 8.6 上线策略

1. Shadow 模式：执行检索但仍使用 `reflection_v1`；
2. 内部评审检索结果，不向用户展示；
3. 5% 用户启用 `reflection_v2`；
4. 比较具体性、负反馈、安全拦截、成本和延迟；
5. 逐步扩大到 25%、50%、100%。

必须保留按用户和全局关闭 Personal Memory 的 Feature Flag。

### 8.7 验收标准

- 所有检索 SQL 强制包含 `user_id`；
- Top-3 人工相关率 >= 80%；
- 历史事实无来源率 < 1%；
- 相比 `reflection_v1`，用户主动查看回响率或收藏/停留指标有明确提升；
- P95 检索延迟 < 200ms，不含 LLM；
- 关闭功能后立即退回单篇日记回响。

## 9. AI-E4：Personal Memory RAG

### 9.1 进入条件

只有同时满足以下条件才进入 RAG：

- AI-E3 已证明结构化历史检索能提升用户价值；
- 失败案例主要来自语义表达差异，而不是抽取错误；
- MemoryItem 数量和用户历史长度达到 SQL/关键词检索瓶颈；
- 团队具备向量索引监控、重建、删除和成本治理能力。

### 9.2 Embedding 单元

优先对 MemoryItem 建向量，不直接对完整日记全文建向量。建议文本：

```text
[type] achievement
[label] 完成毕业答辩
[date] 2026-06-18
[evidence] 今天终于完成了毕业答辩
```

保存字段：

```text
memory_item_id
user_id
embedding_version
embedding_model
dimension
vector
content_hash
created_at
```

Embedding 版本、维度或模型变化时新建索引并双写，不原地混用。

### 9.3 Vector Store 选择

初期优先 PostgreSQL + pgvector，原因是：

- 数据量与 MVP 用户规模匹配；
- 用户隔离、事务和删除链路更简单；
- 避免过早增加独立向量数据库运维面。

只有在向量规模、并发或延迟证明 pgvector 不足时，再评估独立 Vector Store。

### 9.4 Hybrid Retrieval

候选集合由以下部分合并：

- 结构化过滤：用户、类型、日期、确认状态；
- 关键词/BM25；
- 向量相似度；
- 历史上的今天与关系锚点规则召回。

合并后执行：

1. 去重；
2. 来源日记多样性约束；
3. 时间衰减；
4. 敏感记忆过滤；
5. Top-N Rerank；
6. Context Builder 截断。

### 9.5 Rerank

首版使用可解释的加权重排。只有离线数据证明必要时才引入 Cross Encoder 或 LLM Rerank。禁止让高成本 Rerank 成为日记保存的同步依赖。

### 9.6 RAG 评估

- Recall@10；
- NDCG@5；
- Context Precision；
- Context Recall；
- Groundedness；
- 历史事实误用率；
- 敏感记忆误召回率；
- 每次回响平均 token、Embedding 与 Rerank 成本；
- P50/P95/P99 端到端延迟。

必须维护固定回归集，模型、Prompt、Embedding 或权重升级都要重跑。

## 10. AI-E5：阶段摘要

### 10.1 产品形态

对应 PRD 的 30 天、100 天和年度回顾。只有满足最小日记数量时生成，用户可主动刷新，但不能无限重试。

### 10.2 输入策略

不直接把阶段内所有日记全文一次性发送给模型。采用：

```text
MemoryItems + daily reflections
  -> weekly deterministic groups
  -> map summaries
  -> reduce summary
  -> structured validation
  -> safety and evidence audit
```

阶段摘要建议输出：

- 被记录最多的生活主题；
- 用户明确写下的完成与变化；
- 可回看的 3-5 个时刻；
- 一段克制的总结。

禁止输出人格结论、心理趋势诊断、情绪排名和未来预测。

### 10.3 增量计算

- 使用时间窗口和源内容 hash；
- 新增日记只重算受影响分片；
- 摘要版本与 Prompt 版本独立保存；
- 用户删除源日记后标记摘要过期并异步重建；
- 过期摘要不得继续分享。

## 11. AI-E6：关系锚点与生活阶段

### 11.1 用户确认优先

模型只能提出候选：

```text
“我们在一起了” -> relationship_anchor_candidate
```

只有用户确认后才创建正式关系锚点和计时卡。模型不得根据多篇日记擅自判断恋爱、分手、家庭关系或关系质量。

### 11.2 数据建议

```text
MemoryLink
  id
  user_id
  source_memory_item_ids
  link_type
  display_label
  occurred_on
  status              candidate|confirmed|rejected|archived
  confirmed_at
```

用户拒绝后应保存最小化的 rejected 状态，避免相同候选反复打扰；用户可随时归档或删除。

## 12. AI-E7：第三人称回顾与分享

### 12.1 实现边界

- 只生成展示副本，不修改原文；
- 默认满 7 天后由用户主动解锁；
- 不开放自由指令和多轮改写；
- 分享前必须预览确认；
- 默认隐藏精确日期、地点、EXIF、真实姓名候选和敏感证据。

### 12.2 安全流水线

```text
selected diary/memories
  -> deterministic redaction
  -> third-person rewrite
  -> structured output validation
  -> privacy leak detection
  -> content safety
  -> preview
  -> explicit share action
```

分享稿应有独立过期时间，不永久复制完整日记。

## 13. Agent 与任务编排演进

当前 FastAPI BackgroundTask 适用于短任务。出现以下任一情况后应迁移 Worker/MQ：

- 历史回填任务超过单实例可控范围；
- 阶段摘要需要多步 Map-Reduce；
- 任务需要延迟重试、优先级、暂停和恢复；
- 部署重启导致任务丢失不可接受；
- 同时运行 Extraction、Embedding、Summary 等多类任务。

建议任务状态统一为：

```text
pending -> processing -> success
                    -> failed -> retry_wait -> processing
                    -> blocked
                    -> cancelled
```

Worker 必须具备：

- 幂等任务 ID；
- 最大重试次数和指数退避；
- Dead Letter Queue；
- 用户删除时取消任务；
- 每用户并发限制；
- Provider 级熔断和预算限制；
- 任务版本与输入 hash。

不要构建“自主规划型 Agent”。本产品需要的是受控工作流，每一步的输入、输出和权限边界都应明确。

## 14. API 演进建议

```http
GET  /api/v1/memories/on-this-day
GET  /api/v1/memories/items?type=&page=&limit=
POST /api/v1/memories/items/{id}/confirm
POST /api/v1/memories/items/{id}/reject
GET  /api/v1/diaries/{id}/reflection
POST /api/v1/diaries/{id}/reflection/retry
GET  /api/v1/summaries?period=30d|100d|year
POST /api/v1/summaries/{period}/generate
GET  /api/v1/ai/preferences
PATCH /api/v1/ai/preferences
```

MemoryItem 列表是否直接对用户开放，应由产品验证决定。即使不展示，也必须提供关闭个性化记忆、删除派生记忆和触发重建的能力。

## 15. 用户控制与解释

在“数据管理”中逐步增加：

- 是否允许生成结构化记忆；
- 是否允许历史记忆用于 AI 回响；
- 查看系统使用了哪些历史日期，不展示内部 Prompt；
- 删除单条派生记忆；
- 重建派生记忆；
- 关闭后删除 Embedding 与检索缓存；
- 导出原始日记与派生数据的说明。

关闭 Personal Memory 后，新回响立即退回仅使用当前日记的模式。

## 16. 安全、合规与删除闭环

### 16.1 数据分类

| 数据 | 敏感级别 | 处理要求 |
| --- | --- | --- |
| 日记原文、图片 | 高 | 私密存储、严格鉴权、禁止日志记录 |
| MemoryItem、Evidence | 高 | 与原文同级保护、按来源级联删除 |
| Embedding | 高 | 视为个人数据，不做跨用户共享 |
| RetrievalRun | 中高 | 最小化保存，不记录正文 |
| 聚合质量指标 | 中 | 去标识化，不允许反推用户内容 |

### 16.2 删除顺序

```text
cancel pending jobs
  -> delete retrieval cache
  -> delete embeddings/vector entries
  -> delete summaries and memory links
  -> delete memory items/extractions
  -> delete reflections/markers/images/diaries/account
```

删除必须可重试、可审计。任何外部 Vector Store 都必须支持按 `user_id` 和 source ID 验证删除结果。

### 16.3 Prompt Injection

日记是非可信输入。Prompt 必须把日记与系统指令明确分隔，并声明不得执行日记中的命令。Memory Extraction 和 RAG 都不能把历史文本当作工具调用指令。

## 17. 评估体系

### 17.1 离线评估集

建立版本化数据集：

- 正常短日记、长日记、口语和错别字；
- 人物同名、地点歧义和跨天事件；
- 否定表达，例如“没有去北京”；
- 假设与愿望，例如“希望以后毕业”；
- 危机、诊断诱导和 Prompt Injection；
- 删除、编辑、重复任务和模型超时。

标注数据必须脱敏并限制访问，优先使用团队自建合成样本与明确授权样本。

### 17.2 在线指标

产品价值：

- AI 回响查看率；
- 历史回顾打开率；
- 次日/7 日/30 日记录留存；
- 用户关闭 Personal Memory 的比例；
- 负反馈、删除派生记忆和重新生成比例。

工程质量：

- 各任务成功率、重试率和 DLQ 数量；
- Provider 延迟、错误率和 token 成本；
- 检索空结果率和重复来源率；
- Guardrail 拦截率与误拦截抽检；
- 删除闭环耗时与残留检查。

不得使用“情绪变好”“幸福指数提升”作为产品成功指标。

## 18. 成本治理

- 所有 AI 任务记录模型、版本、token 和成本估算；
- 按用户设置每日/每月任务预算；
- Extraction 使用小模型并限制输出长度；
- 相同 source hash + version 结果复用；
- Embedding 批处理并去重；
- 阶段摘要只在数据量门槛满足后生成；
- 高成本 Rerank 受 Feature Flag 和采样率控制；
- Provider 异常时降级到规则结果或当前日记回响。

## 19. 分阶段任务拆分

### AI-E1

- `E101` 用户时区与日期查询服务；
- `E102` 历史上的今天 API；
- `E103` 客户端入口、空状态和图片延迟加载；
- `E104` 闰年、时区、权限和删除测试；
- `E105` 召回率与打开率埋点。

### AI-E2

- `E201` Extraction/MemoryItem 表与迁移；
- `E202` `memory_extract_v1` Prompt 与 Schema；
- `E203` Evidence Span 和敏感推断 Guardrail；
- `E204` 异步任务、锁、重试与删除取消；
- `E205` 历史回填命令与预算控制；
- `E206` 标注集和离线评估流水线；
- `E207` Feature Flag 与用户关闭入口。

### AI-E3

- `E301` Query Analyzer；
- `E302` SQL/关键词/时间候选召回；
- `E303` 可配置评分与多样性过滤；
- `E304` Context Builder；
- `E305` `reflection_v2` 与历史事实 Guardrail；
- `E306` Shadow 模式和 A/B 发布；
- `E307` Retrieval 审计与指标。

### AI-E4

- `E401` Embedding Provider Adapter；
- `E402` pgvector 迁移和用户级索引；
- `E403` 双写、回填和版本切换；
- `E404` Hybrid Retrieval；
- `E405` 可解释 Rerank；
- `E406` RAG 离线评估与压力测试；
- `E407` Vector 删除完整性测试。

### AI-E5-E7

- `E501` 阶段摘要 Map-Reduce 与增量重建；
- `E601` 关系候选和用户确认模型；
- `E701` 第三人称改写与隐私脱敏；
- `E702` 分享预览、过期和撤销机制。

## 20. 建议实施节奏

以下是相对工作量，不是固定发布日期：

| 阶段 | 建议周期 | 关键产出 |
| --- | --- | --- |
| AI-E1 | 1-2 周 | 无 LLM 的历史回顾闭环 |
| AI-E2 Prototype | 2 周 | Schema、Prompt、100 篇评估集 |
| AI-E2 Production | 2-4 周 | 任务系统、回填、删除与开关 |
| AI-E3 Shadow | 2 周 | 检索、Context Builder、内部评估 |
| AI-E3 Rollout | 2-4 周 | `reflection_v2` 灰度与 A/B |
| AI-E4 | 4-6 周 | pgvector、Hybrid、RAG 评估 |
| AI-E5-E7 | 按产品验证拆分 | 摘要、关系、分享能力 |

每个阶段结束后必须先观察质量和用户价值，再决定是否进入下一阶段。不能把“引入向量库”本身视为里程碑成功。

## 21. 发布门禁

任何新 AI 能力上线前必须满足：

- [ ] 数据模型和删除级联已评审；
- [ ] Prompt、Schema、Retriever、Embedding 均有明确版本；
- [ ] 离线评估达到该阶段阈值；
- [ ] 权限测试证明不存在跨用户召回；
- [ ] Guardrail 与危机内容回归通过；
- [ ] 日记保存不依赖新 AI 任务成功；
- [ ] Redis、Provider、Worker 失败有降级路径；
- [ ] 日志不包含正文、Evidence、Token 或密钥；
- [ ] 成本预算、限流与熔断已配置；
- [ ] Feature Flag 可全局关闭；
- [ ] 用户可以关闭个性化记忆并删除派生数据；
- [ ] 灰度指标和回滚方案已准备；
- [ ] 隐私政策与 AI 使用说明已同步更新。

## 22. 明确不做

- 不构建开放式多轮聊天机器人；
- 不根据日记推断心理疾病、人格、收入、政治倾向等敏感画像；
- 不跨用户训练、检索或推荐私人内容；
- 不让模型自动修改原始日记；
- 不默认分析图片、EXIF 或精确地理位置；
- 不在 AI-E3 价值未验证前引入独立向量数据库；
- 不把高成本 Agent 或 Rerank 放进同步保存链路；
- 不以技术复杂度、模型数量或向量规模作为产品价值指标。

## 23. 下一步

建议从 AI-E1 开始，先实现“历史上的今天”并验证用户是否愿意回看。并行准备 AI-E2 的脱敏评估集和 `memory_extract_v1` Schema，但在评估阈值、删除闭环和用户开关完成前，不把抽取结果用于线上回响。

推荐的首个技术决策记录（ADR）主题：

1. MemoryItem 数据边界与敏感字段禁区；
2. Evidence Span 校验规则；
3. BackgroundTask 迁移 Worker/MQ 的触发条件；
4. pgvector 与独立 Vector Store 的选择门槛；
5. Personal Memory 用户开关与删除语义。
