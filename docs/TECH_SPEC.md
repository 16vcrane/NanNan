# 喃喃（NanNan）AI 应用工程技术开发规格说明书

> 文档版本：v1.0\
> 项目阶段：MVP 技术开发阶段\
> 产品形态：微信小程序 + AI 应用后端\
> 前端开发：微信开发者工具创建项目，VSCode 负责主要代码开发\
> AI 开发方式：后端统一调用模型，禁止在小程序端暴露模型密钥\
> 文档用途：作为 Codex / Cursor 的开发基准、Git
> 开发任务拆分依据和后续简历项目工程化依据

------------------------------------------------------------------------

## 0. 文档使用规则

### 0.1 本文档的定位

本文件不是新的 PRD，而是将现有 `PRD.md` 和 UI
设计稿转化为可执行的技术开发规格。

优先级：

``` text
PRD.md
  ↓
TECH_SPEC.md
  ↓
代码实现
  ↓
测试 / 验收
```

如果代码实现与 PRD / TECH_SPEC
冲突，应先停止并确认，不允许为了"方便开发"自行改变产品行为。

### 0.2 需求来源与技术决策边界

以下内容直接继承 PRD：

-   产品定位
-   MVP 功能范围
-   页面结构
-   用户流程
-   AI 回响内容规范
-   数据模型核心字段
-   隐私与安全原则
-   异常状态
-   验收标准
-   P0 / P1 / P2 优先级

以下属于本技术规格为了便于工程实现而做出的技术决策：

-   使用 FastAPI 作为自建后端
-   使用 PostgreSQL 作为业务数据库
-   使用 Redis 作为缓存 / 限流 / 任务状态辅助组件
-   前后端采用 REST API
-   后端采用分层架构
-   AI 模型采用 Provider Adapter 设计，具体模型通过环境变量配置
-   MVP 使用轻量异步任务机制，后续如规模增长再拆分 Worker / MQ

如果后续技术方案发生变化，应修改本文件并同步代码，不应仅在代码中隐式改变。

------------------------------------------------------------------------

# 1. 项目目标

## 1.1 产品定位

「喃喃」是一款面向微信生态的私密 AI 回忆录小程序：

> 记录此刻 → AI 共鸣 → 时光回顾 → 激发再次记录

用户低负担记录每天的情绪、事件和片段，AI
在用户完成记录后生成一段温暖、克制、具体的单向回响，再通过时间轴沉淀为可回看的个人故事。

MVP 的核心目标不是功能数量，而是验证：

1.  用户愿意记录；
2.  AI 回信有价值；
3.  用户愿意回看。

## 1.2 MVP 核心闭环

``` text
打开小程序
    ↓
今日记录
    ↓
选择情绪 / 能量
    ↓
输入文字
    ↓
可选上传图片
    ↓
保存日记
    ↓
服务端内容安全校验
    ↓
日记先落库
    ↓
异步生成 AI 回响
    ↓
关键词 / 关键帧提取
    ↓
AI 回响结果
    ↓
时光时间轴
    ↓
日记详情
```

关键原则：

> AI 生成失败不能影响日记保存。

------------------------------------------------------------------------

# 2. MVP 范围冻结

## 2.1 MVP 必做

-   微信登录与用户身份
-   今日记录页
-   文字日记输入
-   情绪 / 能量值选择
-   最多 3 张图片
-   日记保存
-   本地草稿保护
-   AI 晚安信 / AI 回响
-   关键词提取
-   关键帧标记
-   时光瀑布流 / 时间轴
-   日记详情
-   日记删除
-   我的 / 设置与隐私
-   AI 使用说明
-   生成中 / 成功 / 失败 / 空状态
-   基础内容安全
-   用户数据隔离

## 2.2 一级导航

严格保持：

``` text
今日 | 时光 | 我的
```

以下页面不是一级 Tab：

``` text
AI 回响
日记详情
AI 使用说明
隐私政策
用户协议
```

## 2.3 MVP 不做

以下功能不得在 MVP 阶段自行加入：

-   发现页
-   社区
-   评论
-   陌生人匹配
-   开放式多轮 AI Chat
-   自定义 BGM 上传
-   未授权音乐播放
-   复杂心理测评
-   雷达图
-   幸福指数
-   排名式情绪指标
-   复杂推荐系统
-   语音转写作为核心依赖
-   首版全量长文本语义分析
-   Personal RAG 作为 MVP 前置依赖

## 2.4 后续版本预留

``` text
V1.1  今日往事
V1.2  关系计量器
V1.3  第三人称视角 + 分享海报
V1.4  30 / 100 / 365 天 AI 阶段摘要
```

Personal Memory / Personal RAG 可以作为后续 AI 工程增强方向，但不得阻塞
MVP。

------------------------------------------------------------------------

# 3. 开发环境与工作方式

## 3.1 工具职责

### 微信开发者工具

负责：

-   创建微信小程序项目
-   AppID / 小程序配置
-   编译与预览
-   微信 API 调试
-   真机预览
-   网络请求调试
-   上传与发布

### VSCode

负责：

-   主要代码编辑
-   Codex / Cursor
-   Git
-   前端代码
-   FastAPI 后端
-   测试
-   Docker
-   文档
-   API 调试辅助

