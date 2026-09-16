"""Source-backed standalone PNG charts for 即刻/X; never draw invented scores."""
from pathlib import Path
import json
import os
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'cache'/'matplotlib'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'
FONT='/System/Library/Fonts/Hiragino Sans GB.ttc'
font_manager.fontManager.addfont(FONT)
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=FONT).get_name(),'axes.unicode_minus':False,
 'savefig.facecolor':'#f6f5ef','figure.facecolor':'#f6f5ef','text.color':'#20242c','axes.labelcolor':'#20242c'})
INK='#20242c';MUTED='#777b85';BLUE='#384bf5';GOLD='#ffc85b';BG='#f6f5ef'
COLORS={'s01':'#eb8e5b','s02':BLUE,'s03':'#8b80bd','s04':'#657976','s05':'#c77495'}

def main():
    results=json.loads((OUT/'results.json').read_text());rows=results['rows']
    # Explicit pixels through figsize × dpi; intended as standalone social graphics.
    fig=plt.figure(figsize=(12,9),dpi=180)
    ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
    ax.text(.06,.945,'PILLOW BENCH  /  播客催眠评测',fontsize=13,color=BLUE,weight='bold')
    ax.text(.94,.945,'v0.2 · 首轮试跑',fontsize=11,color=MUTED,ha='right')
    ax.text(.06,.86,'谁把播客讲成了关机键？',fontsize=31,weight='bold')
    ax.text(.06,.808,'5 个单集 × 中段 20 分钟   /   声音越平、越慢、越稳，分数越高',fontsize=12,color=MUTED)
    ax.plot([.06,.94],[.768,.768],color=INK,lw=1)
    ax.text(.06,.739,'排名',fontsize=10,color=MUTED)
    ax.text(.135,.739,'参赛单集',fontsize=10,color=MUTED)
    ax.text(.565,.739,'催眠指数  ·  样本内相对分',fontsize=10,color=MUTED)
    ax.text(.94,.739,'0–100',fontsize=10,color=MUTED,ha='right')
    for i,r in enumerate(rows):
        y=.663-i*.104
        if i==0:
            ax.add_patch(FancyBboxPatch((.044,y-.041),.912,.088,boxstyle='round,pad=.006,rounding_size=.012',fc='#e7e9ff',ec='none'))
        ax.text(.06,y,f"{r['rank']:02d}",fontsize=24,color=BLUE if i==0 else MUTED,va='center')
        ax.text(.135,y+.012,r['name'],fontsize=16,weight='bold',va='center')
        ax.text(.135,y-.020,r['short'],fontsize=10,color=MUTED,va='center')
        ax.add_patch(FancyBboxPatch((.565,y-.008),.265,.014,boxstyle='round,pad=0,rounding_size=.007',fc='#e1e2e8',ec='none'))
        ax.add_patch(FancyBboxPatch((.565,y-.008),.265*r['score']/100,.014,boxstyle='round,pad=0,rounding_size=.007',fc=BLUE if i==0 else '#9ca4dc',ec='none'))
        ax.text(.94,y,f"{r['score']:.1f}",fontsize=26,weight='bold',va='center',ha='right')
    ax.plot([.06,.94],[.176,.176],color=INK,lw=1)
    ax.text(.06,.136,'计分配方',fontsize=11,weight='bold')
    ax.text(.178,.136,'语调平 30%   +   语速慢 30%   +   音量稳 25%   +   少突变 15%',fontsize=11)
    ax.text(.06,.088,'只评这 5 段声音，不代表整档节目；分数是自定义娱乐评分，不是入睡概率。',fontsize=10,color=MUTED)
    ax.text(.06,.054,'中文自动转写 · 秒级 RMS 音量 · 局部相对音高 · 原始数据可复核',fontsize=9,color=MUTED)
    fig.savefig(OUT/'01-催眠榜-数据原图.png',dpi=180);plt.close(fig)

    fig,ax=plt.subplots(figsize=(12,8),dpi=180)
    fig.subplots_adjust(left=.12,right=.93,bottom=.17,top=.75)
    fig.text(.08,.925,'PILLOW BENCH  /  语速 × 语调',fontsize=12,color=BLUE)
    fig.text(.08,.855,'有的语调躺平，有的自带弹幕',fontsize=27,weight='bold')
    x=np.array([r['units_per_min'] for r in rows]);y=np.array([r['pitch_iqr_st'] for r in rows])
    # Data-space coordinates, no quadrant implying clinical sleep outcomes.
    ax.axvline(np.median(x),ls='--',lw=1,color='#c1c2c8');ax.axhline(np.median(y),ls='--',lw=1,color='#c1c2c8')
    offsets={'s01':(-8,16),'s02':(10,-22),'s03':(-10,16),'s04':(10,10),'s05':(-8,16)}
    for r in rows:
        ax.scatter(r['units_per_min'],r['pitch_iqr_st'],s=230,color=COLORS[r['id']],edgecolor=BG,linewidth=2,zorder=3)
        dx,dy=offsets[r['id']]
        ax.annotate(r['name'],(r['units_per_min'],r['pitch_iqr_st']),xytext=(dx,dy),textcoords='offset points',fontsize=12,
                    ha='right' if dx<0 else 'left',color=INK)
    ax.set_xlim(min(x)-30,max(x)+40);ax.set_ylim(min(y)-.5,max(y)+.6)
    ax.set_xlabel('语速：自动转写字词 / 分钟  →  越右越快',fontsize=12,labelpad=14)
    ax.set_ylabel('语调起伏：局部音高四分位距 / 半音\n越高起伏越大',fontsize=12,labelpad=14)
    ax.grid(alpha=.2);ax.set_facecolor(BG)
    for side in ['top','right']:ax.spines[side].set_visible(False)
    ax.spines['left'].set_color('#b5b5bd');ax.spines['bottom'].set_color('#b5b5bd')
    fig.text(.08,.055,'每点为一个单集的 20 分钟样本；虚线为本组中位数。声音特征不等于实际睡眠效果。',fontsize=10,color=MUTED)
    fig.savefig(OUT/'02-语速与语调.png',dpi=180);plt.close(fig)

    fig,axes=plt.subplots(1,4,figsize=(16,8),dpi=150)
    fig.subplots_adjust(left=.16,right=.96,top=.74,bottom=.23,wspace=.45)
    fig.text(.055,.925,'PILLOW BENCH  /  指标拆解',fontsize=13,color=BLUE)
    fig.text(.055,.84,'别光看总分，把嘴拆开看',fontsize=29,weight='bold')
    fields=[('units_per_min','语速','转写字词 / 分钟',0),('pitch_iqr_st','语调起伏','半音',2),
            ('loudness_range_db','音量起伏','dB',1),('spikes_per_10min','突发变响','次 / 10 分钟',1)]
    pos=np.arange(len(rows))
    for j,(ax,(key,title,unit,dec)) in enumerate(zip(axes,fields)):
        vals=[r[key] for r in rows]
        ax.barh(pos,vals,color=BLUE if j==0 else '#a7aedf',height=.43)
        ax.set_yticks(pos,labels=[r['name'] for r in rows] if j==0 else ['']*5,fontsize=12);ax.invert_yaxis()
        ax.set_title(title+'\n'+unit,fontsize=13,pad=20);ax.set_xlim(0,max(vals)*1.38)
        ax.set_facecolor(BG);ax.xaxis.grid(True,alpha=.2);ax.set_axisbelow(True)
        for i,v in enumerate(vals):ax.text(v+max(vals)*.035,i,str(int(v+.5)) if dec==0 else f'{v:.{dec}f}',va='center',fontsize=12)
        for spine in ['top','right','left']:ax.spines[spine].set_visible(False)
        ax.tick_params(axis='y',length=0);ax.spines['bottom'].set_color('#b5b5bd')
    fig.text(.055,.125,'四项都是数值越低、对应催眠分越高。不同指标的坐标单位不同，不能直接比较柱长。',fontsize=11,color=MUTED)
    fig.text(.055,.077,'突发变响：秒级音量比前 10 秒语音参照高 ≥6 dB，并持续至少 0.5 秒；并非真实惊醒次数。',fontsize=11,color=MUTED)
    fig.savefig(OUT/'03-四项指标.png',dpi=150);plt.close(fig)
    print('Saved three source-backed charts.')

if __name__=='__main__':main()
