# 可选：地域测活 Runner

> **非必须。** 云端 `collect.yml` 独立日更 `live.m3u`。  
> 仅当你需要 `live_verified.m3u`（某出口实测子集）时再部署。

## 网络口径（示例：武汉联通）

- 测活出口 = runner 所在网络（文档请写真实出口）
- IPv4 无公网（NAT）也可：只需**出站**访问 GitHub 与流媒体
- IPv6 有公网可增强部分源测活
- **live_verified ≠ 全国通用**

## 推荐镜像：oasisic-runner

新项目（自研，推 Docker Hub）：

- 仓库：https://github.com/Hawaiine/oasisic-runner  
- 镜像：`barryallen26/oasisic-runner:latest`  
- **不要**再使用已弃用的 `minimal-runner` / `minimal-runner-to-del`

### 一键运行

```bash
docker run -d --restart unless-stopped --name oasisic-runner \
  -e REPO_URL=https://github.com/Hawaiine/Oasisic-IPTV \
  -e ACCESS_TOKEN=ghp_your_token \
  -e RUNNER_NAME=oasisic-iptv-wuhan \
  -e RUNNER_LABELS=self-hosted,iptv,region-wuhan \
  barryallen26/oasisic-runner:latest
```

标签说明：

| 标签 | 用途 |
|------|------|
| `self-hosted` | GHA 约定 |
| `iptv` | 匹配 `probe.yml` 的 `runs-on` |
| `region-wuhan` | 软标签，区分出口 |

### Token

Classic PAT 勾选 `repo`，或 Fine-grained 对目标仓 **Administration: Read and write**。  
Token 只放本机环境变量 / `.env`，禁止提交 git。

### 验证

仓库 **Settings → Actions → Runners** 显示 Idle 后：

1. 在 GitHub 将 workflow **probe** 设为 Enable（若曾禁用）  
2. Actions → **probe** → Run workflow  
3. 成功后应出现/更新 `output/live_verified.m3u`

## 无 Runner 时

- **无需部署** — 主订阅用 `live.m3u` 即可  
- 保持 `probe` workflow **Disable**，避免无机器时 job 排队  
- 本地临时测活：

```bash
PROBE_ENABLED=true PROBE_CONCURRENCY=5 python scripts/collect.py
```

## 安全

- 镜像非 root、无 Docker-in-Docker  
- 限制 runner 出站范围（可选防火墙）  
- 定期更新镜像版本  