### 项目目录关系

微信开发者工具创建的小程序项目作为：

``` text
nan-nan/miniprogram/
```

不要重新创建第二个小程序项目。

VSCode 打开整个：

``` text
nan-nan/
```

而不是只打开 `miniprogram/`。

------------------------------------------------------------------------

# 4. 总体技术架构

## 4.1 MVP 架构

``` text
┌──────────────────────────────┐
│       微信小程序              │
│  WXML / WXSS / JavaScript    │
└──────────────┬───────────────┘
               │ HTTPS / REST
               ↓
┌──────────────────────────────┐
│          FastAPI             │
│                              │
│  Auth / Diary / Upload       │
│  Reflection / Timeline       │
└───────┬───────────┬──────────┘
        │           │
        ↓           ↓
 PostgreSQL       Redis
        │
        ↓
┌──────────────────────────────┐
│        AI Application        │
│                              │
│ Safety → Prompt → LLM        │
│       → Output Guardrail     │
│       → Reflection Store     │
└──────────────┬───────────────┘
               │
               ↓
        LLM Provider
```

## 4.2 架构原则

### 前端

只负责：

-   UI
-   用户交互
-   本地草稿
-   API 调用
-   上传文件
-   展示状态

不负责：

-   AI API Key
-   AI Prompt 核心逻辑
-   用户权限判断
-   最终内容安全判断
-   数据归属判断

### 后端

负责：

-   身份认证
-   用户数据隔离
-   CRUD
-   内容安全
-   AI 调用
-   AI 输出校验
-   关键词 / 关键帧
-   删除闭环
-   日志
-   错误处理

------------------------------------------------------------------------

# 5. 技术栈

## 5.1 前端

``` text
微信小程序原生
JavaScript
WXML
WXSS
```

不引入大型 UI 框架作为 MVP 必选依赖。

## 5.2 后端

``` text
Python
FastAPI
SQLAlchemy
Pydantic
```

## 5.3 数据库

``` text
PostgreSQL
```

## 5.4 缓存 / 辅助状态

``` text
Redis
```

MVP Redis 用于：

-   API 限流
-   AI 请求防重复
-   临时任务状态
-   热点数据缓存（如需要）

不要把 Redis 当作唯一持久化数据库。

## 5.5 AI

采用 Provider Adapter：

``` text
AIService
   ↓
LLMProvider
   ├── Provider A
   └── Provider B
```

具体模型通过环境变量配置。

示例：

``` env
LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=
LLM_BASE_URL=
```

不得把密钥写入：

-   小程序代码
-   Git
-   README
-   前端环境文件
-   客户端请求参数

------------------------------------------------------------------------

# 6. 仓库目录结构

``` text
nan-nan/
│
├── miniprogram/
│   ├── pages/
│   │   ├── today/
│   │   ├── timeline/
│   │   ├── detail/
│   │   ├── profile/
│   │   └── ai-info/
│   │
│   ├── components/
│   │   ├── mood-slider/
│   │   ├── diary-card/
│   │   ├── image-uploader/
│   │   └── reflection-result/
│   │
│   ├── services/
│   │   ├── api.js
│   │   ├── auth.js
│   │   └── upload.js
│   │
│   ├── utils/
│   │   ├── request.js
│   │   ├── storage.js
│   │   └── format.js
│   │
│   ├── app.js
│   ├── app.json
│   ├── app.wxss
│   └── project.config.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── diaries.py
│   │   │   ├── reflections.py
│   │   │   ├── uploads.py
│   │   │   └── users.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   └── logging.py
│   │   │
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── diary.py
│   │   │   ├── reflection.py
│   │   │   └── marker.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── diary.py
│   │   │   ├── reflection.py
│   │   │   └── common.py
│   │   │
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── diary_service.py
│   │   │   ├── reflection_service.py
│   │   │   ├── marker_service.py
│   │   │   └── safety_service.py
│   │   │
│   │   ├── ai/
│   │   │   ├── client.py
│   │   │   ├── provider.py
│   │   │   ├── reflection.py
│   │   │   ├── guardrails.py
│   │   │   └── prompts/
│   │   │       └── reflection_v1.txt
│   │   │
│   │   └── workers/
│   │       └── reflection_worker.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── docs/
│   ├── PRD.md
│   ├── TECH_SPEC.md
│   ├── API_SPEC.md
│   ├── DATABASE.md
│   ├── AI_ARCHITECTURE.md
│   └── EVALUATION.md
│
├── scripts/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

------------------------------------------------------------------------

# 7. 前端页面规格

## 7.1 pages/today

核心页面：

``` text
日期 + 问候语
        ↓
情绪 / 能量控件
        ↓
大面积文字输入
        ↓
图片上传
        ↓
