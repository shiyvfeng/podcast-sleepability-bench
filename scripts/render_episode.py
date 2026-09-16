"""Render three data charts using full episode titles and English paper titles."""
import hashlib
import json
import os
import unicodedata
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'cache'/'matplotlib'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
from matplotlib.transforms import ScaledTranslation
from paths import OUT

FONT='/System/Library/Fonts/Hiragino Sans GB.ttc'
font_manager.fontManager.addfont(FONT)
INK='#20242c';MUTED='#666b77';PURPLE='#384bf5';BG='#f6f5ef'
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=FONT).get_name(),
 'font.weight':300,'axes.titleweight':300,'axes.unicode_minus':False,
 'figure.facecolor':BG,'savefig.facecolor':BG,'text.color':INK,'axes.labelcolor':INK})
EPISODES={
 's01':'AI时代是谁的黄金时代？｜和张咋啦聊：文科生、积极行动、爆款的规律、普通人也能赢',
 's02':'No.233 单口｜手机为什么要折叠？Apple 为什么要「跟风」？',
 's03':'全面解析“世界模型”：定义、路线、实践与AGI的更近一步',
 's04':'153. 和曾鸣聊产业史观：残酷的真相、会消亡的公司、优秀≠卓越、“OAI、Anth大概率不是原生时代大赢家”',
 's05':'#22 在风口也在浪尖：8年TikTok到Meta，做影响十亿人的产品',
 's06':'蒸馏Liblib陈冕：关于成为神的时刻',
}
SHOWS={
 's01':'十字路口Crossing', 's02':'三五环', 's03':'硅谷101',
 's04':'张小珺Jùn｜商业访谈录', 's05':'鹿鹿鱼鱼', 's06':'葬AI',
}
PAPERS=[
 'Scarratt et al. (2023). The audio features of sleep music: Universal and subgroup characteristics.',
 'Schewski et al. (2025). Measuring negative emotions and stress through acoustic correlates in speech: A systematic review.',
]
COLORS={'s01':'#eb8e5b','s02':PURPLE,'s03':'#8b80bd','s04':'#657976','s05':'#c77495','s06':'#657976'}
AUDIT=[]

def wrap_title(s,width):
    """Wrap at character boundaries without dropping any part of the title."""
    lines=[];line='';size=0
    for char in s:
        step=2 if unicodedata.east_asian_width(char) in ('W','F') else 1
        if size+step>width and line:
            lines.append(line);line='';size=0
        line+=char;size+=step
    if line:lines.append(line)
    return '\n'.join(lines)

def header(fig,title,subtitle):
    fig.text(.055,.939,title,fontsize=26,color=PURPLE,weight=600,va='center')
    fig.text(.055,.889,subtitle,fontsize=12,color=MUTED,va='center')

def episode_label(fig,x,y,sid,width,fontsize,transform,weight=300):
    title=wrap_title(EPISODES[sid],width)
    height=fontsize*(1+1.5*title.count('\n'))
    top=(height+17)/2
    for text,offset,size,color,bold in [
        (SHOWS[sid],top,10.5,PURPLE,600),
        (title,top-17,fontsize,INK,weight),
    ]:
        fig.text(x,y,text,transform=transform+ScaledTranslation(0,offset/72,fig.dpi_scale_trans),
                 fontsize=size,color=color,weight=bold,ha='left',va='top',linespacing=1.5)

def footer(fig,methods):
    fig.add_artist(Line2D([.055,.945],[.211,.211],transform=fig.transFigure,color='#b7bac4',lw=.8))
    lines=['理论依据｜'+PAPERS[0],'　　　　　'+PAPERS[1],*methods,
           '说明｜仅比较所选单集片段；自定义娱乐评分，不代表整档节目或实际入睡效果。']
    for y,line in zip([.178,.147,.116,.085,.049],lines):
        fig.text(.055,y,line,fontsize=10.5,color=MUTED,va='center')

