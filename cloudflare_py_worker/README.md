# Cloudflare Python Worker (Beta) 适配

该目录提供一个将原 FastAPI 后端最小迁移到 *Cloudflare Python Workers (Beta)* 的示例。此实现只为演示：不保证生产稳定性。

## 重要限制 / 风险
| 项目 | 说明 | 建议 |
|------|------|------|
| 运行时 Beta | `python_workers` flag 可能更名或语义变化 | 部署前查看最新官方文档 |
| 内存会话不持久 | `SESSIONS` 为进程/isolated VM 级内存，扩缩容或冷启动会丢 | 使用 Durable Objects / KV / D1 持久化 |
| 第三方库体积 | 不适合引入庞大生态（如完整 LangChain） | 保持精简，直调 HTTP API |
| 并发一致性 | 多实例间不共享状态 | Durable Object 维护会话房间 |
| 冷启动 | 首次执行需加载 Python/Stdlib | 减少依赖、关闭调试日志 |
| 安全 | 无鉴权、LLM 输出直接返回 | 添加鉴权 header + 速率限制 + 输出过滤 |

## 文件
- `wrangler.toml`：Worker 配置（启用 `python_workers` 兼容标志，环境变量）
- `worker.py`：核心逻辑（路由匹配、OpenRouter 调用、diff 计算）

## 环境变量
在 `wrangler.toml` 里声明普通变量，在部署前用 Secret 存储敏感值：

```bash
npx wrangler secret put OPENROUTER_API_KEY
```

可根据需要调整：`MODEL`, `GENERATION_MAX_TOKENS`, `TEMPERATURE`, `OPENROUTER_BASE_URL`。

## 本地开发 & 发布
确保安装新版 Wrangler（支持 Python Beta）。

```bash
# 进入目录
cd cloudflare_py_worker

# 本地开发（Beta：可能仅模拟 JS 层；请关注官方更新）
npx wrangler dev

# 发布
npx wrangler publish
```

发布成功后会得到形如：
```
https://vibe-coding-python-worker.<subdomain>.workers.dev
```
用它替换前端的 `API_BASE`（或浏览器中设置 localStorage）：
```js
localStorage.setItem('vc_api_base', 'https://vibe-coding-python-worker.<subdomain>.workers.dev');
```
刷新前端页面即可。

## 路由对照
| 原 FastAPI | Worker Python | 说明 |
|------------|---------------|------|
| POST /sessions | 同 | 创建会话，返回 `session_id` |
| POST /sessions/{id}/messages | 同 | 生成新代码与 diff |
| GET /sessions/{id}/code | 同 | 取当前代码 |
| GET /health | 同 | 健康检查 |

## 逻辑简述
1. `on_fetch` -> `handle_request` 解析路径
2. `/sessions` 创建：生成 UUID，写入 `SESSIONS`
3. `/sessions/{id}/messages`：
   - 取旧代码
   - 组装 Prompt （System + User 模板）
   - 调用 OpenRouter `/chat/completions`
   - 正则抽取 fenced code block
   - 生成 unified diff（`difflib`）
   - 返回 JSON
4. `/sessions/{id}/code`：返回当前代码字符串

## 与原项目的差异
| 方面 | FastAPI 版本 | Python Worker 版本 |
|------|--------------|--------------------|
| 框架 | FastAPI + Uvicorn | 纯函数式 on_fetch | 
| 状态 | 进程内存 | 边缘 isolate 内存（更易丢失） |
| 多区域 | 取决于部署位置 | Cloudflare 边缘自动调度 |
| 模型回退 | 原版支持 fallback 列表 | 当前示例未做（可扩展迭代 models） |
| 错误处理 | HTTPException | 手动构造 Response JSON |

## 扩展点建议
1. **模型回退**：仿造原 `iter_models` 逻辑，循环多模型。
2. **持久化**：用 KV (键: `session:<id>`) 存 JSON；或 Durable Object 做串行化操作。
3. **鉴权**：增加 Header 校验（如 `X-API-Key`），无则 401。
4. **速率限制**：结合 Durable Object 计数或 Turnstile。
5. **日志/监控**：发送 `fetch` 到自建收集端点或使用 Logpush。
6. **安全**：在前端 iframe 加 `sandbox` 属性，限制脚本权限。

## 轻量回退模型（示意伪码）
```python
for model_name in [env.MODEL, *filter(None, getattr(env, 'FALLBACK_MODELS', '').split(','))]:
    try:
        # set payload['model'] = model_name; call
        ...
        return content, code
    except PermissionError:
        last_exc = e
        continue
if last_exc: raise last_exc
```

## 生产前 Checklist
- [ ] 确认 Python Workers 计费/限制是否满足
- [ ] 添加鉴权或速率限制
- [ ] 将会话存储迁移到 KV / DO
- [ ] 增加模型回退与错误日志
- [ ] iframe sandbox 化 & 输出审计

---
如需我继续：
- 增加 KV 版本示例
- 加入模型回退逻辑
- 加 Durable Object 代码骨架

告诉我下一步想要哪一个，我可以继续补充。
