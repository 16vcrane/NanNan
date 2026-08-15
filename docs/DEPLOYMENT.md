# 喃喃生产部署

## 1. 前置条件

- 已备案并可解析的 API 域名，例如 `api.example.com`
- 公网服务器开放 TCP `80/443` 和 UDP `443`
- 微信小程序 AppID、AppSecret
- 私有 S3 兼容对象存储
- 已开通的模型 API
- Docker Engine 与 Docker Compose

生产环境不会接受默认密钥、HTTP 地址或本地文件存储。缺少必要配置时后端会在启动阶段退出。

## 2. 配置与启动

```powershell
Copy-Item .env.production.example .env.production
# 填写 .env.production 中所有空值和示例密码
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Caddy 根据 `PUBLIC_DOMAIN` 自动申请和续期 TLS 证书。PostgreSQL、Redis 和 FastAPI
只在 Docker 内部网络开放；公网只暴露 Caddy 的 `80/443`。

验证：

```powershell
curl.exe -i https://api.example.com/api/v1/health
```

响应必须为 `200`，数据库与 Redis 均为 `ok`，并包含 `Strict-Transport-Security`、
`X-Content-Type-Options` 和 `X-Request-ID`。

## 3. 小程序合法域名

在微信公众平台的“开发管理 -> 开发设置 -> 服务器域名”配置：

| 类型 | 域名 |
| --- | --- |
| request 合法域名 | `https://api.example.com` |
| uploadFile 合法域名 | `https://api.example.com` |
| downloadFile 合法域名 | `https://api.example.com` |

域名必须完成备案，使用受信任 TLS 证书，不得填写路径、端口或 IP 地址。当前版本不需要
socket 合法域名。配置完成后，将同一地址写入
`miniprogram/config/environment.js` 的 `PRODUCTION_API_BASE_URL`，保留 `/api/v1`。

## 4. 隐私与数据删除

发布前在微信公众平台同步声明以下能力及用途：

- `wx.login`：建立用户私密账户；
- `wx.chooseMedia`：由用户主动选择日记图片；
- 本地缓存和保存文件：保存登录态、未提交草稿及图片预览。

小程序内的“AI 使用说明”“隐私政策”“用户协议”和“数据管理”必须可访问。数据管理页提供：

- 删除单篇日记；
- 退出登录但保留服务端数据；
- 永久删除账户、日记、图片、AI 回响与关键帧。

运营侧收到删除请求时，应引导用户使用小程序内自助入口，不应要求用户通过非必要渠道
提交更多身份资料。

## 5. 备份与回滚

上线前备份 PostgreSQL，并确认对象存储启用了生命周期与备份策略。应用回滚只回滚镜像，
不得直接回退已执行的数据库迁移。先在备份数据上验证兼容性，再决定是否执行独立的降级迁移。

日志不得写入微信 code、access token、AppSecret、日记正文或图片内容。
