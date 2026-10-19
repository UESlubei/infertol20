# vLLM KV Cache 分层感知调度实验与离线迁移

基于单张 RTX 3090 24GB、Qwen3-1.7B FP16、vLLM 0.11.2 的 GPU/Tier-aware Admission 与恢复代价感知抢占实验。

**实验已完成：130 个正式 Run、167 个参数扫描/消融 Run、10 个独立长测 Run、10 个 HTTP Run，最终数据与正确性审计通过。** 数据审计通过不等于所有策略都有性能收益，负向结果同样保留。

**离线包上传状态：等待本机 GitHub CLI 登录后上传 Release 分卷；当前仓库源码与文档可用。**

| 内容 | 入口 |
| --- | --- |
| 完整实验设计 V3 | [实验方案](vLLM_KV分层感知调度_单卡RTX3090实验方案_V3.md) |
| 完整实测报告、负向结果和图表 | [实验报告](vllm_kv_scheduling/reports/完整实验报告_V3.md) |
| GitHub 下载、分卷合并与离线迁移 | [迁移操作文档](migration/README.md) |
| 离线安装详细说明 | [安装说明](vllm_kv_scheduling/offline_migration/README_离线迁移.md) |
| 离线环境分卷 | [GitHub Release](https://github.com/UESlubei/infertol20/releases/tag/v3-rtx3090-offline-20261019) |
| 打包与迁移验证记录 | [构建记录](migration/BUILD_RECEIPT.json) |

## 已实现的优化

- **GPU Cache-aware Admission**：有限窗口内优先复用 GPU KV，保留不合格请求屏障、稳定顺序和超时优先。
- **Tier-aware Admission**：结合 GPU 命中、CPU 连续 Ready KV、实测 Prefill/H2D 成本及等待时间排序。
- **Recompute/Restore-aware Preemption**：根据实际可释放 Blocks、当前缺口、恢复成本和输出预算进度选择 Victim，支持非队尾预留回滚。
- 公共兼容修复、执行区间重算账本、逐 Run Manifest 和故障验证，用于保证对照安全、可解释。

目前主矩阵中，GPU 640 Blocks 的共享前缀场景 P95 TTFT 降低 19.05%，CPU 混合缓存联合策略降低 13.28%；混合长短请求的 Recompute 和多轮会话联合策略存在退化。完整区间、独立长测和公平性取舍以实验报告为准，不宣称通用加速。

## 离线包

合并后的归档为 `vllm-kv-offline-linux-x86_64-20261019.tar`，14,232,545,280 Bytes（约 14.23 GB）。SHA256：

```text
4e22a854f9f4f2d14c3bb1740a2e7d9bf61f82f8c4b53f4f93d341c24f5ddbeb
```

包括完整模型权重和 Tokenizer、Python/vLLM/Torch、Stock/Optimized Overlay、CUDA Toolkit 12.8、Nsight、独立绘图运行环境、成本表和实验源码。归档按 1 GiB 分为 14 卷，通过 Release 下载；Git 仓库只保存源码、文档、图表和校验清单。

目标为 Ubuntu/Linux x86_64、glibc >= 2.31。服务器需要已有兼容 CUDA 12.8 的 NVIDIA 驱动与 GCC/C 开发头文件。建议先在联网机器合并归档，再把 `.tar` 与 `.tar.sha256` 迁移到服务器；服务器建议预留 60GB 空间。更换 GPU 或 PCIe 环境时先重测成本表。

## 复现与版本边界

核心发布 SHA256：`bd2dec2afee8da292e0c7876a0710c7156f487cb46d8849875e21fd96942430a`。模型 Revision：`70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`。vLLM 基础 Commit：`275de34170654274616082721348b7edd9741d32`。

本仓库对应已经验收的 vLLM 0.11.2 实验与迁移包。运行时二进制和模型通过 Release 中的自包含包获取；GitHub 自动生成的 Source code ZIP 不包含运行环境和权重。离线安装会按目标目录修复路径并重新冻结源码，记录原发布与迁移修改。目标服务器从全新性能数据开始，源机器的报告不会被当成目标结果。
