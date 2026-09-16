"""Write the Chinese handoff with traceable results and scoped conclusions."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output'

def stamp(seconds):
    seconds=round(seconds);return f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}'

def main():
    data=json.loads((OUT/'results.json').read_text());rows=data['rows']
    top=rows[0];fast=max(rows,key=lambda r:r['units_per_min']);slow=min(rows,key=lambda r:r['units_per_min'])
    flat=min(rows,key=lambda r:r['pitch_iqr_st']);animated=max(rows,key=lambda r:r['pitch_iqr_st'])
    stable=min(rows,key=lambda r:r['loudness_range_db']);spiky=max(rows,key=lambda r:r['spikes_per_10min'])
    text=f'''# 播客催眠等级分析：5 个单集首轮结果

## 先看结果

**本轮相对综合分最高：{top['name']}，{top['score']:.1f} 分。**

本次使用用户提供的 5 个音频文件，每份取中间连续 20 分钟，共 100 分钟。它们是 5 个指定单集，不是整个中文播客市场的代表样本；本榜只描述这些片段的声音特征。分数是项目自定义的相对娱乐评分，不是入睡概率。

| 排名 | 节目／单集 | 催眠指数 | 语速（转写字词/分） | 语调起伏（半音） | 音量起伏（dB） | 突发变响（次/10分） |
|---|---|---:|---:|---:|---:|---:|
'''
    for r in rows:
        text+=f"| {r['rank']} | {r['name']} · {r['short']} | {r['score']:.1f} | {int(r['units_per_min']+.5)} | {r['pitch_iqr_st']:.2f} | {r['loudness_range_db']:.1f} | {r['spikes_per_10min']:.1f} |\n"
    text+=f'''
语调、语速、音量起伏和突发事件四项均为数值越低，对应娱乐评分越高。音量起伏不代表播放设备实际声压；突发变响不是惊醒次数。

## 单项奖与可用吐槽

- **嘴速涡轮增压奖：{fast['name']}**，约 {int(fast['units_per_min']+.5)} 转写字词/分钟。文案：“别人给大脑充电，你给大脑跑压力测试。”
- **慢速巡航奖：{slow['name']}**，约 {int(slow['units_per_min']+.5)} 转写字词/分钟。文案：“知识还在路上，眼皮已经办理退休。”
- **语调先躺平奖：{flat['name']}**，局部音高起伏 {flat['pitch_iqr_st']:.2f} 半音。文案：“你负责输出观点，我负责降低屏幕亮度。”
- **语调蹦迪奖：{animated['name']}**，局部音高起伏 {animated['pitch_iqr_st']:.2f} 半音。文案：“音量可以克制，语调必须上桌跳舞。”
- **音量管理大师：{stable['name']}**，秒级音量起伏 {stable['loudness_range_db']:.1f} dB。文案：“后期把分贝驯服了，知识还在自由奔跑。”
- **分贝反复横跳奖：{spiky['name']}**，20 分钟共 {spiky['spikes_count']} 次规则检出的变响事件。文案：“刚找到一个舒服音量，下一句又让我重新做人。”事件可能来自句子重音、不同人电平、笑声或制作，未逐个试听分类。

以上文案是围绕本次声音特征的玩梗，不是在评价节目内容质量。

## 排名稳不稳

| 节目 | 权重变化下名次范围 | 5 个四分钟片段的名次范围 | 四分钟片段语速范围 |
|---|---|---|---|
'''
    for r in rows:
        text+=f"| {r['name']} | {r['weight_rank_min']}–{r['weight_rank_max']} | {r['window_rank_min']}–{r['window_rank_max']} | {r['block_rate_min']:.0f}–{r['block_rate_max']:.0f} 字词/分 |\n"
    text+='''
权重检查包括四项分别上下浮动 20% 后归一化的 16 种组合，以及等权组合。分段检查将各样本分成 5 段，以同一相对时间段重新比较。这些范围用于展示敏感性，**不是统计置信区间**。四分钟窗口不是独立节目样本，单集内变动也不能替代跨单集验证。

## 样本与时间点

音频完整解码后总长约 8.1 小时。文件有来自视频平台的音轨，也有播客平台导出文件；本轮反映用户提供的版本，后期处理差异也可能进入结果。所有抽样均按机械规则完成，没有为了名次挑选片段。

| 节目 | 单集 | 文件实际时长 | 本轮取样位置 |
|---|---|---|---|
'''
    for r in rows:
        text+=f"| {r['name']} | {r['episode']} | {stamp(r['full_duration_s'])} | {stamp(r['sample_start_s'])}–{stamp(r['sample_start_s']+r['sample_duration_s'])} |\n"
    text+='''
完整文件名、SHA-256、原始采样率、元数据和采样位置见 `manifest.json`；节目识别依据见项目根目录 `sample_catalog.json`。三五环文件中有疑似制作工具遗留的 artist/album 标签，未用这些标签替代用户文件名。

## 算法与依据

- 综合分 = 30% 语调平 + 30% 语速慢 + 25% 音量稳 + 15% 少突变。
- 各分项按这 5 个样本内的反向排名映射至 0–100，并列取平均；最终加权。增加参赛样本可能改变分数。
- 语调：每 5 秒内有效基频的半音四分位距，再取所有有效窗口中位数；未直接比较男女声的绝对音高。
- 语速：Whisper small 中文自动转写，汉字按字计、英文和数字按词或串计，除以完整片段时长，包括停顿。未人工逐字校对，图上按整数展示估计值。
- 音量起伏：语音占比至少一半的 1 秒 RMS 窗口，P90−P10 分贝差。
- 突发变响：同一秒级电平比前 10 秒语音窗口中位数高至少 6 dB，持续至少 0.5 秒，合并 2 秒内的事件。
- 说话人切换、笑声识别和内容无聊度本轮未计分，不能把其他指标冒充为这些结果。

理论只支持“值得测这些声音特征”的方向，不给出本项目的权重，也不证明分数与睡眠结果之间的关系：

1. [Scarratt et al. (2023), The audio features of sleep music](https://doi.org/10.1371/journal.pone.0278813)：225,626 首睡眠歌单曲目总体更轻、更慢，但存在较大个体选择差异。研究对象是音乐选择特征，不是播客催眠评分验证。
2. [Schewski et al. (2025), Measuring negative emotions and stress through acoustic correlates in speech](https://doi.org/10.1371/journal.pone.0328833)：综述 38 篇文章、39 项研究；某些情绪与基频、音量和语速有关，但不能反向推断听众是否困倦。

完整定义及首次试跑的窗口修正记录见 `../method-v0.1.md`（当前内容版本 v0.2）。

## 转写与质量检查

正式语速采用同一套 MLX Whisper small float16 本地模型，20 分钟分为 5 个四分钟块，固定中文、温度 0、不带前文续写。原音频未上传，本轮付费转写费用为 0。CPU Whisper small 的初步转写和用于核对节目身份的开头转写另行保留，不混入正式计分。

| 节目 | 总转写字词 | 自动标记待复核段数 | 相邻完全重复段数 |
|---|---:|---:|---:|
'''
    for r in rows:
        text+=f"| {r['name']} | {r['units']} | {len(r['asr_flagged_segments'])}/{r['asr_segment_count']} | {r['asr_repeat_adjacent']} |\n"
    text+='''
自动标记条件为平均 log probability < −0.8 或文本压缩比 > 2.4。未标记不等于转写准确，特别是英文专名、重叠讲话和口头语。没有进行真人助眠实验或逐分钟人工听写。本轮完成的是文件解码、计算、转写及数值和图表核对。

## 交付文件

- `01-催眠榜-数据原图.png`：可复算的数据榜单。
- `01-催眠榜-imagegen美化版.png`：已生成并目视核对名称、排名、分数和权重的主榜美化图。
- `02-语速与语调.png`：五个样本的真实数值散点图。
- `03-四项指标.png`：四项原始指标对比。
- `榜单与指标.csv`、`四分钟分段指标.csv`、`results.json`：详细数据及敏感性结果。
- `acoustics/`：语音检测、基频、音量中间数据和突发事件位置。
- `transcripts_mlx/`：计分用转写；`transcripts/`：初步 CPU 转写及身份核对。

imagegen 美化图使用内置工具生成，完整提示词与核对记录见 `imagegen-prompt.md`。精确数值和条形比例以数据原图和 CSV 为准。
'''
    (OUT/'首轮分析报告.md').write_text(text)
    copy=f'''# 即刻 / X 发布文案草案

## 即刻

开车听播客听困了，我干脆给 5 个单集跑了个 benchmark。

大模型卷智商，播客卷谁先把我送走（送去睡觉）。

每集取中间 20 分钟，算语速、语调起伏、音量稳定性和突发变响，再拼一个“催眠指数”。

这轮最高分：{top['name']}，{top['score']:.1f}。
嘴最快：{fast['name']}，约 {int(fast['units_per_min']+.5)} 转写字词/分钟。
语调最平：{flat['name']}。

最有意思的是：语调平、说得慢、音量稳，根本不是一回事。

你以为自己在吸收知识，大脑已经在申请强制关机。

只有 5 个单集样本，分数是自定义娱乐评分，不是入睡概率，也不代表节目质量。原始数值见图，欢迎提名下一轮参赛选手。

## X（短版草案）

给 5 个播客单集跑了个“催眠 benchmark”。

每集取中段 20 分钟，测语速、语调和音量。

本轮最高：{top['name']}（{top['score']:.1f}）。
嘴最快：{fast['name']}（约 {int(fast['units_per_min']+.5)} 字词/分）。

大模型卷智商，播客卷谁先把我大脑强制关机。

娱乐评分，只评这 5 段声音，不是入睡概率。👇

发布前可按账号字符限制拆为主帖与方法回复；本文件为草案，尚未发布。
'''
    (OUT/'社交媒体文案.md').write_text(copy)
    print('Wrote report and post drafts.')

if __name__=='__main__':main()