保存按钮
```

要求：

-   `content`: 1\~3000 字
-   `energyScore`: 0\~100
-   默认 `energyScore = 50`
-   最多 3 张图片
-   保存按钮防重复提交
-   有未保存内容离开时提示
-   网络异常时保留草稿
-   草稿恢复后允许继续编辑

## 7.2 情绪组件

数据：

``` text
energyScore: 0~100
moodLabel
color
```

情绪映射必须集中管理，不在多个页面重复硬编码。

建议配置：

``` js
[
  { min: 0,  max: 20, label: '低落' },
  { min: 21, max: 40, label: '平静' },
  { min: 41, max: 60, label: '明亮' },
  { min: 61, max: 80, label: '愉悦' },
  { min: 81, max: 100, label: '高亢' }
]
```

具体视觉颜色以 UI Design System 为准。

## 7.3 图片上传

要求：

-   最多 3 张
-   单张上传前压缩
-   上传状态可见
-   单张失败允许移除后继续保存文字
-   不因为图片失败导致整篇日记丢失
-   删除日记时清理图片关联
-   详情支持预览

## 7.4 pages/timeline

按 `createdAt DESC` 展示。

卡片至少包含：

-   日期
-   情绪
-   最多 80 字摘要
-   图片缩略图
-   关键帧标签

分页：

``` text
page=1
limit=20
```

或者使用 cursor pagination，但 MVP 优先保持 API 简单。

## 7.5 pages/detail

展示：

-   日期
-   情绪
-   原文
-   图片
-   AI 回响
-   关键词 / 关键帧
-   删除入口

删除：

``` text
点击删除
  ↓
二次确认
  ↓
DELETE API
  ↓
返回时间轴
  ↓
刷新列表
```

## 7.6 pages/profile

包含：

-   隐私政策
-   用户协议
-   AI 使用说明
-   数据删除说明
-   可选退出登录
-   账户基础信息

不要加入与 MVP 无关的功能入口。

## 7.7 pages/ai-info

解释：

-   AI 回响是什么
-   AI 会处理哪些数据
-   AI 不会做什么
-   AI 不提供心理诊断
-   AI 回响失败时会发生什么

------------------------------------------------------------------------

# 8. 微信登录与身份体系

## 8.1 原则

用户数据必须按用户身份隔离。

后端不得信任前端提交的：

``` text
userId
```

作为权限依据。

服务端必须从登录态中获得当前用户身份。

## 8.2 推荐流程

``` text
小程序
  ↓
wx.login()
  ↓
登录凭证
  ↓
POST /api/v1/auth/login
  ↓
后端验证微信身份
  ↓
创建 / 获取 User
  ↓
返回应用登录态
  ↓
小程序保存登录态
```

## 8.3 后端

用户身份统一通过依赖注入获取：

``` python
current_user = get_current_user()
```

业务接口不允许直接接收：

``` json
{
  "userId": "xxx"
}
```

然后拿它做权限判断。

------------------------------------------------------------------------

# 9. 数据库设计

## 9.1 UserProfile

对应 PRD 的 `UserProfile`。

核心字段：

``` text
id
wechat_open_id
created_at
last_active_at
ai_reflection_enabled
anniversary_reminder_enabled
third_person_unlocked
```

说明：

-   `wechat_open_id` 唯一
-   用户设置可以拆成独立字段，也可以使用 JSONB
-   MVP 不保存不必要的个人信息

## 9.2 DiaryEntry

核心字段：

``` text
id
user_id
content
energy_score
mood_label
privacy_status
ai_reflection_id
created_at
updated_at
deleted_at
```

图片不要把复杂对象直接塞入 `content`。

建议单独维护：

``` text
DiaryImage
```

字段：

``` text
id
diary_id
user_id
storage_key
url
sort_order
status
created_at
deleted_at
```

这样更利于：

-   删除
-   失败重试
-   图片状态管理
-   数据清理

## 9.3 AiReflection

对应 PRD：

``` text
id
diary_entry_id
user_id
status
content
model_name
prompt_version
safety_status
created_at
updated_at
```

状态：

``` text
pending
success
failed
blocked
```

安全状态：

``` text
safe
sensitive
blocked
```

建议额外增加工程字段：

``` text
attempt_count
error_code
latency_ms
token_usage
```

这些字段用于后续 AI 应用工程指标统计。

## 9.4 TimelineMarker

字段：

``` text
id
diary_entry_id
user_id
type
keyword
display_text
color
created_at
```

类型：

``` text
growth
relationship
place
achievement
custom
```

## 9.5 DiaryImage

这是技术实现新增的辅助实体，不改变 PRD 产品模型。

目的：

> 不让图片上传状态、存储信息和日记正文耦合。

## 9.6 索引

至少：

``` text
UserProfile.wechat_open_id UNIQUE

DiaryEntry(user_id, created_at DESC)

DiaryEntry(user_id, deleted_at)

AiReflection(diary_entry_id)

TimelineMarker(diary_entry_id)

DiaryImage(diary_id)
```

所有查询默认带当前用户条件。

------------------------------------------------------------------------

# 10. API 设计

统一前缀：

``` text
/api/v1
```

统一响应格式建议：

``` json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

错误：

``` json
{
  "code": "DIARY_NOT_FOUND",
  "message": "日记不存在",
  "data": null
}
```

## 10.1 登录

``` http
POST /api/v1/auth/login
```

请求：

``` json
{
  "code": "wechat-login-code"
}
```

响应：

``` json
{
  "code": 0,
  "message": "ok",
  "data": {
    "accessToken": "xxx",
    "user": {
      "id": "xxx"
    }
  }
}
```

