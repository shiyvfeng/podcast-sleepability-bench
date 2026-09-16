"""Read-only audit of v0.2 spikes; preserves scores and source analysis."""
import os,json,csv,hashlib,subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import imageio_ffmpeg
from paths import ROOT,OUT
from render_episode import SHOWS
D=OUT/'spike-review';D.mkdir(exist_ok=True)
font_manager.fontManager.addfont('/System/Library/Fonts/Hiragino Sans GB.ttc')
plt.rcParams.update({'font.family':'Hiragino Sans GB','font.weight':300,'axes.unicode_minus':False,'font.size':11,'figure.facecolor':'#f6f5ef','savefig.facecolor':'#f6f5ef'})

def runs(m):
 d=np.diff(np.r_[False,m,False].astype(int));return list(zip(np.flatnonzero(d==1),np.flatnonzero(d==-1)))
def detect(delta,threshold=6,min_steps=5):
 ev=[]
 for a,b in runs(delta>=threshold):
  if b-a<min_steps:continue
  for i in range(a,b):
   if ev and i-ev[-1]['last_i']<=20:
    e=ev[-1];e['last_i']=i
    if delta[i]>delta[e['peak_i']]:e['peak_i']=i
   else:ev.append(dict(start_i=i,last_i=i,peak_i=i))
 return ev

def baseline(L,m,percentile=50):
 B=np.full(len(L),np.nan)
 for i in range(100,len(L)):
  past=L[i-100:i][m[i-100:i]]
  if len(past)>=20:B[i]=np.percentile(past,percentile)
 return B

def clock(t):
 return f'{int(t//3600):02d}:{int(t%3600//60):02d}:{t%60:04.1f}'

def dumpcsv(path,rows):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

manifest={r['id']:r for r in json.loads((OUT/'manifest.json').read_text())}
sens=[];states={};verified=[]
for sid,row in manifest.items():
 frame=np.load(OUT/f'acoustics/{sid}_frames.npz');L=frame['level_1s_db'];m=frame['level_speech_mask'];B=baseline(L,m);delta=L-B
 ev=detect(delta);saved=json.loads((OUT/f'acoustics/{sid}.json').read_text())
 assert len(ev)==saved['spikes_count']
 for e,old in zip(ev,saved['events']):
  for key in ['start','last','peak']:assert abs(e[key+'_i']/10-old[key+'_s'])<1e-7
  assert abs(delta[e['peak_i']]-old['max_delta_db'])<1e-7
 sens.append(dict(id=sid,show=SHOWS[sid],**{f'threshold_{t}dB_count':len(detect(delta,t)) for t in [6,8,10]},
  persist_1s_count=len(detect(delta,6,10)),persist_1_5s_count=len(detect(delta,6,15)),
  past_P75_count=len(detect(L-baseline(L,m,75))),current_speech_gate_count=len(detect(np.where(m,delta,np.nan)))))
 states[sid]=(L,m,B,delta,ev,frame)
 verified.append(dict(id=sid,event_count=len(ev),cached_event_reproduction='passed'))
