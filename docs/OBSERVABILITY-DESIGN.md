# Agent Unit 可观测性设计

## 核心问题

Agent Unit 是企业级 AI 生产单元。要让它**可评估、可改进**，管理平台（HA-OOS）需要持续回答三个问题：

1. 这个 Unit 运行得好不好？（可评估）
2. 它在变好还是变差？（可改进）
3. 哪些环节需要优化？（可归因）

## 三层评估数据模型

评估数据按来源分为三层，每层的采集方式、采集者、时效性不同：

### 第一层：HA-OOS 自动测量

HA-OOS 坐在请求链路上，**不需要 Unit 配合**就能测量：

| 指标 | 采集方式 | 时效性 |
|------|---------|--------|
| 请求延迟（P50/P95/P99） | HTTP round-trip 计时 | 实时 |
| 成功率 | HTTP 状态码统计 | 实时 |
| 吞吐量（QPS） | 请求计数 | 实时 |
| 可用性 | 健康检查探测 | 准实时 |

**类比**：Nginx 不需要后端服务配合就能统计响应时间和错误率。

### 第二层：Unit 主动上报

这些数据**只有 Unit 内部才知道**，HA-OOS 从外面看不到：

| 指标 | 为什么只有 Unit 知道 |
|------|---------------------|
| Token 消耗 | Unit 调 LLM API，token 计数在 API response 中，HA-OOS 看不到 |
| 实际使用的模型 | `MODEL_BASE_URL` 指向什么端点、实际调的是什么模型，只有运行时知道 |
| 命中的 Skill | 路由决策在 Unit 内部完成，HA-OOS 只看到请求进出 |
| 自评质量分 | Unit 内部对输出质量的评估（如 PRD 的 quality_score），是业务逻辑的一部分 |
| 内部推理步数 | Agent 的 chain-of-thought / ReAct 走了几步，属于内部状态 |

**关键问题**：如果不暴露这些数据，HA-OOS 只能看延迟和成功率。一个 Unit 延迟 3 秒、成功率 99%，但每次消耗 50000 token 且质量分只有 0.3 — 从外面完全看不出来。

### 第三层：人/平台评估

需要外部输入，不在 Unit 能力范围内：

| 指标 | 谁来评估 |
|------|---------|
| 用户满意度 | 真正使用输出的人打分 |
| 输出准确性 | 事实核查或领域专家 |
| 业务价值 | 这个 Unit 是否帮企业提效 |
| 合规性 | 合规检查工具或人工审核 |

## 数据采集方案：Telemetry 信封

### 设计选择

**方案 A（采纳）**：`/run` 响应分为 `output` + `telemetry` 两部分。

```json
{
  "output": { ... },
  "telemetry": {
    "skill_id": "prd_writer",
    "token_usage": { "input": 500, "output": 2000 },
    "model_used": "gpt-4o-2024-08-06",
    "latency_ms": 3200
  }
}
```

**为什么选择方案 A**：

1. **关注点分离** — `output` 是纯业务数据，调用方只关心这个；`telemetry` 是纯观测数据，HA-OOS 只关心这个
2. **标准化** — 所有 Unit 的 telemetry 结构一致（skill_id, token_usage, model_used, latency_ms），HA-OOS 用同一套逻辑处理
3. **无侵入** — 调用方不需要理解 telemetry，只看 output 即可
4. **可扩展** — 未来可以给 telemetry 加新字段（如 reasoning_steps），不影响 output

**方案 B（未采纳）**：telemetry 混在 contract.outputs 里。

问题：业务数据和观测数据混在一起，HA-OOS 无法区分 `prd_document`（业务输出）和 `token_usage`（系统指标），也不知道哪些字段应该被采集。

### 标准 Telemetry 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `skill_id` | string | 本次请求命中的 skill 标识 |
| `token_usage.input` | int | 输入 token 数 |
| `token_usage.output` | int | 输出 token 数 |
| `model_used` | string | 实际使用的模型标识（可能不同于 spec 声明的设计时模型） |
| `latency_ms` | int | Unit 内部处理耗时（不含网络传输） |

所有字段都是可选的 — 简单 Agent 可以不填 telemetry，HA-OOS 就只做第一层测量。

## Spec 的角色

Spec 新增 `observability` section，声明：

### 采集通道

- `metrics_endpoint`：Unit 是否暴露 Prometheus 格式的系统指标端点

### 质量指标标记

- `evaluation_indicators`：标记 `contract.outputs` 中哪些字段是质量信号
  - 引用 output 字段名（如 `quality_score`）
  - 声明预期范围（如 `[0, 1]`）和方向（越高越好还是越低越好）
  - HA-OOS 从响应的 `output` 中提取这些字段值进行追踪

### 性能基线

- `baselines`：Unit 设计者的性能预期
  - `latency_p95_ms`：正常情况下 95% 请求的预期延迟
  - `success_rate`：正常情况下的预期成功率
  - 这些不是硬约束，而是 HA-OOS 对比实际数据的参考基准

## 职责划分总结

| 数据 | 谁测量/提供 | 数据来源 | Spec 声明 |
|------|-----------|---------|----------|
| 请求延迟 | HA-OOS | HTTP round-trip | `baselines.latency_p95_ms` |
| 成功率 | HA-OOS | HTTP status | `baselines.success_rate` |
| Token 消耗 | **Unit 上报** | telemetry.token_usage | 标准字段，无需逐个声明 |
| Skill 归因 | **Unit 上报** | telemetry.skill_id | 标准字段 |
| 实际模型 | **Unit 上报** | telemetry.model_used | 标准字段 |
| 自评质量分 | **Unit 上报** | output.quality_score | `evaluation_indicators` 标记 |
| 用户满意度 | HA-OOS | 外部反馈机制 | 不在 spec |
| 准确性 | HA-OOS | 外部评估 | 不在 spec |

**核心原则**：Spec 声明"HA-OOS 应该关注什么"，HA-OOS 决定"怎么采集和分析"。
