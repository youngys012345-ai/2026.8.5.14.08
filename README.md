# 预研仓库（精简版）

只改根目录 `config.json`（内含 `_help` 字段说明与可选值），只跑三个脚本。

| 模块 | 命令 |
|------|------|
| 下载 | `python scripts/download_data.py` / `--run` |
| 训练 | `python scripts/train.py` / `--run` |
| 评测 | `python scripts/eval.py` / `--run` |

内网步骤见 [docs/guide/内网执行清单.md](docs/guide/内网执行清单.md)。流程图见 [docs/guide/流程图.md](docs/guide/流程图.md)。

勿提交内部业务数据与权重。
