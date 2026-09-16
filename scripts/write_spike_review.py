"""Write the evidence-led Markdown audit beside exported clips and plots."""
import json
from pathlib import Path
import numpy as np
from paths import OUT
D=OUT/'spike-review';r=json.loads((D/'review_data.json').read_text());s=next(x for x in r['sensitivity'] if x['id']=='s04')
# An explicit synthetic counterexample to the overlapping-window persistence rule.
power=np.full(400,.01);power[200]=1.0
level=10*np.log10(np.convolve(power,np.ones(10)/10,'valid'));base=np.full(len(level),np.nan)
for i in range(100,len(level)):base[i]=np.median(level[i-100:i])
m=level-base>=6;d=np.diff(np.r_[False,m,False].astype(int));runs=list(zip(np.flatnonzero(d==1),np.flatnonzero(d==-1)))
assert any(b-a>=5 for a,b in runs)
synth={'baseline_100ms_rms_dbfs':-20,'pulse_duration_s':.1,'pulse_rms_dbfs':0,'max_1s_delta_db':float(np.nanmax(level-base)), 'over_threshold_window_count':int(sum(m)), 'passes_existing_5_window_rule':True}
(D/'synthetic_persistence_check.json').write_text(json.dumps(synth,ensure_ascii=False,indent=2))
body='''# 张小珺访谈：突发变响指标复核

## 先说结论

**52 次能从现有算法精确复现，但不宜解释为 52 次“突然爆响”或“吓醒”。** 当前指标测的是相对近期语音电平的抬升，没有直接测声音上升速度，也没有做人耳惊吓标注。

- 对象：张小珺Jùn｜商业访谈录，《153. 和曾鸣聊产业史观：残酷的真相、会消亡的公司、优秀≠卓越、“OAI、Anth大概率不是原生时代大赢家”》。
- 分析区间：原音频 **01:07:11.5—01:27:11.5**，共 20 分钟；52 次 ÷ 20 × 10 = **26 次 / 10 分钟**。
- 从分析 WAV 重新计算了秒级 RMS，与缓存一致；六个样本全部事件的起点、终点、最大差值时间和差值均复现一致。
- 52 个事件中，47 个最大差值窗口的电平达到本片段语音窗口 P90 以上；因此不能把全部事件归因于“参照太轻、实际不响”。
- 但最大相对增幅与最响的声音不是同一个事件。事件 39 的参照很低（−34.62 dBFS），抬升到 −22.76 dBFS 就得到 +11.86 dB；事件 04 达到 −15.66 dBFS，实际数字电平更高，相对增幅却为 +10.40 dB。
- 本次完成信号、算法与已有自动转写复核，**没有进行人耳主观逐条标注**。下方原声供回听；转写可能有错字，不用转写断定说话人、笑声或情绪。

## 1. 原算法一步一步在算什么

源码：[`analyze.py`](../../../scripts/analyze.py)，主要逻辑在 `extract()`。

1. 将分析音频解码为 **16 kHz、单声道、16-bit PCM**。未逐片段调音量。
2. 每 100 毫秒计算一次均方功率，再将连续 10 个功率值平均，得到 1 秒 RMS 电平。步长 100 毫秒，因此相邻窗口重叠 90%。
3. 利用语音活动检测标记语音。1 秒窗口里，语音覆盖至少 50%，才会进入历史参照集合。
4. 对窗口起点 `t`，取起点在 `[t−10秒, t)` 内的合格历史窗口；至少有 20 个才计算其中位电平。注意这些是重叠窗口，不是 20 秒独立语音。
5. 当前窗口电平减去这个中位数，达到 **6 dB**，且连续至少 **5 个步长**满足条件，就成为候选。
6. 两个候选时间点相隔不超过 2 秒则合并成一个事件；保留最大差值及其窗口起点，最后换算为每 10 分钟次数。

```text
L(t) = 10 × log10(mean(x²，窗口 [t, t+1 秒)))
B(t) = median(此前 10 秒内语音占比 ≥50% 的 L)
Δ(t) = L(t) − B(t)
候选 = Δ(t) ≥6 dB，连续至少 5 个 100 毫秒步长
```

### 为什么它可能与听感不符

- **没有测“突发”速度。** 正常重音、说话由轻到重、轮到另一个更响的说话人，都可能过线；目前没有说话人音量校正，也没有音效/笑声分类。
- **持续性条件容易误读。** 五个连续窗口覆盖 1.4 秒原声，但高度重叠；同一个短声音能使多个窗口过线。这不是原声连续高音量 0.5 秒的证明。
- **合并后的事件不是全程持续变响。** 中间最多可以有约 2 秒候选间隔；表格和图上浅红色是窗口覆盖范围。
- **时间戳指窗口起点。** `peak_s` 代表最大差值的 1 秒窗口起点，不是瞬时振幅最高点；图中曲线按中心 `t+0.5秒` 绘制。历史窗口与当前窗口也可能共享最多 0.9 秒原声。
- **数字电平不等于耳边音量。** dBFS 是音频文件的电平；此处没有播放设备音量或耳边声压测量。
- 原代码只用语音掩码筛历史参照，未强制当前窗口属于语音。但加上当前语音门限后，本次六个样本计数均不变，因此它不是这期异常高计数的解释。

**重叠窗口的反例验证：** 在 −20 dBFS 的恒定底音里放入一个 100 毫秒、0 dBFS 的脉冲，1 秒平均后约上升 10.37 dB，连续 10 个窗口过线，会通过现有持续条件。这个合成信号只用于验证规则缺陷，不是播客中的实测事件。详见 `synthetic_persistence_check.json`。

## 2. 全片段概览

蓝线为电平，橙线为动态门槛，红点为事件最大差值窗口。下方分布图比较全部语音窗口与事件窗口；谱图中的颜色不用于判断“惊吓”。

![20 分钟全览](00-overview.png)

## 3. 参数敏感性

以下仅为诊断，**没有修改正式榜单或重新定权重**。所有数字为整段 20 分钟内的事件次数；每 10 分钟需再除以 2。

| 栏目 | ≥6 dB（现有） | ≥8 dB | ≥10 dB | 6 dB、10 个连续窗口 | 6 dB、15 个连续窗口 | 历史改用 P75 +6 dB |
|---|---:|---:|---:|---:|---:|---:|
'''
for q in r['sensitivity']:
 body+='| '+q['show'].replace('|','｜')+' | '+' | '.join(str(q[k]) for k in ['threshold_6dB_count','threshold_8dB_count','threshold_10dB_count','persist_1s_count','persist_1_5s_count','past_P75_count'])+' |\n'
