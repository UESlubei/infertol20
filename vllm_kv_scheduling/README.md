# vLLM KV 分层感知调度实验（已验收 V3）

本目录对应 RTX 3090 24GB / Qwen3-1.7B FP16 / vLLM 0.11.2，完整实现 GPU/Tier-aware Admission 与恢复代价感知抢占。

- [完整实验设计](../vLLM_KV分层感知调度_单卡RTX3090实验方案_V3.md)
- [完整实验报告](reports/完整实验报告_V3.md)
- [GitHub 下载与离线迁移步骤](../migration/README.md)
- [离线安装详细说明](offline_migration/README_离线迁移.md)
- [最终验收记录](reports/v3_completion_receipt.json)

已完成正式矩阵 130 Run、开发扫描/消融 167 Run、独立长测 10 Run、HTTP 10 Run，数据与正确性审计通过；性能提升的场景边界、负向结果和分类等待取舍见报告。

## 实现位置

- `kv_sched/policy.py`：配置、成本插值、实际重算区间账本、稳定准入顺序、Victim 规则。
- `kv_sched/runtime.py`：GPU/CPU 只读探针、资源缺口、独占 Block 统计、运行时观测和安全回滚。
- `patches/`：调度器接入及基线/优化共享的兼容修复。
- `benchmarks/`：固定 Trace、校准、HTTP、Profile、配对统计与完整串行流水线。
- `tests/`：策略与原生组件回归验证。
- `offline_migration/`：打包、路径重定位、安装校验和 GPU Smoke。

模型 Revision：`70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`。
vLLM 基础 Commit：`275de34170654274616082721348b7edd9741d32`。

## 在目标服务器运行

先按迁移文档从 Release 下载并安装自包含包，再使用包生成的环境变量：

```bash
source /实际安装目录/env.sh
cd "$KV_EXP_PROJECT"
"$KV_EXP_PYTHON" benchmarks/run_quick.py --label offline_quick
"$KV_EXP_PYTHON" benchmarks/full_pipeline.py
```

源码保留源机器的固定目录，安装程序会在离线副本中按目标路径重定位。源码浏览目录本身不包含模型权重与原生运行环境，完整包从 Release 获取。目标机器从全新性能数据开始。