dumpcsv(D/'threshold_sensitivity.csv',sens)
sid='s04';row=manifest[sid];L,m,B,delta,events,frame=states[sid];y,sr=sf.read(ROOT/row['sample_file']);t=np.arange(len(L))*.1
rawpowers=np.mean(y[:len(y)//1600*1600].reshape(-1,1600)**2,axis=1)
recalc=10*np.log10(np.maximum(np.convolve(rawpowers,np.ones(10)/10,'valid'),1e-12))
assert np.allclose(recalc,L,atol=1e-8)
start=row['sample_start_s'];segments=json.loads((OUT/'transcripts_mlx/s04.json').read_text())['segments']
rows=[]
for j,e in enumerate(events):
 i=e['peak_i'];a=e['start_i']/10;b=e['last_i']/10+1
 speech_text=' / '.join(s['text'] for s in segments if s['end']>a-1 and s['start']<b+1)
 rows.append(dict(event=j+1,sample_start_s=round(a,1),sample_support_end_s=round(b,1),sample_peak_window_start_s=round(i/10,1),
  original_peak_window_start=clock(start+i/10),max_delta_db=round(float(delta[i]),4),level_dbfs=round(float(L[i]),4),baseline_dbfs=round(float(B[i]),4),
  speech_level_percentile=round(float(np.mean(L[m]<=L[i])*100),2),peak_window_speech=bool(m[i]),transcript_auto=speech_text))
dumpcsv(D/'all_52_events.csv',rows)
# Distinct predeclared diagnostic cases, not a subjective listening selection.
peaks=np.array([e['peak_i'] for e in events]);diff=delta[peaks]
choices=[('最大相对增幅',int(np.argmax(diff))),('最高绝对电平',int(np.argmax(L[peaks]))),
 ('典型增幅（最接近中位数）',int(np.argmin(abs(diff-np.median(diff))))),('最低绝对电平',int(np.argmin(L[peaks]))),
 ('刚过阈值',int(np.argmin(diff))),('最长合并事件',int(np.argmax([e['last_i']-e['start_i'] for e in events])))]
chosen=[]
for reason,j in choices:
 if j not in [q[1] for q in chosen]:chosen.append((reason,j))
# Overview: levels, all peaks and distribution, exact same units.
fig,axs=plt.subplots(3,1,figsize=(16,11),gridspec_kw={'height_ratios':[2,1,1]})
axs[0].plot(t/60,L,color='#384bf5',lw=.65,label='1 秒 RMS');axs[0].plot(t/60,B+6,color='#d78a35',lw=.7,label='此前 10 秒语音中位电平 + 6 dB')
axs[0].scatter(peaks/600,L[peaks],s=18,color='#cc4e5c',label='52 个事件的最大差值窗口')
axs[0].set(xlabel='采样片段内时间（分钟）',ylabel='dBFS（数字电平）',ylim=(-50,-10));axs[0].legend(loc='lower right')
axs[1].plot(t/60,delta,color='#384bf5',lw=.65);axs[1].axhline(6,color='#cc4e5c',ls='--');axs[1].set(xlabel='采样片段内时间（分钟）',ylabel='相对前 10 秒增幅（dB）',ylim=(-16,15))
axs[2].hist(L[m],bins=55,density=True,alpha=.45,label='所有语音窗口');axs[2].hist(L[peaks],bins=18,density=True,alpha=.55,label='52 个事件峰值窗口');axs[2].axvline(np.percentile(L[m],90),ls='--',color='#666',label='语音电平 P90');axs[2].set(xlabel='1 秒 RMS（dBFS）',ylabel='概率密度');axs[2].legend()
fig.suptitle('张小珺Jùn｜商业访谈录 · 突发变响复核\n原音频 '+clock(start)+'—'+clock(start+1200)+'：52 次 / 20 分钟',fontsize=19,color='#384bf5')
fig.tight_layout(rect=(0,0,1,.93));fig.savefig(D/'00-overview.png',dpi=160);plt.close(fig)
clips=[]
for reason,j in chosen:
 e=events[j];peak=e['peak_i']/10;a=max(0,e['start_i']/10-12);b=min(1200,e['last_i']/10+1+8)
 stem=f'event-{j+1:02d}';audio=D/(stem+'.wav')
 # Export original 48 kHz stereo: no normalization/compression/gain change.
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-nostdin','-y','-i',str(ROOT/'samples'/row['source_file']),'-ss',str(start+a),'-t',str(b-a),'-vn','-c:a','pcm_s16le',str(audio)],check=True)
 f,st,p=signal.spectrogram(y[round(a*sr):round(b*sr)],sr,window='hann',nperseg=512,noverlap=384,scaling='density',mode='psd')
 psd=10*np.log10(np.maximum(p,1e-14));sel=(t>=a)&(t<=b);ix=e['peak_i']
 fig,axs=plt.subplots(4,1,figsize=(14,13),gridspec_kw={'height_ratios':[1,1.5,2,1.5]})
 stride=8;ty=np.arange(round(a*sr),round(b*sr),stride)/sr
 axs[0].plot(ty,y[round(a*sr):round(b*sr):stride],lw=.5,color='#384bf5');axs[0].set(ylabel='波形振幅',ylim=(-1,1))
 axs[1].plot(t[sel]+.5,L[sel],label='当前 1 秒 RMS（按窗口中心绘制）',color='#384bf5')
 axs[1].plot(t[sel]+.5,B[sel],label='此前 10 秒语音中位电平',color='#888')
 axs[1].plot(t[sel]+.5,B[sel]+6,label='触发线 = 参照 + 6 dB',color='#d78a35',ls='--');axs[1].set(ylabel='dBFS',ylim=(-50,-10));axs[1].legend(fontsize=9,loc='lower left')
 mesh=axs[2].pcolormesh(st+a,f/1000,psd,shading='auto',cmap='magma',vmin=-100,vmax=-35,rasterized=True);axs[2].set(ylabel='频率（kHz）',ylim=(0,8),xlabel='采样片段内时间（秒）')
 cax=axs[2].inset_axes([1.012,0,.015,1]);fig.colorbar(mesh,cax=cax,label='PSD · dB re 1 FS^2/Hz')
 for ax in axs[:3]:
  ax.axvspan(e['start_i']/10,e['last_i']/10+1,color='#df5068',alpha=.1)
  ax.axvspan(peak,peak+1,color='#df5068',alpha=.23)
  ax.set_xlim(a,b);ax.grid(alpha=.15)
 # Baseline spectral curve uses exactly the eligible 1 s windows used for scalar median, averaged in power.
 def ps(x):return signal.welch(x,sr,nperseg=512,noverlap=256,scaling='density')
 ff,pp=ps(y[round(peak*sr):round((peak+1)*sr)])
 prior=[ps(y[k*1600:k*1600+sr])[1] for k in range(ix-100,ix) if m[k]]
 baseps=np.mean(prior,axis=0)
 axs[3].plot(ff,10*np.log10(np.maximum(pp,1e-14)),label='峰值 1 秒',color='#384bf5')
 axs[3].plot(ff,10*np.log10(np.maximum(baseps,1e-14)),label='参照语音窗口平均功率谱（非中位谱）',color='#888')
 axs[3].set(xlim=(0,8000),ylim=(-115,-25),xlabel='频率（Hz）',ylabel='PSD（dB re 1 FS^2/Hz）');axs[3].grid(alpha=.15);axs[3].legend(fontsize=9)
 fig.suptitle(f'事件 {j+1:02d} · {reason} · 原音频 {clock(start+peak)}\n增幅 +{delta[ix]:.2f} dB = 当前 {L[ix]:.2f} - 参照 {B[ix]:.2f} dBFS',fontsize=17,color='#384bf5')
 fig.text(.06,.018,'浅红：合并事件的窗口覆盖范围（不代表全程超阈值）；深红：最大差值对应的 1 秒。频谱来自 16 kHz 单声道分析副本。',fontsize=10,color='#666')
 fig.subplots_adjust(top=.90,bottom=.075,left=.08,right=.91,hspace=.48);fig.savefig(D/(stem+'.png'),dpi=150);plt.close(fig)
 clips.append(dict(reason=reason,**rows[j],clip_start_original=clock(start+a),clip_end_original=clock(start+b),event_at_clip_s=round(peak-a,1),audio=audio.name,figure=stem+'.png'))
(D/'review_data.json').write_text(json.dumps(dict(source=row,verified=verified,raw_rms_recomputed=True,events=rows,selected=clips,sensitivity=sens),ensure_ascii=False,indent=2))
print(json.dumps(dict(selected=clips,sensitivity=sens,median_delta=float(np.median(diff)),peak_below_P90=int(sum(L[peaks]<np.percentile(L[m],90))),current_inactive=int(sum(~m[peaks]))),ensure_ascii=False,indent=2))
