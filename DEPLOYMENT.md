# 本地部署记录

部署目录：D:\电商直播agent

- 本地服务：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs
- 模型服务：https://www.yunzhuhub.com/v1
- 配置模型：gpt-6-sol
- 模型模式：openai（真实模型模式，无自动演示回退）
- 已完成：虚拟环境、依赖安装、24 个模拟商品、API、浏览器工作台、SSE、日志、反馈、启动脚本和 Docker 配置。
- 验证：20 项自动化测试通过；pip check 通过；页面 HTTP 200；页面 JavaScript 语法检查通过。
- 上游验证：gpt-6-sol 已通过真实端到端测试：提取 4 个卖点，流式生成 114 字话术并收到 done，互动回复成功识别 price 意图。此前 qwen3.8-flash 返回服务商模型故障，现已切换。
- 硬件差异：本机 RTX 3050 4GB，不能按原文运行 Qwen-7B FP16；采用用户提供的远程模型服务。Redis 本机未安装，暂用进程内缓存，SQLite 日志持久化。

修改 `.env` 中的模型名或服务地址后，重启服务即可重试。密钥不得粘贴到日志或提交版本库。`/ready` 仅校验模型列表，不能保证推理成功。可运行 `.venv/Scripts/python.exe -X utf8 scripts/smoke.py` 验证完整链路。

服务输出在 runtime/server.out.log 和 runtime/server.err.log，进程号记录在 runtime/server.pid。电脑重启后运行 start.ps1。
