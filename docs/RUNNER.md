# Self-hosted Runner 部署

## 网络口径

- **测活出口**：湖北武汉联通（AS4837）
- **IPv4**：无公网（NAT），仅需**出站**访问 GitHub，无需入站映射
- **IPv6**：有公网
- **live_verified** = 武汉联通出口视角，**禁止**写成全国通用

## 方案

使用 [Hawaiine/minimal-runner](https://github.com/Hawaiine/minimal-runner) Docker 镜像部署自建 runner。

## 部署命令

```bash
docker run -d --restart unless-stopped --name oasisic-iptv-runner \
  -e REPO_URL=https://github.com/Hawaiine/Oasisic-IPTV \
  -e ACCESS_TOKEN=*** \
  -e RUNNER_NAME=oasisic-iptv-wuhan \
  -e RUNNER_LABELS=self-hosted,iptv,region-wuhan \
  barryallen26/minimal-runner:latest
```

## 环境要求

- **网络**：武汉联通（AS4837），仅需出站连接至 `github.com`，无需配置入站端口映射
- **IPv4**：无公网 IP 亦可运行（只需出站 HTTPS）
- **IPv6**：有公网 IPv6，可提供额外测活能力

## 离线说明

Runner 离线时 probe job 会失败/queued，不影响 collect 已推送的输出内容。
collect job 任何时候都在 GitHub 云端独立运行，不依赖 runner 在线。

## 安全说明

- 社区镜像 `myoung34/docker-github-actions-runner` 为基础
- 定期更新镜像版本
- 限制 runner 网络访问
- 勿使用 root 运行