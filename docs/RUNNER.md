# 可选：地域测活 Runner

> **非必须。** 云端 `collect.yml` 独立日更 `live.m3u`。  
> 仅当你需要 `live_verified.m3u`（某出口实测子集）时再部署。

## 网络口径（示例：武汉联通）

- 测活出口 = runner 所在网络
- IPv4 无公网（NAT）也可：只需**出站**访问 GitHub 与流媒体
- **live_verified ≠ 全国通用**

## 推荐镜像：oasisic-runner

- 仓库：https://github.com/Hawaiine/oasisic-runner  
- **一键镜像**：`ghcr.io/hawaiine/oasisic-runner:latest`  
- Docker Hub（可选双推）：`barryallen26/oasisic-runner:latest`  
- **不要**再使用 `minimal-runner` / `minimal-runner-to-del`

### 一键安装

```bash
export ACCESS_TOKEN=ghp_你的PAT
curl -fsSL https://raw.githubusercontent.com/Hawaiine/oasisic-runner/main/install.sh | bash
```

### docker run

```bash
docker run -d --restart unless-stopped --name oasisic-runner \
  -e REPO_URL=https://github.com/Hawaiine/Oasisic-IPTV \
  -e ACCESS_TOKEN=ghp_your_token \
  -e RUNNER_NAME=oasisic-iptv-wuhan \
  -e RUNNER_LABELS=self-hosted,iptv,region-wuhan \
  ghcr.io/hawaiine/oasisic-runner:latest
```

| 标签 | 用途 |
|------|------|
| `self-hosted` | GHA 约定 |
| `iptv` | 匹配 `probe.yml` |
| `region-wuhan` | 软标签 |

### 启用测活

1. Settings → Actions → Runners 显示 Idle  
2. Actions → **probe** → Enable → Run workflow  
3. 成功后更新 `output/live_verified.m3u`

### 无 Runner

保持 `probe` workflow **Disable**；主订阅只用 `live.m3u`。

## 安全

- 非 root、无 DinD  
- Token 仅本机环境变量  
- 定期 `docker pull` 更新镜像  
