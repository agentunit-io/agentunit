# AgentUnit Progress

## 项目状态

**当前阶段**: Phase 0 — 开源 Packer CLI + Spec
**最后更新**: 2026-06-05

---

## 已完成

### 基础架构 (commit 904b8ab)
- CLI 工具 `au` — Typer 框架，4 个命令 (`init`, `validate`, `pack`, `run`)
- Spec 解析与校验 — Pydantic 模型 + JSON Schema 双重验证
- 适配器架构 — 基类 + 注册中心 + 3 个内置适配器 (generic-python, langchain, pm-agent)
- PRD Writer 示例 — generic-python 框架，完整 skill/tool/knowledge 结构
- 测试覆盖 — 33 个测试全部通过

### Skill 路由 (commit b097b16)
- Spec 新增 `runtime.routing` — auto/explicit/hybrid 三种模式
- Skill 支持可选 `id` 和 `description` 字段
- 路由校验 — 唯一 skill ID、explicit 模式必须指定 skill_id

### Spec v0.1 修订 (未提交)
本轮修订经过多轮设计审查，核心变更：

**修复 7 项问题：**
1. Dockerfile 从 CMD 改为 ENTRYPOINT（支持 one-shot 模式）
2. Dockerfile 生成逻辑从 3 个适配器下沉到 base.py 统一实现
3. `RUN pip install` 使用 spec 中的 dependencies.file（而非硬编码）
4. pm-agent `get_run_command` 添加缺失的 `--input` 标志
5. 移除 `responsible_human`（属于运营绑定，非 Unit 固有属性）
6. pm-agent run_command 移除失效的 `${VAR}` shell 语法
7. `au run` 注入 build.env 环境变量 + 缺失变量警告

**新增 4 个维度：**
- `protocol` — 调用接口声明（streaming/function call/协议兼容性）
- `resources` — 部署资源需求（CPU/内存/GPU/超时/并发）
- `services` — 外部服务依赖（外网访问/域名白名单）
- `skills[].contract` — Skill 级别契约覆盖（多 Skill 不同输入输出）

**新增可观测性：**
- `observability` section — 质量指标标记 + 性能基线
- Telemetry 信封 — `/run` 响应从 `{output}` 变为 `{output, telemetry}`
- 三层评估模型文档 `docs/OBSERVABILITY-DESIGN.md`

**修复 6 项调整：**
- `max_token_per_task` 从 `int=0` 改为 `int|None=None`
- `routing.default` 统一为 `hybrid`（Pydantic + Schema + 所有模板）
- JSON Schema 补齐 tools/knowledge 的 description 字段
- `build.env` "空串=必填"惯例写入文档
- `runtime.model` 标注为设计时声明（非运行时硬约束）
- `tools[].type` 从 `str` 改为 `Literal`

**当前测试**: 79 tests passed, lint clean

### 三轮一致性审查 (本轮新增)
三轮 Pydantic ↔ JSON Schema ↔ Spec 文档 ↔ 适配器模板 ↔ 示例 的全量交叉审查：

**Round 1 — 16 项修复：**
- Pydantic 新增 `metadata.name` kebab-case pattern 约束
- Pydantic 新增 `metadata.version` SemVer pattern 约束
- Pydantic 新增 `metadata.description` min_length/max_length
- Pydantic `runtime.language` 从 `str` 改为 `Literal["python", "nodejs", "go"]`
- Pydantic `apiVersion`/`kind` 从 `str` 改为 `Literal`（精确值约束）
- Pydantic `Resources.timeout_seconds`/`concurrency` 新增 `ge=1`
- Pydantic `EvaluationBaselines.latency_p95_ms` 新增 `ge=1`
- Pydantic `EvaluationBaselines.success_rate` 新增 `ge=0, le=1`
- Pydantic `Build.port` 新增 `ge=1, le=65535`
- JSON Schema `runtime.model` 补齐 provider/name 默认值
- LangChain 模板补齐 `build.health_check`、`build.env`
- Spec 文档 `runtime.entry` 描述从 "file" 改为 "file path or module path"
- Spec 文档 `runtime.framework`/`language`/`entry` 标注 "with default"
- 新增 23 个约束测试（TestMetadataConstraints, TestRuntimeConstraints, TestBuildConstraints, TestResourcesConstraints, TestBaselineConstraints, TestApiVersionKindConstraints）

