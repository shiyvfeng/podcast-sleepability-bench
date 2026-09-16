"""Merge acoustic measurements and ASR; rank and audit without invented fields."""
from pathlib import Path
import csv
import itertools
import json
import numpy as np
from scipy.stats import rankdata
from transcribe import count_units

from paths import ROOT, OUT
FIELDS=['pitch_iqr_st','units_per_min','loudness_range_db','spikes_per_10min']
WEIGHTS=np.array([.30,.30,.25,.15])

def scores(matrix,weights=WEIGHTS):
    matrix=np.asarray(matrix,dtype=float)
    assert np.isfinite(matrix).all(), 'Missing or nonfinite measurement; do not silently rank it.'
    n=len(matrix)
    assert n>=2
    parts=np.array([100*(n-rankdata(matrix[:,j],method='average'))/(n-1) for j in range(matrix.shape[1])]).T
    return parts@weights,parts

def block_count(segments,start,end):
    total=0
    for s in segments:
        # Words with timestamps allocate each segment's exact unit total to blocks.
        words=s['words']
        denom=sum(count_units(w['word']) for w in words)
        if denom:
            total+=s['units']*sum(count_units(w['word']) for w in words if start <= (w['start']+w['end'])/2 < end)/denom
        elif start <= (s['start']+s['end'])/2 < end:
            total+=s['units']
    return total

def main():
    manifest=json.loads((OUT/'manifest.json').read_text())
    catalog=json.loads((ROOT/'sample_catalog.json').read_text())
    rows=[];block_rows=[]
    for src in manifest:
        sid=src['id']
        a=json.loads((OUT/'acoustics'/f'{sid}.json').read_text())
        t=json.loads((OUT/'transcripts_mlx'/f'{sid}.json').read_text())
        assert a['method_version']=='0.2'
        assert abs(t['duration_s']-src['sample_duration_s'])<.1
        assert a['pitch_valid_windows']>=200
        seg=t['segments']; units=sum(count_units(s['text']) for s in seg)
        assert units==t['units'] and units>0
        flagged=[dict(start_s=s['start'],end_s=s['end'],avg_logprob=s['avg_logprob'],compression_ratio=s['compression_ratio'],text=s['text'])
                 for s in seg if s['avg_logprob'] < -.8 or s['compression_ratio']>2.4]
        r={**src,**catalog[sid],**{k:v for k,v in a.items() if k not in {'name','blocks','events','vad_segments'}},
           'units':units,'units_per_min':units/(src['sample_duration_s']/60),
           'asr_flagged_segments':flagged,'asr_segment_count':len(seg),
           'asr_repeat_adjacent':sum(seg[i]['text'].strip()==seg[i-1]['text'].strip() for i in range(1,len(seg))),
           'asr_model':t['model'],'asr_elapsed_s':t['elapsed_s']}
        local=[]
        for b in a['blocks']:
            b={**b,'id':sid,'name':r['name'],'units':block_count(seg,b['start_s'],b['end_s'])}
            b['units_per_min']=b['units']/(b['duration_s']/60)
            local.append(b);block_rows.append(b)
        assert abs(sum(b['units'] for b in local)-units)<1e-6
        r['block_rate_min']=min(b['units_per_min'] for b in local)
        r['block_rate_max']=max(b['units_per_min'] for b in local)
        rows.append(r)
    matrix=np.array([[r[f] for f in FIELDS] for r in rows])
    total,parts=scores(matrix)
    for i,r in enumerate(rows):
        r['score']=float(total[i]);r['component_scores']={f:float(parts[i,j]) for j,f in enumerate(FIELDS)}
        r['rank']=int(rankdata(-total,method='min')[i])
    # Check all 16 corners at +/-20% each weight, then renormalize; plus equal weights.
    scenarios=[]
    for factors in itertools.product([.8,1.2],repeat=4):
        w=WEIGHTS*np.array(factors);w=w/w.sum()
        ts,_=scores(matrix,w)
        scenarios.append(dict(weights=w.tolist(),scores=ts.tolist(),ranks=rankdata(-ts,method='min').astype(int).tolist()))
    ts,_=scores(matrix,np.ones(4)/4)
    scenarios.append(dict(weights=[.25]*4,scores=ts.tolist(),ranks=rankdata(-ts,method='min').astype(int).tolist()))
    for i,r in enumerate(rows):
        r['weight_rank_min']=min(s['ranks'][i] for s in scenarios)
        r['weight_rank_max']=max(s['ranks'][i] for s in scenarios)
    # Same relative 4-minute positions, five different windows; not confidence intervals.
    temporal=[]
    for j in range(5):
        chunk=[next(b for b in block_rows if b['id']==r['id'] and b['start_s']==j*240) for r in rows]
        ts,_=scores([[b[f] for f in FIELDS] for b in chunk])
        ranks=rankdata(-ts,method='min').astype(int).tolist()
        temporal.append(dict(block=j+1,start_s=j*240,ranks=ranks,scores=ts.tolist()))
        for i,b in enumerate(chunk):b['score']=float(ts[i]);b['rank']=ranks[i]
    for i,r in enumerate(rows):
        r['window_rank_min']=min(s['ranks'][i] for s in temporal)
        r['window_rank_max']=max(s['ranks'][i] for s in temporal)
    result=dict(method_version='0.2',scope=f'{len(rows)} supplied episode excerpts; 20 minutes each',weights=dict(zip(FIELDS,WEIGHTS.tolist())),
                rows=sorted(rows,key=lambda x:(-x['score'],x['id'])),weight_sensitivity=scenarios,window_sensitivity=temporal,
                sensitivity_id_order=[r['id'] for r in rows])
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    keys=['rank','name','episode','score','units_per_min','pitch_iqr_st','loudness_range_db','spikes_per_10min','spikes_count',
          'speech_fraction','pause_median_s','longest_pause_s','sample_start_s','sample_duration_s','full_duration_s',
          'weight_rank_min','weight_rank_max','window_rank_min','window_rank_max','source_file','source_sha256']
    with (OUT/'榜单与指标.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');writer.writeheader();writer.writerows(result['rows'])
    with (OUT/'四分钟分段指标.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(block_rows[0]));writer.writeheader();writer.writerows(block_rows)
    print(json.dumps([{k:r[k] for k in ['name','rank','score','units_per_min','pitch_iqr_st','loudness_range_db','spikes_per_10min','weight_rank_min','weight_rank_max','window_rank_min','window_rank_max']} for r in result['rows']],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
