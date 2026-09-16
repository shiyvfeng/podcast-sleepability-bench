"""Acoustic features v0.2; see method-v0.1.md for the calibration changelog."""
from pathlib import Path
import csv
import json
import argparse
import numpy as np
import soundfile as sf
import parselmouth
from faster_whisper.vad import VadOptions, get_speech_timestamps

from paths import ROOT, OUT
RAW = OUT / 'acoustics'
RAW.mkdir(exist_ok=True)

def runs(mask):
    edges = np.diff(np.r_[False, mask, False].astype(int))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))

def extract(y, sr):
    hop = round(sr * .1)
    n = len(y) // hop
    powers = np.mean(y[:n*hop].reshape(n, hop).astype('float64')**2, axis=1)
    db = 10*np.log10(np.maximum(powers, 1e-12))
    speech = get_speech_timestamps(y, VadOptions(threshold=.5, min_speech_duration_ms=150,
                  min_silence_duration_ms=300, speech_pad_ms=0), sampling_rate=sr)
    centers = (np.arange(n)+.5)*hop
    mask = np.zeros(n, dtype=bool)
    for s in speech:
        mask |= (centers >= s['start']) & (centers < s['end'])
    snd = parselmouth.Sound(y.astype('float64'), sampling_frequency=sr)
    pitch = snd.to_pitch_ac(time_step=.01, pitch_floor=65, pitch_ceiling=500)
    f0 = pitch.selected_array['frequency']
    times = pitch.xs()
    # Gate unvoiced and non-speech frames. No global speaker-pitch penalty.
    active = mask[np.minimum((times/.1).astype(int), n-1)]
    f0[~active] = 0
    # Compare like-for-like 1 s power windows, not 400 ms means to 100 ms medians.
    level = 10*np.log10(np.maximum(np.convolve(powers, np.ones(10)/10, mode='valid'),1e-12))
    level_active = np.convolve(mask.astype(float),np.ones(10)/10,mode='valid')>=.5
    candidates = []
    delta = np.zeros(len(level))
    for i in range(100, len(level)):
        past = level[i-100:i][level_active[i-100:i]]
        if len(past) >= 20:
            delta[i] = level[i] - np.median(past)
    # A rise must persist across at least 0.5 s of overlapping windows.
    for a,b in runs(delta>=6):
        if b-a >= 5:
            candidates.extend((i*.1,float(delta[i])) for i in range(a,b))
    events=[]
    for t, delta in candidates:
        if events and t-events[-1]['last_s'] <= 2.00001:
            e=events[-1]
            e['last_s']=t
            if delta > e['max_delta_db']:
                e['peak_s'],e['max_delta_db']=t,delta
        else:
            events.append(dict(start_s=t,last_s=t,peak_s=t,max_delta_db=delta))
    return db,mask,times,f0,events,speech,level,level_active

def summarize(db, mask, times, f0, events, start, end, level, level_active):
    a,b=round(start*10),round(end*10)
    local_db=level[a:b][level_active[a:b]]
    local_pitch=[]
    for t in np.arange(start,end,5):
        v=f0[(times >= t)&(times < min(t+5,end))]
        v=v[v>0]
        if len(v)>=50:
            semi=12*np.log2(v)
            local_pitch.append(float(np.percentile(semi,75)-np.percentile(semi,25)))
    pauses=[(j-i)*.1 for i,j in runs(~mask[a:b]) if j-i >= 3]
    selected=[e for e in events if start<=e['peak_s']<end]
    voiced=f0[(times >= start)&(times < end)]
    voiced=voiced[voiced>0]
    return dict(start_s=start,end_s=end,duration_s=end-start,
        pitch_iqr_st=float(np.median(local_pitch)) if local_pitch else None,
        pitch_valid_windows=len(local_pitch),pitch_voiced_fraction=len(voiced)/max(1,np.sum((times>=start)&(times<end))),
        loudness_range_db=float(np.percentile(local_db,90)-np.percentile(local_db,10)) if len(local_db) else None,
        spikes_count=len(selected),spikes_per_10min=len(selected)*600/(end-start),
        speech_fraction=float(np.mean(mask[a:b])),pause_count=len(pauses),
        pause_median_s=float(np.median(pauses)) if pauses else 0,
        longest_pause_s=max(pauses,default=0),pitch_median_hz=float(np.median(voiced)) if len(voiced) else None)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ids',nargs='*',help='Only calculate these IDs; reuse existing acoustic JSON for others.')
    args=parser.parse_args()
    rows=json.loads((OUT/'manifest.json').read_text())
    summaries=[]
    for row in rows:
        if args.ids and row['id'] not in args.ids:
            saved=json.loads((RAW/f"{row['id']}.json").read_text())
            summaries.append({k:v for k,v in saved.items() if k not in {'blocks','events','vad_segments'}})
            print('Reused acoustics:',row['id'],flush=True)
            continue
        print('Acoustics starting:',row['name'],flush=True)
        y,sr=sf.read(ROOT/row['sample_file'],dtype='float32')
        db,mask,times,f0,events,speech,level,level_active=extract(y,sr)
        duration=len(y)/sr
        mainrow=summarize(db,mask,times,f0,events,0,duration,level,level_active)
        blocks=[summarize(db,mask,times,f0,events,t,min(t+240,duration),level,level_active) for t in np.arange(0,duration,240)]
        result=dict(id=row['id'],name=row['name'],method_version='0.2',**mainrow,blocks=blocks,events=events,
                    vad_segments=[dict(start_s=s['start']/sr,end_s=s['end']/sr) for s in speech])
        (RAW/f"{row['id']}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
        np.savez_compressed(RAW/f"{row['id']}_frames.npz",rms_db=db,speech_mask=mask,pitch_time_s=times,pitch_hz=f0,level_1s_db=level,level_speech_mask=level_active)
        summaries.append({k:v for k,v in result.items() if k not in {'blocks','events','vad_segments'}})
        print(json.dumps(summaries[-1],ensure_ascii=False),flush=True)
    with (OUT/'acoustic_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)

if __name__=='__main__':
    main()