**Round 2 — 7 项修复：**
- JSON Schema `dependencies.file` 从 required 改为 optional + default
- JSON Schema `runtime.framework`/`language`/`entry` 补齐默认值
- Pydantic `Protocol` 新增 `model_validator` 校验 mode/streaming_type 交叉约束
- JSON Schema `protocol` 新增 `if/then` 校验 streaming_type 一致性
- LangChain 模板补齐 `governance`、`protocol`、完整 `resources`
- 全部模板补齐 `gpu`、`concurrency`、完整 `protocol` 字段
- Generic-python 模板 tools 示例补齐 `type` 字段
- 新增 4 个 Protocol 交叉约束测试

**Round 3 — 2 项修复：**
- Pydantic `Governance.max_token_per_task` 新增 `ge=1` 约束
- Spec 文档 `dependencies.file` 从 "Required" 改为 "Optional. Default"

### Streamlit Invoker
- 通用调用演示前端 — 连接运行中的 Agent Unit 的 `/run` 端点
- 动态表单生成 — 从 `/spec` 拉取 contract.inputs 自动生成输入控件
- Telemetry 展示 — latency、token usage、skill_id
- 多 Skill 选择支持
- 放置于 `examples/invokers/`，与 Unit 实现解耦

### Docker 端到端验证
- HEALTHCHECK 从 curl 改为 python urllib（修复 slim 镜像无 curl 问题）
- `au run` 新增 `--serve` 模式（HTTP 服务器前台运行）
- Dockerfile 改为临时文件生成，不再污染源码目录
- 完整流程验证通过：validate → pack → one-shot run → serve → HTTP 调用

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `src/agentunit/core/spec.py` | Spec 解析 & 14 个 Pydantic 模型 |
| `src/agentunit/adapters/base.py` | 适配器基类（Dockerfile 生成 + hook 方法） |
| `src/agentunit/adapters/registry.py` | 适配器注册中心 |
| `src/agentunit/adapters/generic_python/` | 通用 Python 适配器（完整） |
| `src/agentunit/adapters/langchain/` | LangChain 适配器（骨架） |
| `src/agentunit/adapters/pm_agent/` | pm-agent 适配器（完整） |
| `src/agentunit/commands/init.py` | `au init` 命令 |
| `src/agentunit/commands/validate.py` | `au validate` 命令 |
| `src/agentunit/commands/pack.py` | `au pack` 命令 |
| `src/agentunit/commands/run.py` | `au run` 命令 |
| `src/agentunit/cli/main.py` | CLI 入口 |
| `spec/agentunit-spec-v0.1.md` | Spec 规范文档 |
| `examples/invokers/streamlit_invoker.py` | Streamlit 调用演示 |
| `examples/invokers/requirements.txt` | Invoker 依赖 |
| `spec/schemas/agentunit-schema.json` | JSON Schema |
| `examples/prd-writer-generic/` | PRD Writer Demo |
| `tests/test_spec.py` | Spec 测试（37 tests） |
| `tests/test_adapters.py` | 适配器测试（16 tests） |
| `docs/AGENTUNIT-CHARTER.md` | 项目计划书 |
| `docs/PRINCIPLES.md` | 个人原则卡 |
| `docs/OBSERVABILITY-DESIGN.md` | 可观测性设计文档 |

---

## 下一步

### 近期（当前未提交的变更提交后）
- [ ] 提交本轮所有变更
- [ ] 补充 pm-agent 适配器的真实 Demo（`examples/prd-writer-pmagent/`）
- [ ] 端到端验证：`au init → au validate → au pack → au run` 完整流程

### Phase 1 计划
- [ ] 安全/沙箱声明（`security.sandbox_level`）
- [ ] 版本兼容性声明
- [ ] 可观测性增强（日志格式、tracing、metrics 端点模板）
- [ ] Skill 级别 governance 覆盖
- [ ] `metadata.license` 推荐 SPDX 标识符
- [ ] 社区贡献适配器入口（entry_points）

### Phase 2
- [ ] HA-OOS MVP — Agent 注册 + 责任锚定 + Score Card
- [ ] 企业 Registry
- [ ] 审计/合规

### Phase 3
- [ ] Agent Unit 商店
- [ ] 行业模板
- [ ] 商业平台
