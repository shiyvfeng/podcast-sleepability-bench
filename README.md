# Pillow Bench · 播客催眠等级分析

把播客的语调、语速和音量变化，做成一个可解释的「催眠指数」。面向中文播客的娱乐性声学比较，附本地分析脚本、计算方法和六个单集的真实结果示例。

![六个单集的催眠评测](examples/six-episodes/01-播客催眠评测.png)

## 六个单集示例

每个单集取时间轴正中间连续 20 分钟，共 120 分钟。这里保留 v0.2 的原始结果，未根据听感调整分数。

| 排名 | 栏目 | 催眠指数 | 语速（字词/分） | 语调起伏（半音） | 音量起伏（dB） | 局部音量抬升（次/10分） |
|---|---|---:|---:|---:|---:|---:|
| 1 | 三五环 | 87.5 | 286.3 | 3.80 | 6.1 | 0.5 |
| 并列 2 | 张小珺Jùn｜商业访谈录 | 54.0 | 258.9 | 3.96 | 10.5 | 26.0 |
| 并列 2 | 鹿鹿鱼鱼 | 54.0 | 294.1 | 4.72 | 6.2 | 1.0 |
| 4 | 硅谷101 | 50.5 | 296.5 | 5.65 | 5.7 | 0.5 |
| 5 | 葬AI | 28.0 | 298.3 | 5.31 | 8.4 | 7.0 |
| 6 | 十字路口Crossing | 26.0 | 343.6 | 4.26 | 9.4 | 9.5 |

[完整单集清单与示例说明](examples/six-episodes/README.md) · [CSV 数据](examples/six-episodes/metrics.csv) · [JSON 数据](examples/six-episodes/results.json)

### 「突发变响」指标的已知局限

示例图中的「突发变响」目前更准确的含义是 **局部音量抬升**：当前 1 秒 RMS 比此前 10 秒语音窗口的中位电平高至少 6 dB，并连续 5 个步长过线。

- 相邻窗口重叠 90%，五个窗口过线不等于原声持续变响 0.5 秒；短重音也可能触发。
- 它没有判断上升速度、说话人切换、笑声或音效，不能直接称为「爆响」或「吓醒次数」。
- 张小珺这期的 20 分钟样本，在 6 / 8 / 10 dB 阈值下分别检出 52 / 16 / 3 次；计数依赖定义。尚未用人工听感标注校准。

## 如何计分

| 指标 | 测量方式 | 权重 |
|---|---|---:|
| 语调平 | 每 5 秒计算有效基频的半音四分位距，再取中位数 | 30% |
| 语速慢 | 自动转写中的汉字、英文词和数字串计数，除以片段分钟数，包含停顿 | 30% |
| 音量稳 | 语音窗口的 1 秒 RMS 电平 P90−P10 | 25% |
| 少局部抬升 | 相对前 10 秒语音中位电平的抬升事件次数 | 15% |

四项原始值均越低、分项分越高。每项采用样本内排名，并列取平均名次：

```text
分项分 = 100 × (样本数 − 平均名次) / (样本数 − 1)
总分 = 语调平 × 30% + 语速慢 × 30% + 音量稳 × 25% + 少局部抬升 × 15%
```

阈值与权重是项目自定义规则，未经睡眠实验训练。增加或移除样本会改变相对分数。详见 [计算规则 v0.2](method-v0.1.md)。

## 快速查看示例

无需音频、模型或转写即可阅读 `examples/six-episodes/`。用 Python 标准库核对公开数据的字段和计分：

```bash
python3 scripts/verify_example.py
```

重新绘制这六个单集的图（需下文的绘图依赖及 macOS 中文字体）：

```bash
PODCAST_OUTPUT_DIR=examples/six-episodes python scripts/render.py
```

## 本地分析自己的音频

### 1. 安装环境

