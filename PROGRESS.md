# AgentUnit Progress

## 项目状态

**当前阶段**: Phase 1 — 开源 Packer + 社区采纳
**最后更新**: 2026-06-07

---

## Phase 0 — 完成 ✅

### 基础架构 (commit 904b8ab)
- CLI 工具 `au` — Typer 框架，4 个命令 (`init`, `validate`, `pack`, `run`)
- Spec 解析与校验 — Pydantic 模型 + JSON Schema 双重验证
- 适配器架构 — 基类 + 注册中心 + 2 个内置适配器 (generic-python, langchain)
- PRD Writer 示例 — generic-python 框架，完整 skill/tool/knowledge 结构
- 测试覆盖 — 77 tests passed, lint clean

### Skill 路由 (commit b097b16)
- Spec 新增 `runtime.routing` — auto/explicit/hybrid 三种模式
- Skill 支持可选 `id` 和 `description` 字段
- 路由校验 — 唯一 skill ID、explicit 模式必须指定 skill_id

### Spec v0.1 修订
- 新增 4 个维度：protocol / resources / services / skills[].contract
- 新增可观测性：observability section + Telemetry 信封
- 3 轮 Pydantic ↔ JSON Schema ↔ Spec 文档 ↔ 适配器模板一致性审查（共 25 项修复）

### Docker 端到端验证
- HEALTHCHECK 改为 Python urllib（修复 slim 镜像无 curl 问题）
- `au run` 新增 `--serve` 模式（HTTP 服务器前台运行）
- Dockerfile 改为临时文件生成，不再污染源码目录
- 完整流程验证通过：validate → pack → one-shot run → serve → HTTP 调用

### Streamlit Invoker
- 通用调用演示前端 — `examples/invokers/streamlit_invoker.py`
- 动态表单生成、Telemetry 展示、多 Skill 选择

### Phase 0 收尾
- pm-agent 适配器和 demo 骨架移除（非开源框架，用户无法运行）
- docs/ 清空（HA-OOS 治理设计移至独立仓库）
- README.md 创建（开源项目首页）

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `README.md` | 项目首页 |
| `src/agentunit/core/spec.py` | Spec 解析 & 14 个 Pydantic 模型 |
| `src/agentunit/adapters/base.py` | 适配器基类（Dockerfile 生成 + hook 方法） |
| `src/agentunit/adapters/registry.py` | 适配器注册中心 |
| `src/agentunit/adapters/generic_python/` | 通用 Python 适配器（完整） |
| `src/agentunit/adapters/langchain/` | LangChain 适配器（骨架） |
| `src/agentunit/commands/init.py` | `au init` 命令 |
| `src/agentunit/commands/validate.py` | `au validate` 命令 |
| `src/agentunit/commands/pack.py` | `au pack` 命令 |
| `src/agentunit/commands/run.py` | `au run` 命令 |
| `src/agentunit/cli/main.py` | CLI 入口 |
| `spec/agentunit-spec-v0.1.md` | Spec 规范文档 |
| `spec/schemas/agentunit-schema.json` | JSON Schema |
| `examples/prd-writer-generic/` | PRD Writer Demo |
| `examples/invokers/streamlit_invoker.py` | Streamlit 调用演示 |
| `examples/invokers/requirements.txt` | Invoker 依赖 |
| `tests/test_spec.py` | Spec 测试 |
| `tests/test_adapters.py` | 适配器测试 |

---

## Phase 1 — 进行中

**目标**: 3 个非团队成员 star / fork / 提 issue

- [ ] 开源发布（GitHub public + 博客 + 视频）
- [ ] 选择一个开源框架（LangGraph / CrewAI）做真实 Demo
- [ ] JSON Schema 自动生成（从 Pydantic model_json_schema() 生成，保留手写 if/then 后处理）
- [ ] validate_spec 返回带严重级别的 warning（替代 `"not found" in w` 字符串匹配）
- [ ] 安全/沙箱声明（`security.sandbox_level`）
- [ ] 版本兼容性声明
- [ ] 可观测性增强（日志格式、tracing、metrics 端点模板）
- [ ] Skill 级别 governance 覆盖
- [ ] `metadata.license` 推荐 SPDX 标识符
- [ ] 社区贡献适配器入口（entry_points）