## 10.2 创建日记

``` http
POST /api/v1/diaries
```

请求：

``` json
{
  "content": "今天……",
  "energyScore": 65,
  "moodLabel": "愉悦",
  "imageIds": []
}
```

处理：

``` text
鉴权
 ↓
参数校验
 ↓
内容安全
 ↓
创建 DiaryEntry
 ↓
创建 AiReflection(pending)
 ↓
触发异步 AI 任务
 ↓
关键词 / 关键帧处理
 ↓
返回 diaryId
```

重要：

> 创建日记 API 不等待 LLM 完成。

响应：

``` json
{
  "code": 0,
  "data": {
    "diaryId": "xxx",
    "reflectionStatus": "pending"
  }
}
```

## 10.3 日记列表

``` http
GET /api/v1/diaries?page=1&limit=20
```

只返回当前用户自己的数据。

默认：

``` text
createdAt DESC
```

响应：

``` json
{
  "code": 0,
  "data": {
    "list": [],
    "page": 1,
    "limit": 20,
    "hasMore": false
  }
}
```

## 10.4 日记详情

``` http
GET /api/v1/diaries/{diaryId}
```

返回：

``` json
{
  "diary": {},
  "images": [],
  "reflection": {},
  "markers": []
}
```

必须校验：

``` text
diary.user_id == current_user.id
```

## 10.5 删除日记

``` http
DELETE /api/v1/diaries/{diaryId}
```

删除前：

``` text
校验归属
```

删除：

``` text
DiaryEntry
  ├── DiaryImage
  ├── AiReflection
  └── TimelineMarker
```

图片对象存储也必须进入清理流程。

如果采用软删除：

``` text
deleted_at != null
```

业务查询默认排除已删除数据。

## 10.6 查询 AI 回响

``` http
GET /api/v1/diaries/{diaryId}/reflection
```

返回：

``` json
{
  "status": "pending|success|failed|blocked",
  "content": "..."
}
```

小程序可轮询。

------------------------------------------------------------------------

# 11. AI Reflection Pipeline

## 11.1 总流程

``` text
Diary
 ↓
Safety Check
 ↓
Prompt Builder
 ↓
LLM Provider
 ↓
Raw Output
 ↓
Structured Validation
 ↓
Safety Guardrail
 ↓
Persist Reflection
 ↓
Frontend Poll / Refresh
```

## 11.2 AI 状态机

``` text
pending
   │
   ↓
generating
   │
   ├────────────→ failed
   │
   └────────────→ blocked
   │
   ↓
success
```

数据库可以继续使用 PRD 规定的：

``` text
pending | success | failed | blocked
```

`generating` 可以作为内部任务状态，不强制持久化。

## 11.3 触发规则

MVP：

> 每篇日记默认只生成一次 AI 回响。

失败允许有限次数重试。

不得因为前端重复点击导致多个 AI 任务并发执行。

推荐使用：

``` text
reflection:{diary_id}
```

作为 Redis 分布式锁 / 幂等键。

------------------------------------------------------------------------

# 12. AI Prompt 规范

## 12.1 Prompt 必须版本化

例如：

``` text
reflection_v1
reflection_v2
```

文件：

``` text
backend/app/ai/prompts/reflection_v1.txt
```

数据库保存：

``` text
prompt_version = "reflection_v1"
```

## 12.2 AI 输出要求

必须：

-   30\~80 字
-   目标约 50 字
-   使用第二人称
-   温暖
-   具体
-   克制
-   只基于用户提供的信息
-   不编造事实
-   不做心理诊断
-   不给治疗建议
-   不输出建议清单
-   不主动引导聊天
-   不形成多轮 Chat

## 12.3 明确禁止

例如：

``` text
你一定会成功
加油，你可以的
```

这种空泛鼓励应判定为低质量。

禁止：

``` text
你可能患有……
```

禁止：

``` text
你今天一定很难过，因为……
```

如果用户没有提供对应事实，不允许推断成事实。

------------------------------------------------------------------------

# 13. AI Structured Output

AI 服务内部优先要求结构化结果：

``` json
{
  "reflection": "今天的这一页……",
  "keywords": ["毕业", "朋友"],
  "tone": "warm"
}
```

后端 Pydantic 校验：

``` text
reflection: string
keywords: string[]
tone: string
```

最终保存到 `AiReflection.content` 的是经过验证的回响正文。

如果模型无法输出合法结构：

``` text
→ 不直接展示原始模型结果
→ 标记 failed
→ 使用兜底文案
```

------------------------------------------------------------------------

# 14. AI Guardrails

## 14.1 输入安全

日记进入 AI 前：

``` text
用户输入
 ↓
文本安全检测
 ↓
通过 → AI
不通过 → 阻断 / 提示用户修改
```

## 14.2 输出安全

``` text
LLM
 ↓
长度检查
 ↓
格式检查
 ↓
敏感内容检查
 ↓
心理诊断规则检查
 ↓
事实幻觉基础检查
 ↓
通过 → success
不通过 → blocked / fallback
```

## 14.3 兜底文案

固定：

> 今天的这一页已经被好好保存。AI
> 暂时没有写出回信，但这些文字会在未来某天重新陪你见到此刻的自己。