def save(fig,filename,rows):
    fig.canvas.draw();renderer=fig.canvas.get_renderer();excluded=set()
    for ax in fig.axes:
        if not ax.axison:
            excluded.update(id(t) for axis in [ax.xaxis,ax.yaxis] for t in axis.findobj(matplotlib.text.Text));continue
        for coords,labels,limits in [(ax.get_xticks(),ax.get_xticklabels(),ax.get_xlim()),(ax.get_yticks(),ax.get_yticklabels(),ax.get_ylim())]:
            lo,hi=sorted(limits)
            excluded.update(id(t) for v,t in zip(coords,labels) if not lo<=v<=hi)
    texts=[t for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text() and id(t) not in excluded]
    for t in texts:
        b=t.get_window_extent(renderer);full=fig.bbox
        assert b.x0>=-1 and b.y0>=-1 and b.x1<=full.width+1 and b.y1<=full.height+1, f'Clipped: {t.get_text()}'
    all_text='\n'.join(t.get_text() for t in texts)
    normalized=''.join(all_text.split())
    for r in rows:
        assert ''.join(EPISODES[r['id']].split()) in normalized
        assert SHOWS[r['id']] in all_text
    for paper in PAPERS:assert paper in all_text
    assert '分析方法' in all_text and 'http' not in all_text
    for old_label in ['补跑','新增']:
        assert old_label not in all_text,old_label
    fig.savefig(OUT/filename,dpi=fig.dpi)
    AUDIT.append(dict(file=filename,pixels=[int(fig.bbox.width),int(fig.bbox.height)],
        full_episode_titles=[EPISODES[r['id']] for r in rows],show_names=[SHOWS[r['id']] for r in rows],papers=PAPERS,text_bounds='passed'))
    plt.close(fig)

