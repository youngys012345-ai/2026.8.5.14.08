# 预研仓库

内网请先阅读：[docs/guide/内网执行清单.md](docs/guide/内网执行清单.md)

参数文件：根目录 `config.json`（内网按需修改）。

常用命令：

```bash
python scripts/prepare_dirs.py
python scripts/clone_third_party.py
python scripts/download_t1.py --dry-run
python scripts/download_t3.py --dry-run
python scripts/run_train.py
python scripts/run_eval.py
```

勿将内部业务视频、权重、密钥提交到本仓库。