## 14.4 AI 失败不影响日记

这是系统级硬约束：

``` text
AI Failure != Diary Failure
```

------------------------------------------------------------------------

# 15. 关键词与关键帧

MVP 使用轻量规则词库，不引入高成本语义模型作为前置依赖。

## 15.1 词库

### 成长

``` text
学会
掌握
第一次
完成
通过
```

### 关系

``` text
认识
在一起
分开
重逢
纪念日
```

### 地点

``` text
去了
旅行
搬家
回到
离开
```

### 成就

``` text
拿到
获奖
录取
入职
毕业
```

## 15.2 规则

-   按出现顺序处理
-   每篇最多 3 个标签
-   无命中不强行生成
-   关键词词库集中配置
-   类型、颜色、展示文本集中配置

------------------------------------------------------------------------

# 16. 本地草稿

## 16.1 目标

弱网、误返回、程序异常时保护用户输入。

草稿属于客户端本地数据，不作为服务端正式日记。

## 16.2 保存内容

建议：

``` json
{
  "content": "",
  "energyScore": 50,
  "moodLabel": "平静",
  "localImages": [],
  "updatedAt": 0
}
```

## 16.3 保存时机

不要每次键盘输入都写入高频存储。

建议：

``` text
输入变化
 ↓
debounce
 ↓
本地保存
```

页面隐藏 / 退出前再次保存。

## 16.4 恢复

进入今日页：

``` text
存在草稿
 ↓
提示“发现未完成记录”
 ↓
继续编辑 / 放弃草稿
```

------------------------------------------------------------------------

# 17. 图片上传架构

推荐：

``` text
小程序
 ↓
选择图片
 ↓
压缩
 ↓
上传接口
 ↓
对象存储
 ↓
返回 imageId
 ↓
创建日记时提交 imageIds
```

不要把图片 Base64 直接放进日记 API。

## 上传状态

``` text
pending
uploading
success
failed
```

## 删除日记

必须形成：

``` text
Diary
 ↓
Images
 ↓
Object Storage
```

的完整清理链路。

------------------------------------------------------------------------

# 18. 安全与隐私

## 18.1 数据隔离

所有日记查询：

``` sql
WHERE user_id = current_user.id
```

禁止：

``` text
只根据 diary_id 查询
```

然后直接返回。

## 18.2 删除

用户删除自己的记录时：

``` text
正文
图片关联
对象存储图片
AI 回响
关键词
关键帧
```

都进入删除流程。

## 18.3 前端不保存敏感凭据

禁止：

``` text
LLM_API_KEY
DATABASE_URL
微信 AppSecret
```

进入小程序代码。

## 18.4 分享

MVP 如果实现分享：

-   必须用户主动触发
-   默认脱敏
-   不展示完整原文
-   不展示精确地点
-   不暴露图片 EXIF
-   不自动分享
-   分享前允许预览

------------------------------------------------------------------------

# 19. 日志与可观测性

为了让项目具备 AI 应用工程属性，后端从 MVP 开始记录：

## API 指标

``` text
request_count
error_count
latency_ms
status_code
```

## AI 指标

``` text
model_name
prompt_version
request_id
diary_id
latency_ms
attempt_count
token_usage
status
error_code
```

注意：

> 日志中不要直接打印用户完整日记正文。

推荐：

``` text
request_id
user_id
diary_id
event
latency
status
```

而不是：

``` text
print(diary.content)
```

------------------------------------------------------------------------

# 20. AI 工程指标

后续简历需要真实数据，因此从代码层预留统计能力。

重点指标：

``` text
AI Success Rate
AI Failure Rate
P95 AI Latency
Average AI Latency
Retry Rate
Token Usage
API Error Rate
Diary Save Success Rate
```

后续可在 `EVALUATION.md` 中加入：

``` text
100 条测试日记
 ↓
Baseline Prompt
 ↓
Optimized Prompt
 ↓
比较：
- Relevance
- Specificity
- Empathy
- Hallucination
- Safety
```

不得提前编造指标。

------------------------------------------------------------------------

# 21. 错误码

建议统一：

``` text
AUTH_REQUIRED
AUTH_INVALID
PERMISSION_DENIED

DIARY_NOT_FOUND
DIARY_CONTENT_EMPTY
DIARY_CONTENT_TOO_LONG
DIARY_SAFETY_BLOCKED
DIARY_SAVE_FAILED

IMAGE_UPLOAD_FAILED
IMAGE_LIMIT_EXCEEDED
IMAGE_SAFETY_BLOCKED

REFLECTION_NOT_FOUND
REFLECTION_GENERATION_FAILED
REFLECTION_BLOCKED
REFLECTION_RETRY_LIMIT

RATE_LIMITED
INTERNAL_ERROR
```

前端根据 `code` 做用户可理解的提示。

不要直接把 Python Exception / 数据库异常返回给用户。

------------------------------------------------------------------------

# 22. 前端 API 层规范

所有网络请求统一经过：

``` text
miniprogram/services/api.js
```

底层请求统一经过：

``` text
miniprogram/utils/request.js
```

页面不得大量直接调用：

``` javascript
wx.request(...)
```

统一：