body+='''
张小珺这期随阈值提高从 **52 → 16 → 3**；要求 10 个连续窗口为 **23** 次，15 个为 **4** 次，历史参照改 P75 为 **11** 次。说明绝对次数对定义很敏感；但它在这些方案里依然最多，不能据此直接把这项差异抹掉。更严格的规则也不自动等于更符合听感，需要同一批人工标注来校准。

## 4. 六个触发样本：原声 + 音量曲线 + 时频谱 + 功率谱

按“最大增幅、最高电平、典型增幅、最低电平、刚过阈值、最长合并事件”选样，不是只挑支持某种判断的片段。每段保留事件前 12 秒与后 8 秒；相邻事件的片段可能重叠。

音频直接从用户的原始文件导出为 **48 kHz 双声道 WAV**，未单独归一化、加增益或动态压缩；频谱基于实际参与评分的 **16 kHz 单声道**副本，因此仅展示 0—8 kHz。回听时保持播放器音量一致。

读图方法：第一行波形，第二行秒级电平和参照，第三行时间—频率图，第四行当前 1 秒与历史语音参照的平均功率谱。所有样本时频图统一色标 −100 至 −35 dB re 1 FS^2/Hz；功率谱是每 Hz 功率密度，不是声压或感知响度。历史谱按入选的重叠语音窗口平均功率；它不是原算法使用的标量中位电平。

| 事件 | 选择原因 | 原文件窗口起点 | 相对增幅 | 当前电平 | 参照电平 | 播放后重点位置 |
|---|---|---|---:|---:|---:|---:|
'''
for q in r['selected']:
 body+=f"| {q['event']:02d} | {q['reason']} | {q['original_peak_window_start']} | +{q['max_delta_db']:.2f} dB | {q['level_dbfs']:.2f} dBFS | {q['baseline_dbfs']:.2f} dBFS | {q['event_at_clip_s']:.1f} 秒 |\n"
for q in r['selected']:
 body+=f"\n### 事件 {q['event']:02d}：{q['reason']}\n\n原音频 {q['clip_start_original']}—{q['clip_end_original']}，最大差值窗口在播放后 **{q['event_at_clip_s']:.1f} 秒**。\n\n自动转写定位（未人工校对）：{q['transcript_auto']}\n\n![原声片段]({q['audio']})\n\n[下载 WAV]({q['audio']}) · [查看完整图]({q['figure']})\n\n![事件诊断图]({q['figure']})\n"
body+='''
## 5. 接下来怎样改才有依据

目前建议先把该项理解为 **“局部音量抬升次数”**，不要将 26 次 / 10 分钟表述为“爆响/吓醒次数”。这次只诊断，没有改名或重算已发布图。

如果仍想保留“突发变响”的含义，应先回听这些片段，标注“明显突然变响 / 正常语句重音或起句 / 说话人切换 / 音效或笑声 / 不确定”，并加入六个节目中未触发的对照片段。再统一评估上升速度、非重叠短窗持续性、参照分位数和事件合并规则，检查误报与漏报；不能只为了让一档节目的数值看起来合理而调阈值。

## 复核文件

- [52 个事件明细 CSV](all_52_events.csv)：完整时间、增幅、基准、当前电平、转写定位。
- [六个节目参数敏感性 CSV](threshold_sensitivity.csv)。
- [机器可读复核数据](review_data.json)。
- [重叠窗口持续性反例](synthetic_persistence_check.json)。
- [复现脚本](../../../scripts/review_spikes.py)、[报告生成脚本](../../../scripts/write_spike_review.py)。

运行：`PODCAST_OUTPUT_DIR=output/batch-06 .venv/bin/python scripts/review_spikes.py`，随后运行同目录的 `scripts/write_spike_review.py`。
'''
(D/'张小珺-突发变响复核.md').write_text(body)
print(D/'张小珺-突发变响复核.md')
