"""Verify the public example schema and rankings without audio or ASR dependencies."""
import csv
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'examples'/'six-episodes'
ALLOWED={'id','rank','score','units_per_min','pitch_iqr_st','loudness_range_db','spikes_per_10min',
         'spikes_count','units','sample_start_s','sample_duration_s','full_duration_s','component_scores',
         'weight_rank_min','weight_rank_max','window_rank_min','window_rank_max','name','episode'}

def main():
    data=json.loads((D/'results.json').read_text());rows=data['rows'];n=len(rows)
    assert n==6 and len({r['id'] for r in rows})==n
    assert set(data)=={'method_version','scope','weights','rows','note'}
    assert math.isclose(sum(data['weights'].values()),1)
    for r in rows:
        assert set(r)==ALLOWED
        assert set(r['component_scores'])==set(data['weights'])
        assert r['sample_duration_s']==1200
        assert math.isclose(r['spikes_count']/2,r['spikes_per_10min'])
        assert math.isclose(r['units']/20,r['units_per_min'])
        score=0
        for f,w in data['weights'].items():
            values=[q[f] for q in rows if q['id']!=r['id']]
            part=100*(sum(v>r[f] for v in values)+.5*sum(v==r[f] for v in values))/(n-1)
            assert math.isclose(part,r['component_scores'][f],abs_tol=1e-9)
            score+=part*w
        assert math.isclose(score,r['score'],abs_tol=1e-9)
        assert r['rank']==1+sum(q['score']>r['score'] for q in rows)
    with (D/'metrics.csv').open(encoding='utf-8-sig',newline='') as f:
        csvrows=list(csv.DictReader(f))
    assert len(csvrows)==n
    for a,b in zip(csvrows,rows):
        assert set(a)<=ALLOWED
        for k,v in a.items():
            assert math.isclose(float(v),b[k],abs_tol=1e-9) if isinstance(b[k],(int,float)) else v==b[k]
    print('PASS: six aggregate rows, allowlisted fields, CSV consistency, four components and final ranks.')

if __name__=='__main__':main()