``` javascript
api.createDiary(...)
api.getDiaryList(...)
api.getDiaryDetail(...)
api.getReflection(...)
api.deleteDiary(...)
```

这样便于：

-   登录态注入
-   错误处理
-   重试
-   日志
-   API 版本升级

------------------------------------------------------------------------

# 23. UI Design System

UI 设计稿作为视觉基准。

整体关键词：

``` text
安静
私密
柔和
暖米色
旧纸张感
温和棕色
低饱和情绪色
```

## 23.1 基础色

当前设计基准：

``` text
页面背景：#FBF7F0
主文字：#3D2C1B
辅助文字：#8B7A6B
```

其余颜色统一建立 Design Tokens。

## 23.2 情绪色

情绪颜色必须集中配置。

不要在：

``` text
today
timeline
detail
```

三个页面分别写颜色。

## 23.3 组件

优先抽取：

``` text
MoodSlider
DiaryCard
ImageUploader
ReflectionResult
EmptyState
LoadingState
ErrorState
```

## 23.4 动效

原则：

> 不为了视觉效果堆叠复杂动效。

优先保证：

-   点击反馈
-   loading
-   AI 生成状态
-   页面切换
-   图片上传状态

------------------------------------------------------------------------

# 24. AI 回响页面状态

必须实现：

### pending

``` text
正在生成回响……
```

### success

显示 AI 回信。

### failed

显示兜底文案 + 有限重试入口。

### blocked

显示安全兜底，不展示模型原始内容。

### empty

例如没有历史记录：

``` text
还没有日记
去写下第一篇吧
```

------------------------------------------------------------------------

# 25. 测试策略

## 25.1 后端单元测试

至少测试：

-   Diary 创建
-   Diary 查询
-   Diary 删除
-   用户权限隔离
-   字数校验
-   energyScore 校验
-   marker 提取
-   AI 输出校验
-   AI 状态转换
-   错误码

## 25.2 AI 测试

准备固定测试集：

``` text
正常日记
短文本
3000 字边界
敏感内容
空内容
无关键帧
多个关键帧
AI 返回异常格式
AI 超时
AI 输出过长
AI 输出诊断词
```

## 25.3 小程序测试

必须覆盖：

``` text
首次进入
微信登录
今日记录
情绪默认值
情绪修改
文字输入
图片上传
图片失败
保存
重复点击保存
草稿恢复
弱网
AI pending
AI success
AI failed
详情
删除
时间轴分页
空状态
隐私页
```

## 25.4 核心验收

### 记录

-   能输入文字
-   默认情绪可直接保存
-   最多 3 张图片
-   未保存退出有提示
-   草稿可以恢复

### AI

-   保存成功后触发
-   AI 不阻塞保存
-   回响符合 30\~80 字要求
-   AI 失败有兜底
-   敏感内容不产生危险回应

### 时间轴

-   倒序
-   摘要
-   情绪
-   图片
-   关键帧
-   点击详情
-   删除同步

### 隐私

-   只能看到自己的数据
-   能删除自己的记录
-   无公开社区
-   分享默认脱敏

------------------------------------------------------------------------

# 26. Docker 开发环境

推荐：

``` text
docker-compose.yml
```

包含：

``` text
postgres
redis
backend
```

小程序不进入 Docker。

开发：

``` text
微信开发者工具
      ↓
localhost / 局域网
      ↓
FastAPI
      ↓
PostgreSQL + Redis
```

生产环境再单独配置域名与 HTTPS。

------------------------------------------------------------------------

# 27. 环境变量

根目录：

``` text
.env.example
```

后端：

``` env
APP_ENV=development

DATABASE_URL=
REDIS_URL=

WECHAT_APP_ID=
WECHAT_APP_SECRET=

LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=
LLM_BASE_URL=

STORAGE_ENDPOINT=
STORAGE_BUCKET=
STORAGE_ACCESS_KEY=
STORAGE_SECRET_KEY=
```

原则：

``` text
.env
```

永远加入：

``` text
.gitignore
```

只提交：

``` text
.env.example
```

------------------------------------------------------------------------

# 28. Git 工作流

## 28.1 分支

``` text
main
└── develop
    ├── feature/miniprogram-init
    ├── feature/auth
    ├── feature/diary
    ├── feature/image-upload
    ├── feature/reflection
    ├── feature/timeline
    ├── feature/detail
    └── feature/privacy
```

## 28.2 Commit

建议：

``` text
feat: add diary creation api
feat: implement mood slider
feat: add reflection pipeline
fix: prevent duplicate diary submission
fix: handle reflection timeout
refactor: extract diary service
test: add reflection guardrail tests
docs: update api specification
chore: initialize project
```

## 28.3 Codex / Cursor Git 规则

AI 编程工具：

-   可以修改代码
-   可以运行测试
-   可以检查 diff
-   不允许未经用户确认直接 push
-   不允许删除 Git 历史
-   不允许执行 destructive Git 操作
-   不允许自行修改产品需求
-   不允许为了通过测试删除测试

每完成一个功能：

``` text
实现
 ↓
测试
 ↓
git diff
 ↓
人工确认
 ↓
commit
```

------------------------------------------------------------------------

# 29. Codex / Cursor 开发规则

将以下规则作为项目级约束：

