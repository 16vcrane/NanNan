# AI 回响架构

## 1. 范围

Phase 5 为每篇已保存日记生成一次单向 AI 回响。日记保存与 AI 生成解耦；Provider、结构化输出或 Guardrail 失败均不得回滚日记。

## 2. 流程

```text
POST /diaries
  -> 同一事务保存 DiaryEntry + pending AiReflection
  -> 返回 diaryId
  -> BackgroundTask（独立数据库会话）
  -> 输入安全检查
  -> reflection_v1 Prompt
  -> LLM Provider
  -> Pydantic 结构化校验
  -> 输出 Guardrail
  -> success / failed / blocked
  -> 小程序轮询 GET /diaries/{id}/reflection
```

Redis 键 `reflection:{reflection_id}` 用作 120 秒分布式锁。Redis 不可用时退化为进程内锁；数据库中的 `pending` 状态和重试计数仍负责最终约束。

## 3. Provider

`LLM_PROVIDER=openai-compatible` 或 `openai` 时，通过兼容 `/chat/completions` 的服务生成 JSON。模型、密钥、基础 URL 和超时均来自环境变量，客户端不接触模型密钥。

Provider 返回：模型原始 JSON 文本、实际模型名和可选 token 用量。网络错误、非 2xx、缺失字段或非文本内容统一转换为 `LLMProviderError`，不记录日记正文或模型原始输出。

## 4. Prompt 与输出

当前 Prompt 为 `backend/app/ai/prompts/reflection_v1.txt`，持久化版本名为 `reflection_v1`。

模型必须输出：

```json
{
  "reflection": "30 至 80 字的回响",
  "keywords": ["可选关键词"],
  "tone": "warm"
}
```

Pydantic 校验失败时状态为 `failed`，原始输出不返回前端。

## 5. Guardrail

输入命中自伤、自杀或明显生命危机规则时，不调用模型，状态写为 `blocked`、安全状态写为 `sensitive`，只返回固定危机兜底文案。

模型输出依次检查长度、危险方法、心理/医学诊断、治疗建议、空泛保证和与日记内容的基础具体性。安全违规写为 `blocked`，普通生成或格式错误写为 `failed`。两种状态都只展示服务端兜底内容。

## 6. 状态与重试

持久化状态为 `pending | success | failed | blocked`。每次真实生成前增加 `attempt_count`；默认最多 3 次尝试，即首次生成加 2 次人工重试。只有 `failed` 且未达到上限时可调用重试接口，`success`、`pending` 和 `blocked` 不可重试。

## 7. 可观测字段

`AiReflection` 保存 `model_name`、`prompt_version`、`attempt_count`、`error_code`、`latency_ms` 和 `token_usage`。日志只记录回响 ID 和错误类型，不记录完整日记或模型原文。

删除日记时同步删除关联 `AiReflection`。如果生成任务仍在执行，落库阶段会再次检查日记和回响是否存在，已删除内容不会被重新写入。

## 8. 规则关键帧

Phase 6 的关键词和关键帧不依赖 LLM。服务端集中维护成长、关系、地点和成就四类词库，在创建日记的事务中按正文首次出现位置提取，去重后最多保存 3 个 `TimelineMarker`。无命中时不生成标签。

日记列表使用一次批量查询加载当前页全部关键帧，避免逐篇查询；详情按相同结构返回。客户端只负责展示服务端返回的类型、文本和颜色，不自行重复关键词规则。
