# 喃喃

面向微信小程序的私密 AI 回忆录。用户用低负担的方式记录当天的文字、情绪和图片，系统在保存日记后异步生成一段克制、具体的 AI 回响，并通过时间轴帮助用户回看自己的生活。

喃喃的核心原则是“先保存，再生成”：AI 失败不会阻断日记保存；原始日记不会被模型改写；所有数据默认仅本人可见。

## 当前能力

- 微信登录、JWT 会话和用户资料
- 今日记录：文字、情绪/能量值、最多 3 张私有图片
- 日记草稿、本地离线恢复、幂等保存和失败重试
- 异步 AI 回响：Provider 适配、Prompt 版本、结构化校验、安全拦截和兜底文案
- 规则化关键词与时间轴关键帧
- 时间轴分页、日记详情和单篇删除
- 数据管理：退出登录、永久删除账户及其关联数据
- Redis 限流、分布式锁、请求 ID、结构化日志和安全响应头
- Docker Compose 开发环境，以及 Caddy + Docker 生产部署方案

当前 AI 回响只使用本篇日记文本，不读取历史日记，不做心理诊断、人格画像或开放式多轮聊天。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 小程序 | 微信原生小程序、JavaScript、WXML、WXSS |
| API | Python、FastAPI、Pydantic |
| 数据 | PostgreSQL、SQLAlchemy Async、Alembic |
| 缓存与治理 | Redis、限流、幂等键、分布式锁 |
| AI | 可配置 LLM Provider、版本化 Prompt、Guardrail |
| 图片 | Pillow 处理、私有本地/S3 兼容对象存储 |
| 交付 | Docker Compose、Caddy、GitHub/任意 CI |

## 目录结构

```text
backend/       FastAPI 服务、数据库模型、迁移、AI 服务和后端测试
miniprogram/   微信小程序页面、组件、服务和资源
tests/         小程序 Node.js 测试
docs/          PRD、技术设计、API、数据库、部署和 AI 路线
deploy/        Caddy 配置
scripts/       发布前检查脚本
```

## 本地开发

### 前置条件

- Docker Engine 与 Docker Compose
- 微信开发者工具（导入 `miniprogram/`）
- Node.js 18+（运行小程序测试）
- Python 3.11+（直接运行后端测试时使用）
- 可选：微信 AppID、LLM Provider 和对象存储配置

### 启动后端依赖与 API

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis
docker compose up --build backend
```

API 默认地址为 `http://localhost:8000`。开发环境提供 `http://localhost:8000/docs`、`/redoc` 和 `/openapi.json`；健康检查为 `GET /api/v1/health`。

也可以直接在本机创建虚拟环境并安装 `backend/requirements.txt`，然后从 `backend/` 运行：

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 配置小程序

在微信开发者工具中导入 `miniprogram/`，并在 `miniprogram/config/environment.js` 设置开发 API 地址。真机调试时，地址必须是已配置到微信公众平台的 HTTPS 合法域名。

## 常用命令

```powershell
# Python 语法检查
python -m compileall -q backend

# 小程序语法与测试
node --check miniprogram\app.js
node --test tests\miniprogram\*.test.js

# 后端测试（需要数据库、Redis；推荐使用 Compose）
docker compose run --rm backend pytest -q tests

# 发布前检查（外部生产配置检查可按需跳过）
.\scripts\release-check.ps1 -SkipExternalChecks
```

## API 概览

API 前缀为 `/api/v1`，除健康检查外均需要 `Authorization: Bearer <access-token>`。完整请求、响应和错误码见 [docs/API_SPEC.md](docs/API_SPEC.md)。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `POST` | `/auth/login` | 使用微信登录 code 换取访问令牌 |
| `GET` | `/users/me` | 获取当前用户 |
| `POST` | `/diaries` | 创建日记并异步触发 AI 回响 |
| `GET` | `/diaries` | 分页查询时间轴 |
| `GET` | `/diaries/{id}` | 查询日记详情 |
| `DELETE` | `/diaries/{id}` | 删除当前用户的日记及关联数据 |
| `POST` | `/uploads/images` | 上传私有图片 |
| `GET` | `/diaries/{id}/reflection` | 查询 AI 回响状态 |
| `POST` | `/diaries/{id}/reflection/retry` | 重试失败的 AI 回响 |
| `DELETE` | `/users/me` | 永久删除账户和全部服务端数据 |

## AI 与隐私边界

- 日记、图片、回响、关键词和派生数据按用户隔离，图片不会通过公开 URL 暴露。
- AI 输入和输出均经过安全检查；敏感/危机内容进入受控兜底流程。
- 日记原文不会写入日志，日志不包含 token、密钥、图片内容或证据文本。
- 删除账户时清理日记、图片、AI 回响、关键帧及对象存储数据；清理失败可重试。
- 生产环境禁止默认密钥、HTTP 和本地文件存储。

## 生产部署