``` text
1. 先阅读 PRD.md 和 TECH_SPEC.md，再修改代码。

2. PRD 是产品需求唯一基准；TECH_SPEC 是技术实现基准。

3. 不允许自行增加 MVP 功能。

4. 不允许删除已有功能来规避问题。

5. 不允许修改 UI 设计方向。

6. 小程序使用原生 WXML / WXSS / JavaScript。

7. 不在前端保存 AI API Key、AppSecret、数据库密码。

8. 所有用户数据 API 必须进行用户身份校验。

9. 不信任前端提交的 userId。

10. 日记保存与 AI 回响解耦。
    AI 失败不能导致日记保存失败。

11. 所有 AI 输出必须经过后端校验。

12. AI Prompt 必须版本化。

13. 不允许把用户完整日记打印到日志。

14. 修改 API 时同步更新 API_SPEC.md。

15. 修改数据库模型时同步更新 DATABASE.md。

16. 新增环境变量时同步更新 .env.example。

17. 每完成一个 Task 必须运行相关测试。

18. 未经用户确认不得 git push。

19. 不执行 reset --hard、clean -fd、force push 等破坏性 Git 操作。

20. 如果 PRD 与代码现状冲突，先报告冲突，再实施修改。

21. 如果需求存在技术歧义，不要擅自创造产品行为。

22. 优先选择简单、可维护的 MVP 实现。

23. 不为了“AI 工程感”提前引入复杂 Agent / RAG / MQ。

24. 后续 Memory / Personal RAG 应作为独立版本演进。

25. 所有代码需要考虑错误处理、空状态、loading 和弱网场景。
```

------------------------------------------------------------------------

# 30. 开发任务路线

## Phase 0：工程初始化

``` text
T001 创建 Git 仓库结构
T002 初始化 miniprogram
T003 初始化 FastAPI
T004 PostgreSQL
T005 Redis
T006 Docker Compose
T007 环境变量
T008 基础日志
```

验收：

``` text
前端可以启动
后端 /health 可用
数据库可连接
Redis 可连接
```

------------------------------------------------------------------------

## Phase 1：微信登录

``` text
T009 小程序登录
T010 后端身份验证
T011 UserProfile
T012 登录态
T013 current_user dependency
```

验收：

``` text
用户登录
→ 后端识别用户
→ 用户身份稳定
```

------------------------------------------------------------------------

## Phase 2：日记核心链路

``` text
T014 Diary Model
T015 Diary Schema
T016 POST /diaries
T017 GET /diaries
T018 GET /diaries/{id}
T019 DELETE /diaries/{id}
```

验收：

``` text
创建
→ 列表
→ 详情
→ 删除
```

------------------------------------------------------------------------

## Phase 3：小程序今日页

``` text
T020 今日页
T021 MoodSlider
T022 Textarea
T023 字数统计
T024 保存状态
T025 未保存退出
T026 草稿
```

------------------------------------------------------------------------

## Phase 4：图片

``` text
T027 ImageUploader
T028 图片压缩
T029 上传 API
T030 上传失败处理
T031 图片预览
T032 删除清理
```

------------------------------------------------------------------------

## Phase 5：AI Reflection

``` text
T033 Reflection Model
T034 LLM Provider
T035 Prompt v1
T036 AI Pipeline
T037 Output Schema
T038 Guardrails
T039 Reflection Status
T040 Retry
T041 AI Result UI
```

这是整个项目最重要的 AI 工程阶段。

------------------------------------------------------------------------

## Phase 6：关键词 / 关键帧

``` text
T042 Keyword Dictionary
T043 Marker Extraction
T044 TimelineMarker
T045 Timeline UI
```

------------------------------------------------------------------------

## Phase 7：时间轴

``` text
T046 Timeline API
T047 Pagination
T048 DiaryCard
T049 Empty State
T050 Detail Navigation
```

------------------------------------------------------------------------

## Phase 8：我的 / 隐私

``` text
T051 Profile
T052 AI Info
T053 Privacy
T054 Delete Data
T055 Logout（如启用）
```

------------------------------------------------------------------------

## Phase 9：工程质量

``` text
T056 API Tests
T057 Permission Tests
T058 AI Guardrail Tests
T059 Error Handling
T060 Logging
T061 Rate Limit
T062 Duplicate Submission Protection
```

------------------------------------------------------------------------

## Phase 10：上线准备

``` text
T063 Production Environment
T064 HTTPS
T065 小程序合法域名
T066 隐私政策
T067 用户协议
T068 数据删除说明
T069 真机测试
T070 弱网测试
T071 最终回归
```

------------------------------------------------------------------------

# 31. AI 应用工程增强路线

详细工程计划、质量门禁与任务拆分见
[`AI_ENHANCEMENT_ROADMAP.md`](./AI_ENHANCEMENT_ROADMAP.md)。

MVP 完成后，再按以下顺序增强：

## V1.1

``` text
历史上的今天
```

## V1.2

``` text
Memory Extraction
```

将日记抽取成：

``` text
人物
事件
地点
成就
关系
生活阶段
```

但不要改变原始日记。

## V1.3

``` text
Personal Memory Retrieval
```

当前日记：

