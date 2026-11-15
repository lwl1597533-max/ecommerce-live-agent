# 电商直播文案生成 Agent

根据提供的项目文档实现商品卖点提取、四阶段直播话术、三种风格、互动意图分类和回复。提供 FastAPI 接口、浏览器工作台、SSE 流式输出、Redis 缓存（不可用时回退进程内缓存）、SQLite 生成日志及点赞反馈。

## 本机启动

在项目目录执行：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv/Scripts/python.exe scripts/seed.py
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

已有环境时直接运行 `./start.ps1`。页面 http://127.0.0.1:8000 ，接口文档 http://127.0.0.1:8000/docs 。默认只绑定本机地址。

## 模型配置

在 `.env` 中配置，然后重启服务：

```dotenv
MODEL_BACKEND=openai
VLLM_BASE_URL=https://www.yunzhuhub.com/v1
MODEL_NAME=qwen3.8-flash
VLLM_API_KEY=填写你的服务密钥
```

密钥仅放 `.env`，不要提交 Git。`API_KEY` 是本应用访问密钥，与上游模型密钥不同；配置后页面顶部需填写它。真实模型模式会将提交的商品资料和必要对话发送到指定模型服务。接口失败会报错，不会静默切换演示结果。

`MODEL_BACKEND=demo` 使用确定性规则模板，仅用于验证交互和接口，不代表模型能力，不保证目标口播时长。`/health` 表示应用进程可用；`/ready` 在真实模式查询上游 `/models` 并检查模型名，部分未提供该接口的服务需直接生成验证。

## Docker 与原文 GPU 方案

本机检测到 RTX 3050 4GB 显存、Python 3.13，未检测到 Docker，因此没有在本机部署 Qwen-7B FP16。Python 依赖采用支持本地版本的范围，安装后生成 requirements.lock.txt 记录实际版本；没有直接沿用文档中的旧 Python 依赖锁定。

已安装 Docker 的服务器可运行 `docker compose up -d --build api redis`。API 容器连接外部模型时使用上面的远程地址。本机直连运行不要求安装 Redis。

24GB NVIDIA 显存的 Linux GPU 服务器可以使用文档原版容器配置：设置 `.env` 为 `MODEL_BACKEND=openai`、`MODEL_NAME=Qwen/Qwen-7B-Chat`、`VLLM_BASE_URL=http://vllm:8001/v1`、`VLLM_API_KEY=EMPTY`，执行 `docker compose --profile gpu up -d --build`。该路径保留 vLLM 0.4.2 配置，但未在本机验证，依赖 NVIDIA Container Toolkit 和兼容驱动。首次启动会下载模型。

vLLM 官方安装说明：https://docs.vllm.ai/en/v0.18.0/getting_started/installation/gpu/
LangChain 模型接口说明：https://reference.langchain.com/python/langchain-openai/chat_models/base/ChatOpenAI

## 接口

| 接口 | 作用 |
| --- | --- |
| GET /api/products | 24 个模拟商品，覆盖四品类 |
| POST /api/extract/selling-points | 商品 JSON → 3–5 个带证据卖点 |
| POST /api/generate/script | 商品、阶段、风格、时长 → 话术 |
| POST /api/interact/reply | 提问、商品、最近对话 → 意图和回复 |
| POST /api/feedback | generation_id 与 rating（1 或 -1） |

话术阶段为 opening / intro / promote / close，风格为 passionate / professional / humorous。`stream=false` 返回完整 JSON；默认 SSE 事件依次为 selling_points、token、done，生成中断时发送 error，客户端须检查 done。

商品数据进行 Pydantic 校验；超时返回 504，模型错误返回 502，输入错误返回 422。每 IP 每分钟最多 60 个 API 请求，限流和回退缓存均为单进程方案。跨域默认关闭，页面与接口同源。

## 开发与验证

```powershell
.venv/Scripts/python.exe -m pytest -q
```

提示词位于 `app/prompts/v1/script.j2`，可复制为 v2 后通过 PROMPT_VERSION 切换。所有生成日志记录版本、模型模式、输入、输出、耗时和反馈，位于 `runtime/generations.sqlite3`。缓存键含完整商品内容、模型及提示词版本，更新价格不会复用旧缓存。

上下文最多保留最近 10 轮并按字符预算裁剪；这不是精确 token 计数。当前时长通过提示词约束并返回 duration_in_range，不保证每次达标。流式文本未实现完整的事实核验和合规审核，直播前需人工审阅；不要把本项目演示结果、文档中的性能数字或示例简历指标当作实测结果。真实模型质量、并发性能和 GPU 路径需接通服务后另行评估。
