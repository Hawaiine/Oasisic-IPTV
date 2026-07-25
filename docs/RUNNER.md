# Self-hosted Runner 部署

## 方案

使用 [Hawaiine/minimal-runner](https://github.com/Hawaiine/minimal-runner) Docker 镜像部署自建 runner。

## 部署命令

```bash
docker run -d --restart unless-stopped --name oasisic-iptv-runner \
  -e REPO_URL=https://github.com/Hawaiine/Oasisic-IPTV \
  -e ACCESS_TOKEN=ghp_xxx \
  -e RUNNER_NAME=oasisic-iptv-wuhan \
  -e RUNNER_LABELS=self-hosted,iptv,region-wuhan \
  barryallen26/minimal-runner:latest
```

## 环境要求

- **网络**：武汉联通（AS4837），仅需出站连接至 `github.com`
- **IPv4**：无公网 IP 亦可运行（只需出站）
- **IPv6**：有公网 IPv6，可提供额外测活能力

## 安全说明

- 社区镜像 `myoung34/docker-github-actions-runner` 为基础
- 定期更新镜像版本
- 限制 runner 网络访问
- 勿使用 root 运行