``` text
Query
 ↓
历史记忆检索
 ↓
Context Builder
 ↓
LLM
 ↓
个性化回响
```

## V1.4

``` text
Personal Memory RAG
```

此阶段再考虑：

``` text
Embedding
Vector Store
Hybrid Retrieval
Rerank
```

不要为了简历而在 MVP 阶段强行引入。

------------------------------------------------------------------------

# 32. 简历指标预留

开发过程中不要虚构数据。

实际运行后统计：

``` text
Diary Save Success Rate
AI Success Rate
AI P95 Latency
Average AI Latency
AI Retry Rate
Token Usage
API Error Rate
```

如果进行 AI Evaluation，再统计：

``` text
Relevance
Specificity
Empathy
Hallucination
Safety
```

最终简历只填写真实测量结果。

------------------------------------------------------------------------

# 33. MVP 完成定义

只有同时满足以下条件，才能认为 MVP 完成：

``` text
[ ] 微信登录可用
[ ] 今日页可记录
[ ] 情绪可选择
[ ] 文字可保存
[ ] 最多 3 张图片
[ ] 草稿可恢复
[ ] 日记保存与 AI 解耦
[ ] AI 回响可生成
[ ] AI 失败有兜底
[ ] AI 输出经过校验
[ ] 关键词 / 关键帧可用
[ ] 时间轴可分页
[ ] 详情页可用
[ ] 删除闭环完成
[ ] 我的页面完成
[ ] 隐私说明可访问
[ ] 用户数据隔离
[ ] 弱网场景可处理
[ ] 重复提交可处理
[ ] 后端测试通过
[ ] 小程序真机测试通过
[ ] Git 历史清晰
[ ] 无密钥泄露
```

------------------------------------------------------------------------

# 34. 第一阶段立即执行任务

当前不要直接让 Codex 一口气实现全部功能。

第一轮只执行：

``` text
Task 001
项目目录初始化

Task 002
FastAPI /health

Task 003
PostgreSQL + SQLAlchemy

Task 004
Redis

Task 005
小程序 app.json / app.js / app.wxss

Task 006
基础 Design Tokens

Task 007
Git 初始化
```

完成后再进入微信登录。

------------------------------------------------------------------------

# 35. 给 Codex / Cursor 的项目级启动指令

将以下内容作为第一条项目提示词：

``` text
你现在参与开发微信小程序「喃喃」。

这是一个准备作为 AI 应用工程项目写入简历的真实项目。

请先完整阅读：
1. docs/PRD.md
2. docs/TECH_SPEC.md

然后严格按照 TECH_SPEC.md 的 Task 顺序开发。

重要规则：

- 不要一次实现整个项目。
- 当前只实现用户明确要求的 Task。
- 不自行增加产品功能。
- 不自行改变 UI。
- 不在小程序端调用 LLM。
- 不在代码中写死任何 Secret。
- 所有用户数据必须经过身份校验。
- AI 失败不能影响日记保存。
- 所有 AI 输出必须经过 Guardrail。
- Prompt 必须版本化。
- 不要把完整用户日记打印到日志。
- 每完成一个 Task，先运行测试。
- 修改数据库同步更新 docs/DATABASE.md。
- 修改 API 同步更新 docs/API_SPEC.md。
- 新增环境变量同步更新 .env.example。
- 不要自动 git push。
- 不执行破坏性 Git 操作。

开发原则：

Problem → Design → Implementation → Test → Result

优先保证：
1. 正确性
2. 数据安全
3. 可维护性
4. 用户体验
5. AI 工程能力
6. 性能优化

不要为了体现 AI 工程能力，在 MVP 阶段提前引入不必要的 Agent、RAG、MQ 或复杂基础设施。

现在先执行 Phase 0。
完成后停止并报告：
- 修改了哪些文件
- 完成了哪些功能
- 如何验证
- 测试结果
- 下一步 Task
```

------------------------------------------------------------------------

# 36. 文档维护规则

以下文档必须和代码同步：

``` text
PRD.md
    产品需求

TECH_SPEC.md
    技术架构与开发规范

API_SPEC.md
    API Contract

DATABASE.md
    数据库 Schema / Migration

AI_ARCHITECTURE.md
    AI Pipeline / Prompt / Guardrail

EVALUATION.md
    AI Evaluation / Benchmark
```

不要让代码成为唯一的"真实文档"。

------------------------------------------------------------------------

# 37. 最终工程目标

MVP 阶段：

``` text
微信小程序
    +
FastAPI
    +
PostgreSQL
    +
Redis
    +
LLM
    +
安全校验
    +
异步 AI Pipeline
```

后续：

``` text
Memory
    ↓
Personal Retrieval
    ↓
Personal RAG
    ↓
阶段性人生回顾
```

最终形成：

> 一个真正具备 AI 应用工程特征的个人 AI
> Journal，而不是简单的"调用大模型生成一段文字"的小程序。

核心工程闭环：

``` text
用户输入
   ↓
数据安全
   ↓
结构化存储
   ↓
异步 AI Pipeline
   ↓
LLM
   ↓
Structured Output
   ↓
Guardrail
   ↓
持久化
   ↓
前端展示
   ↓
历史数据沉淀
   ↓
后续 Personal Memory
```