生产部署需要已备案域名、微信小程序凭据、私有 S3 兼容对象存储、模型 API 和 Docker。复制并填写 `.env.production.example` 后执行：

```powershell
Copy-Item .env.production.example .env.production
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Caddy 自动申请 TLS 证书，公网仅暴露 80/443。部署完成后检查 `https://<域名>/api/v1/health`，并在微信公众平台配置 request、uploadFile、downloadFile 三类合法域名。详细步骤见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

## 文档索引

- [产品需求](docs/PRD.md)
- [技术设计](docs/TECH_SPEC.md)
- [AI 架构](docs/AI_ARCHITECTURE.md)
- [AI 工程增强路线](docs/AI_ENHANCEMENT_ROADMAP.md)
- [数据库设计](docs/DATABASE.md)
- [API 规范](docs/API_SPEC.md)
- [发布检查清单](docs/RELEASE_CHECKLIST.md)

## TODO：后续版本更新方向

路线遵循“先确定性检索，后概率性增强；先验证用户价值，后引入向量基础设施”。每一项 AI 能力都必须支持版本化、灰度、回滚和用户关闭；新任务失败不能影响原始日记保存。

### 产品与 AI 工程路线

- [ ] **AI-E1 / P-V1.1：历史上的今天**：按用户时区支持同月同日、30/100/365 天召回；补齐闰年、权限、删除和空状态测试；记录打开率，不调用 LLM。
- [ ] **AI-E2：结构化个人记忆**：新增 `MemoryExtraction`、`MemoryItem` 和证据片段模型；实现 `memory_extract_v1`、异步任务、锁、重试、预算、历史回填和删除取消。
- [ ] **AI-E2 质量门禁**：建立不少于 300 篇脱敏评估集；证据片段有效率不低于 98%，结构化输出首次成功率不低于 97%，高敏感错误推断率低于 0.5%。
- [ ] **AI-E3：Personal Memory 检索**：使用用户级 SQL、关键词和时间候选生成 Context Builder；实现 `reflection_v2`、Shadow 模式、灰度发布、检索审计和 Personal Memory 开关。
- [ ] **AI-E3 上线门禁**：Top-3 人工相关率不低于 80%，历史事实无来源率低于 1%，检索 P95 小于 200ms；关闭开关后立即退回单篇日记回响。
- [ ] **AI-E4：Personal Memory RAG**：仅在 E3 证明价值后评估 pgvector；完成 Embedding 版本、双写回填、Hybrid Retrieval、可解释重排、压力测试和向量删除完整性验证。
- [ ] **AI-E5 / P-V1.4：阶段摘要**：实现 30 天、100 天和年度回顾的 Map-Reduce、增量重建、源内容 hash 和过期处理；不输出人格结论、诊断或情绪排名。
- [ ] **AI-E6 / P-V1.2：关系锚点**：模型只能提出候选，必须由用户确认后创建关系计量器；支持拒绝、归档、删除和避免重复打扰。
- [ ] **AI-E7 / P-V1.3：第三人称回顾与分享**：生成独立展示副本，加入确定性脱敏、隐私泄漏检查、预览、撤销和过期；不修改原文。

### 平台、治理与评估

- [ ] 将短任务从 FastAPI BackgroundTask 迁移到具备幂等 ID、指数退避、DLQ、取消和恢复能力的 Worker/MQ。
- [ ] 统一 `pending -> processing -> success/failed/blocked/cancelled` 状态机，并记录模型、Prompt、任务版本、输入 hash、token 和成本。
- [ ] 增加离线回归集：否定表达、跨天事件、同名实体、危机内容、Prompt Injection、重复任务、超时和删除场景。
- [ ] 增加在线指标：回响查看率、历史回顾打开率、留存、负反馈、任务成功率、Provider 延迟、成本、Guardrail 误拦截和删除残留。
- [ ] 在数据管理中提供结构化记忆、历史记忆使用、派生数据删除、重建和数据导出说明；同步更新隐私政策与 AI 使用说明。
- [ ] 保持明确不做：开放式多轮聊天、跨用户检索/训练、心理疾病或人格推断、自动修改原文、默认图片/EXIF 分析。

路线细节与阶段退出标准见 [docs/AI_ENHANCEMENT_ROADMAP.md](docs/AI_ENHANCEMENT_ROADMAP.md)。

## 版本更新日志

### 2026-08-16 · Unreleased

- 完成项目 README，补充项目定位、架构、启动、测试、API、部署和隐私说明。
- 将 AI 应用工程路线整理为 README TODO，覆盖 AI-E1 至 AI-E7、质量门禁、任务编排和治理要求。

### 1.0.0 · MVP 基线

- 完成微信小程序的今日记录、时间轴、详情、AI 回响、个人中心和数据管理闭环。
- 完成 FastAPI、PostgreSQL、Redis、私有图片存储、微信登录和生产 Docker 部署配置。
- 完成限流、幂等、鉴权、输出安全校验、失败兜底、测试和发布检查流程。