目前验证环境为 **Apple Silicon macOS、Python 3.12**。正式转写路径使用 MLX / Metal GPU。`requirements.lock.txt` 是本次使用的完整环境快照，不是跨平台锁文件；绘图脚本使用 macOS 的 Hiragino Sans GB 字体。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
mkdir -p samples models
```

下载转写模型到代码使用的本地路径（需要联网；运行分析时不上传音频）：

```bash
hf download mlx-community/whisper-small-mlx --local-dir models/whisper-small-mlx
```

### 2. 放入音频并准备样本

把自己有权使用的音频放入 `samples/`，支持 `.aac`、`.m4a`、`.mp3`、`.wav`、`.flac`。

当前完整汇总/验证流程要求至少 2 个样本，且每个音频不少于 20 分钟、有足够可检测语音。准备脚本可读取短音频，但后续固定五个四分钟窗口的检查尚不支持它们。

```bash
export PODCAST_OUTPUT_DIR=output/my-run
python scripts/prepare.py
```

准备脚本完整解码后取中段，记录来源哈希、时长及采样位置。随后查看 `output/my-run/manifest.json`，按实际文件与 `id` 的对应关系编辑根目录 `sample_catalog.json` 中的 `name`、`episode`、`short`、`identification`。仓库自带清单只对应示例的六个单集，不要直接套用到新音频。

缓存位于 `cache/`，按样本 ID 存储。使用同一个输出目录继续分析可以复用来源哈希；换一批全新音频时，应另用干净项目副本或先备份并清理旧缓存，避免不同批次的 ID 混用。

### 3. 运行分析与验证

```bash
python scripts/analyze.py
python scripts/transcribe_mlx.py
python scripts/summarize.py
python scripts/verify.py
```

- 声学处理：16 kHz 单声道；不做动态压缩、降噪或逐片段响度归一化。
- 转写：本地 Whisper small，中文、float16、温度 0、每段 4 分钟；语速依赖自动转写，未人工逐字校对。
- 汇总：生成 `results.json`、`榜单与指标.csv`、`四分钟分段指标.csv`，以及权重和时间窗口敏感性结果。
- 验证：核对输入哈希、时长、基频边界、音量指标、事件位置、转写计数和计分。

### 4. 绘图与报告

```bash
python scripts/render.py
python scripts/batch_report.py
```

**当前绘图模板专用于六个单集**，标题映射在 `scripts/render_episode.py` 的 `SHOWS`、`EPISODES` 中。分析自己的节目时要修改映射；不同样本数还需调整版式。`batch_report.py` 的部分示例文案也针对这次六集实验，生成后应人工审阅。核心汇总支持其他样本数，模板尚不是通用产品。

`render_legacy_five.py` 和 `report.py` 是历史模板；`incremental_report.py` 依赖本机历史批次，不属于新仓库的快速开始流程。

## 复核某个音量事件

对这次六集实验，在本机保有原音频、声学缓存和转写时可以运行：

```bash
export PODCAST_OUTPUT_DIR=output/batch-06
python scripts/review_spikes.py
python scripts/write_spike_review.py
```

生成事件清单、原声片段、音量曲线、时频谱和功率谱。该脚本目前固定复核 `s04`；诊断输出含音频与转写，保留在被 Git 忽略的 `output/` 中。

## 仓库内容与数据边界

```text
scripts/                  分析、转写、绘图、验证与示例导出代码
examples/six-episodes/    六个单集的汇总指标与三张示例图
sample_catalog.json      示例节目与单集名称
method-v0.1.md           当前 v0.2 的方法说明及修正记录
requirements.lock.txt   本次环境版本快照
```

**仓库不提供音频或转写文本。** `samples/`、`cache/`、`models/`、`output/`、转写目录及音视频扩展名均被 `.gitignore` 排除。本地 `results.json` 也可能嵌有低置信转写片段，不应直接复制到公开目录。

公开示例由字段白名单导出，只保留节目名称、完整单集名和汇总数字：

```bash
PODCAST_OUTPUT_DIR=output/batch-06 python scripts/export_example.py
python scripts/verify_example.py
```

公开示例能复核计分、重绘图表；缺少原音频和转写，不能独立重算声学指标或验证转写准确率。来源节目与单集标题仅用于说明分析对象。

## 理论参考

- Scarratt et al. (2023). [The audio features of sleep music: Universal and subgroup characteristics](https://doi.org/10.1371/journal.pone.0278813).
- Schewski et al. (2025). [Measuring negative emotions and stress through acoustic correlates in speech: A systematic review](https://doi.org/10.1371/journal.pone.0328833).

这些研究提供声学特征的间接参考，并未验证本项目的公式、权重或播客助眠效果。