def main():
    source=OUT/'results.json';data=json.loads(source.read_text());rows=data['rows'];n=len(rows)
    assert n==6
    # Each label pairs the show name with the full episode title.
    fig=plt.figure(figsize=(16,11),dpi=180)
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    header(fig,'PILLOW BENCH  /  播客催眠评测','6 个单集 × 中段 20 分钟  /  分数越高，声音特征越偏平缓')
    ax.plot([.055,.945],[.847,.847],color=INK,lw=1)
    for x,title,ha in [(.055,'排名','left'),(.135,'栏目 / 单集标题','left'),(.70,'催眠指数 · 样本内相对分','left'),(.945,'0–100','right')]:
        ax.text(x,.821,title,fontsize=11,color=MUTED,ha=ha,va='center')
    for i,r in enumerate(rows):
        y=.758-i*.094
        if i==0:ax.add_patch(FancyBboxPatch((.043,y-.040),.914,.080,boxstyle='round,pad=.003,rounding_size=.01',fc='#e7e9ff',ec='none'))
        ax.text(.055,y,f"{r['rank']:02d}",fontsize=24,color=PURPLE if i==0 else MUTED,va='center')
        if sum(q['rank']==r['rank'] for q in rows)>1:ax.text(.099,y,'并列',fontsize=9,color=MUTED,va='center')
        episode_label(fig,.135,y,r['id'],80,13.5,ax.transData,weight=600)
        for length,color in [(.16,'#e1e2e8'),(.16*r['score']/100,PURPLE if i==0 else '#9ca4dc')]:
            ax.add_patch(FancyBboxPatch((.70,y-.006),length,.012,boxstyle='round,pad=0,rounding_size=.006',fc=color,ec='none'))
        ax.text(.945,y,f"{r['score']:.1f}",fontsize=26,weight=600,va='center',ha='right')
    footer(fig,['分析方法｜6 个单集共 120 分钟；四项原始指标取反向排名分，再按权重加总。',
                '计分权重｜语调平 30% ＋ 语速慢 30% ＋ 音量稳 25% ＋ 少突变 15%。'])
    save(fig,'01-播客催眠评测.png',rows)

    # Numbered dots map to full episode titles in an adjacent key to avoid overlapping labels.
    fig=plt.figure(figsize=(18,11),dpi=160)
    ax=fig.add_axes([.09,.31,.51,.51])
    header(fig,'PILLOW BENCH  /  语速 × 语调','6 个单集 × 中段 20 分钟  /  虚线为本组中位数；编号用于对应右侧单集标题')
    x=np.array([r['units_per_min'] for r in rows]);y=np.array([r['pitch_iqr_st'] for r in rows])
    ax.axvline(np.median(x),ls='--',lw=1,color='#bfc2ce');ax.axhline(np.median(y),ls='--',lw=1,color='#bfc2ce')
    fig.text(.665,.818,'栏目 / 单集标题',fontsize=12,color=MUTED)
    for i,r in enumerate(rows):
        ax.scatter(r['units_per_min'],r['pitch_iqr_st'],s=255,color=COLORS[r['id']],edgecolor=BG,linewidth=1.5,zorder=3,marker='D' if r['id']=='s06' else 'o')
        ax.annotate(f'{i+1:02d}',(r['units_per_min'],r['pitch_iqr_st']),xytext=(11,5),textcoords='offset points',fontsize=12,color=INK)
        yy=.755-i*.089
        fig.text(.63,yy,f'{i+1:02d}',fontsize=14,color=COLORS[r['id']],weight=600,va='center')
        episode_label(fig,.665,yy,r['id'],58,11.2,fig.transFigure)
    ax.set(xlim=(min(x)-18,max(x)+20),ylim=(min(y)-.4,max(y)+.4))
    ax.set_xlabel('语速：自动转写字词 / 分钟  →  越右越快',fontsize=12,labelpad=15)
    ax.set_ylabel('语调起伏：半音  →  越高起伏越大',fontsize=12,labelpad=15)
    ax.grid(alpha=.18);ax.set_facecolor(BG);ax.tick_params(labelsize=11)
    for side in ['top','right']:ax.spines[side].set_visible(False)
    for side in ['left','bottom']:ax.spines[side].set_color('#b5b5bd')
    footer(fig,['分析方法｜语速＝自动转写字词数 ÷ 20 分钟（含停顿）；语调为局部相对音高起伏。',
                '语调计算｜每 5 秒取有效基频的半音四分位距，再取所有有效窗口的中位数。'])
    save(fig,'02-语速与语调.png',rows)

    fig,axes=plt.subplots(1,4,figsize=(18,11),dpi=160)
    fig.subplots_adjust(left=.44,right=.955,top=.795,bottom=.30,wspace=.44)
    header(fig,'PILLOW BENCH  /  指标拆解','6 个单集 × 中段 20 分钟  /  四项原始指标均为越低、对应催眠分越高')
    fields=[('units_per_min','语速','转写字词 / 分钟',0),('pitch_iqr_st','语调起伏','半音',2),
            ('loudness_range_db','音量起伏','dB',1),('spikes_per_10min','突发变响','次 / 10 分钟',1)]
    pos=np.arange(n)
    for j,(ax,(key,title,unit,dec)) in enumerate(zip(axes,fields)):
        vals=[r[key] for r in rows]
        ax.barh(pos,vals,color=PURPLE if j==0 else '#a7aedf',height=.38)
        ax.set_yticks(pos,labels=['']*n);ax.invert_yaxis()
        ax.set_title(title+'\n'+unit,fontsize=12,pad=20)
        ax.set_xlim(0,max(vals)*1.45);ax.set_facecolor(BG);ax.xaxis.grid(True,alpha=.18);ax.set_axisbelow(True)
        if j==0:
            for i,r in enumerate(rows):
                # Fixed left edge aligns all wrapped episode titles.
                episode_label(fig,-.385/ax.get_position().width,i,r['id'],78,11.1,ax.get_yaxis_transform())
        for i,v in enumerate(vals):
            ax.text(v+max(vals)*.04,i,str(int(v+.5)) if dec==0 else f'{v:.{dec}f}',va='center',fontsize=11.5)
        for side in ['top','right','left']:ax.spines[side].set_visible(False)
        ax.tick_params(axis='y',length=0);ax.tick_params(axis='x',labelsize=10);ax.spines['bottom'].set_color('#b5b5bd')
    footer(fig,['分析方法｜语速由自动转写计数；语调取局部半音四分位距；音量取语音段秒级 RMS 的 P90 与 P10 之差。',
                '突发变响｜比前 10 秒语音参照高 ≥6 dB、持续 ≥0.5 秒；合并 2 秒内事件，折算至每 10 分钟。'])
    save(fig,'03-四项指标.png',rows)
    (OUT/'chart_verification.json').write_text(json.dumps(dict(source='results.json',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),charts=AUDIT),ensure_ascii=False,indent=2))
    print('Saved 3 charts: show names and full episode titles; English paper titles; values unchanged.')

if __name__=='__main__':main()
