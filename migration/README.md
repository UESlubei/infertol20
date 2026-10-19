# 从 GitHub 下载并迁移到离线服务器

对应已验收的 vLLM 0.11.2 / RTX 3090 / Qwen3-1.7B V3 实验。完整环境、模型权重和源码打在同一个离线包中；GitHub 仓库的 Source code ZIP 只包含代码和文档。

- Release：https://github.com/UESlubei/infertol20/releases/tag/v3-rtx3090-offline-20261019
- 原始包：`vllm-kv-offline-linux-x86_64-20261019.tar`
- 原始大小：14,232,545,280 Bytes，约 14.23 GB。
- SHA256：`4e22a854f9f4f2d14c3bb1740a2e7d9bf61f82f8c4b53f4f93d341c24f5ddbeb`
- 分为 14 卷，每卷不超过 1 GiB，按 manifest.json 中的顺序合并。

上传状态以仓库首页为准；Release 只有全部附件上传并核验后才发布。

## 1. 在联网机器下载附件

打开上面的 Release 页面，把以下文件下载到同一个文件夹：

- 全部 `.tar.part-000` 到 `.tar.part-013`，共 14 个文件。
- `manifest.json`、`SHA256SUMS.parts` 和 `.tar.sha256` 校验文件。
- `restore_bundle.py` 与 `README_迁移操作.md`。

已安装 GitHub CLI 的联网机器可执行：

```bash
gh release download v3-rtx3090-offline-20261019 \
  --repo UESlubei/infertol20 --dir release-download --skip-existing
cd release-download
```

浏览器下载不需要在离线服务器安装 gh。下载完整后再进行迁移，避免遗漏分卷。初次下载可以使用 `--skip-existing`；若某卷校验失败，应重新下载该卷。

## 2. 校验并合并

推荐在联网机器合并，只把最终 `.tar` 和 `.tar.sha256` 带到服务器：

```bash
sha256sum -c SHA256SUMS.parts
python3 restore_bundle.py
sha256sum -c vllm-kv-offline-linux-x86_64-20261019.tar.sha256
```

合并脚本还会逐卷核验 SHA256、检查文件顺序和总大小，并验证整个原始包的 SHA256。它拒绝覆盖已有的完整包；已有 `.partial` 文件时请先检查上次失败原因。

通过移动硬盘、U 盘或内网传输这两个文件：

```text
vllm-kv-offline-linux-x86_64-20261019.tar
vllm-kv-offline-linux-x86_64-20261019.tar.sha256
```

也可以把全部分卷及合并脚本带到离线服务器再合并。原包安装建议预留 60GB 空间；如果分卷、合并后的原包和解压文件都在同一磁盘保留，建议预留 80GB。

## 3. 确认目标服务器条件

- Ubuntu/Linux x86_64、glibc >= 2.31，通常为 Ubuntu 20.04 或更新版本。
- 已有兼容 CUDA 12.8 的 NVIDIA 驱动；源机器驱动为 570.86.15。
- 已有 GCC/cc 和 Linux C 开发头文件，供 Triton 首次运行编译使用。
- 默认实验在 RTX 3090 24GB 上验证。其他 GPU 需要实际执行 GPU Smoke；显存较小时还需调整实验预算。

Python、Conda、CUDA Toolkit、Nsight 和模型不需要在线安装，本包已经包含。宿主 NVIDIA 驱动属于内核组件，不随环境包安装。若缺驱动或编译器，先用服务器现有离线系统软件源补齐。

可检查：

```bash
uname -m
ldd --version | head -n 1
nvidia-smi
gcc --version | head -n 1
```

## 4. 解包和安装

先进入准备长期存放实验的可写目录，把两个完整文件放在其中，再执行：

```bash
bundle_name=vllm-kv-offline-linux-x86_64-20261019
sha256sum -c "$bundle_name.tar.sha256"
tar -xf "$bundle_name.tar"
cd "$bundle_name"
bash install.sh
source env.sh
```

安装无需网络或 root。脚本会执行 conda-unpack、重建实验虚拟环境、修复 vLLM 二进制链接和绝对路径，验证模型哈希与依赖，并生成迁移后的源码冻结清单。原发布与迁移修改保存到 `INSTALLATION.json`。

应先放到最终路径再安装；安装完成后换目录应从原包重新解压安装。

## 5. 验证 GPU 与重测成本

```bash
"$KV_EXP_PYTHON" "$KV_OFFLINE_ROOT/verify_offline.py" --gpu-smoke
```

它启动同步单卡引擎与原生 CPU Offload，完成 2 个短请求，结果保存为 `data/offline_gpu_smoke.json`。

GPU 或 PCIe 环境不同于源 RTX 3090 时，应在正式实验前重新校准成本表：

```bash
bash "$KV_OFFLINE_ROOT/recalibrate.sh"
```

如果已有性能结果，重校准脚本会拒绝继续，防止同一数据目录混用不同成本表；请在全新安装中校准。

## 6. 运行实验

先小规模检查：

```bash
cd "$KV_EXP_PROJECT"
"$KV_EXP_PYTHON" benchmarks/run_quick.py --label offline_quick
```

再运行完整流程：

```bash
"$KV_EXP_PYTHON" benchmarks/full_pipeline.py
```

需要后台运行时：

```bash
nohup "$KV_EXP_PYTHON" benchmarks/full_pipeline.py \
  > "$KV_EXP_DATA/full_pipeline.log" 2>&1 < /dev/null &
```

同一安装目录只启动一条 GPU 实验流水线。每次打开新终端先在包根目录执行 `source env.sh`。

```bash
"$KV_EXP_PYTHON" benchmarks/status_full.py
tail -n 30 "$KV_EXP_DATA/full_pipeline.log"
```

目标机原始结果在 `data/raw/`，报告在 `project/reports/`。成功阶段和完整 Run 支持跳过恢复。目标服务器从新数据开始，不会把源机器的完成状态和性能报告作为本机结果。

完整实验设计见[实验方案 V3](../vLLM_KV分层感知调度_单卡RTX3090实验方案_V3.md)，本机最终结果见[完整实验报告](../vllm_kv_scheduling/reports/完整实验报告_V3.md)。
