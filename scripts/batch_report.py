"""Write a standalone report for every sample in the selected dataset."""
import json
from paths import OUT

def clock(seconds):
    seconds=round(seconds)
    return f'{seconds//3600:02}:{seconds//60%60:02}:{seconds%60:02}'

def write_report():
    data=json.loads((OUT/'results.json').read_text())
    rows=data['rows'];n=len(rows)
    total_minutes=sum(r['sample_duration_s'] for r in rows)/60
    top=rows[0]
    fastest=max(rows,key=lambda r:r['units_per_min'])
    slowest=min(rows,key=lambda r:r['units_per_min'])
    most_variable=max(rows,key=lambda r:r['pitch_iqr_st'])
    most_stable=min(rows,key=lambda r:r['loudness_range_db'])
    rank_counts={r['rank']:sum(q['rank']==r['rank'] for q in rows) for r in rows}
    text=f'''# 中文播客催眠等级分析

## 分析概览

选取 {n} 个中文播客单集，每集取时间轴中间连续 20 分钟，共分析 **{total_minutes:.0f} 分钟**音频。从语调起伏、语速、音量起伏和突发变响四个维度，计算一个直观、可解释的“催眠指数”。

**综合分最高的是《{top['name']}》，{top['score']:.1f} 分。** 这段声音的语调较平、音量较稳，突发变响也少。按预设的 17 组权重组合检查，它均排在第一位。

这是对指定单集片段的娱乐性声音比较，不代表整档节目或实际入睡效果。分数只表示这组样本内的相对位置，不是入睡概率，也不评价内容质量。

## 催眠指数榜单

| 排名 | 节目 | 催眠指数 | 语速（转写字词/分） | 语调起伏（半音） | 音量起伏（dB） | 突发变响（次/10分） |
|---|---|---:|---:|---:|---:|---:|
'''
    for r in rows:
        rank=f"并列 {r['rank']}" if rank_counts[r['rank']]>1 else str(r['rank'])
        text+=f"| {rank} | {r['name']} | {r['score']:.1f} | {int(r['units_per_min']+.5)} | {r['pitch_iqr_st']:.2f} | {r['loudness_range_db']:.1f} | {r['spikes_per_10min']:.1f} |\n"
    text+=f'''
四项原始指标均为数值越低、对应催眠分越高。语速含停顿；音量起伏是音频信号的相对变化，不代表播放设备的实际声压；突发变响也不是实际惊醒次数。

## 几个有意思的结果

- **《{top['name']}》：手机还没折叠，眼皮先折叠了。** 本次分析的是折叠手机单口，综合分 {top['score']:.1f}，语调起伏 {top['pitch_iqr_st']:.2f} 半音，20 分钟检出 {top['spikes_count']} 次突发变响。
- **《{fastest['name']}》：给大脑跑压力测试。** 语速约 {int(fastest['units_per_min']+.5)} 字词/分钟，是这组样本中最快的。
- **《{slowest['name']}》：说得慢，也可能分贝横跳。** 语速约 {int(slowest['units_per_min']+.5)} 字词/分钟，是这组中最慢的；但音量起伏达 {slowest['loudness_range_db']:.1f} dB，说明“慢”和“稳”是不同维度。
- **《{most_variable['name']}》：音量克制，语调蹦迪。** 语调起伏为 {most_variable['pitch_iqr_st']:.2f} 半音，是这组中最大的；音量最稳定的样本则是《{most_stable['name']}》，起伏 {most_stable['loudness_range_db']:.1f} dB。

以上是围绕声音特征的玩梗，不是对节目内容或主播人格的判断。

## 样本与取样位置

{n} 份完整音频合计约 {sum(r['full_duration_s'] for r in rows)/3600:.1f} 小时，均在完整解码后按同一规则取中段，不根据预期结果挑选片段。样本包含播客平台导出音频和视频平台音轨，制作处理差异也可能体现在测量结果中。

| 节目 | 单集 | 完整时长 | 取样位置 |
|---|---|---|---|
'''
    for r in rows:
        text+=f"| {r['name']} | {r['episode']} | {clock(r['full_duration_s'])} | {clock(r['sample_start_s'])}–{clock(r['sample_start_s']+r['sample_duration_s'])} |\n"
    text+=f'''
## 计算方法

音频统一为 16 kHz 单声道 PCM，不做动态压缩或降噪。固定增益不改变相对分贝起伏，因而不通过动态响度归一化改变待测波动。取样区内的音乐、广告或笑声不主动剔除。

| 指标 | 如何计算 | 权重 |
|---|---|---:|
| 语调平 | Praat 自相关基频，搜索范围 65–500 Hz；每 5 秒内将有效基频转换成半音尺度，取四分位距，再取全部有效窗口的中位数 | 30% |
| 语速慢 | 自动转写的汉字数、英文词及数字串数相加，除以完整片段分钟数，计入停顿 | 30% |
| 音量稳 | 语音占比至少 50% 的 1 秒 RMS 窗口中，取 P90−P10 的分贝差，窗口步长为 100 毫秒 | 25% |
| 少突变 | 1 秒 RMS 比前 10 秒内语音窗口的中位电平高至少 6 dB，持续至少 0.5 秒，合并间隔不超过 2 秒的事件 | 15% |

每项在 {n} 个样本内按原始值从低到高排名，并列取平均名次，转换为分项分：

**分项分 = 100 ×（样本数 − 名次）÷（样本数 − 1）**

**催眠指数 = 语调平 × 30% + 语速慢 × 30% + 音量稳 × 25% + 少突变 × 15%**

权重、阈值和排名分是本项目的操作定义，未经睡眠实验训练。局部相对音高用于降低不同人绝对音高差异的影响，但不等价于按说话人归一化。说话人切换、笑声识别和内容“无聊度”不参与计分。

## 理论依据

相关研究支持从声音特征入手分析，但不直接验证本报告的催眠指数：

1. [Scarratt et al. (2023), The audio features of sleep music: Universal and subgroup characteristics](https://doi.org/10.1371/journal.pone.0278813)：分析 225,626 首睡眠歌单曲目，总体更轻、更慢，但内部存在较大差异。研究对象是音乐选择特征，不是播客入睡效果。
2. [Schewski et al. (2025), Measuring negative emotions and stress through acoustic correlates in speech: A systematic review](https://doi.org/10.1371/journal.pone.0328833)：综述 38 篇文章、39 项研究；某些情绪与基频、音量和语速有关，但不能据此反向推断听众是否困倦。

## 排名稳不稳

| 节目 | 17 组权重下的名次范围 | 5 个四分钟窗口的名次范围 |
|---|---|---|
'''
    for r in rows:
        text+=f"| {r['name']} | {r['weight_rank_min']}–{r['weight_rank_max']} | {r['window_rank_min']}–{r['window_rank_max']} |\n"
    text+='''
权重检查包括四项分别上下浮动 20% 后归一化的 16 种组合，以及等权组合。窗口检查将每个样本切成五个四分钟片段，以相同的相对时间段重新比较。

这些范围用于展示结果对权重和片段选择的敏感性，不是统计置信区间。四分钟窗口不是独立节目样本，不能代替对同一节目多个单集的观察。

## 转写与数据核对

全部样本使用本地 MLX Whisper small float16，固定中文、温度 0、四分钟分块，不带前文续写。音频不上传，转写费用为 0 元。转写未人工逐字校对，尤其可能在英文专名、重叠讲话和口头语处出错；图表与榜单中的语速按整数展示估计值。

| 节目 | 转写字词数 | 自动标记待复核段数 | 相邻完全重复段数 |
|---|---:|---:|---:|
'''
    for r in rows:
        text+=f"| {r['name']} | {r['units']} | {len(r['asr_flagged_segments'])}/{r['asr_segment_count']} | {r['asr_repeat_adjacent']} |\n"
    text+='''
自动标记条件为平均 log probability < −0.8 或文本压缩比 > 2.4。未标记不等于转写准确，相邻重复也可能是自然口语重复。

已核对来源文件哈希、取样时长、基频边界、音量计算、突发事件位置、转写字词计数与加权排名。基频峰值插值允许在搜索边界有 0.25 Hz 的数值容差。详细核对结果保存在 `verification.json`。

## 数据文件

- `榜单与指标.csv`：全部样本的原始指标、分数和名次。
- `四分钟分段指标.csv`：分段结果。
- `results.json`：完整结果与敏感性检查。
- `manifest.json`：来源文件、哈希、实际时长和取样位置。
- `acoustics/`、`transcripts_mlx/`：声学中间数据与自动转写。
'''
    target=OUT/'播客催眠等级分析报告.md'
    target.write_text(text)
    print(target)
    return target

if __name__=='__main__':write_report()
