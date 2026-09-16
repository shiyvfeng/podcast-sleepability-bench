"""Independent consistency checks on real inputs, measurements and ranking."""
from pathlib import Path
import hashlib
import json
import numpy as np
import soundfile as sf
from transcribe import count_units

from paths import ROOT, OUT

def main():
    data=json.loads((OUT/'results.json').read_text());rows=data['rows'];checks=[]
    manifest=json.loads((OUT/'manifest.json').read_text())
    n=len(manifest)
    assert n>=2 and len(rows)==n and len({r['source_sha256'] for r in rows})==n
    assert {r['id'] for r in rows}=={r['id'] for r in manifest}
    assert sum(r['sample_duration_s'] for r in rows)==1200*n
    fields=list(data['weights']);weights=np.array(list(data['weights'].values()))
    assert np.isclose(weights.sum(),1)
    for r in rows:
        sid=r['id'];file=ROOT/'samples'/r['source_file']
        assert hashlib.file_digest(file.open('rb'),'sha256').hexdigest()==r['source_sha256']
        info=sf.info(ROOT/r['sample_file']);assert info.samplerate==16000 and info.channels==1 and info.frames==19200000
        assert r['sample_start_s']>=0 and r['sample_start_s']+r['sample_duration_s']<=r['full_duration_s']+.001
        frames=np.load(OUT/'acoustics'/f'{sid}_frames.npz')
        # Praat refines candidate peaks by interpolation; permit 0.25 Hz at search boundaries.
        pitch=frames['pitch_hz'];assert np.all((pitch==0)|((pitch>=64.75)&(pitch<=500.25)))
        level=frames['level_1s_db'];active=frames['level_speech_mask']
        v=level[active];span=np.diff(np.percentile(v,[10,90]))[0]
        # An arbitrary fixed +7.3 dB gain must not change the stability metric.
        assert np.isclose(span,np.diff(np.percentile(v+7.3,[10,90]))[0])
        assert np.isclose(span,r['loudness_range_db'])
        a=json.loads((OUT/'acoustics'/f'{sid}.json').read_text())
        assert len(a['events'])==r['spikes_count']
        assert np.isclose(len(a['events'])/2,r['spikes_per_10min'])
        for e in a['events']:
            i=round(e['peak_s']*10);past=level[i-100:i][active[i-100:i]]
            assert len(past)>=20 and level[i]-np.median(past)>=6-1e-6
            assert 10<=e['start_s']<=e['peak_s']<=e['last_s']<1200
        t=json.loads((OUT/'transcripts_mlx'/f'{sid}.json').read_text())
        assert all(0<=s['start']<=s['end']<=1200.01 for s in t['segments'])
        assert sum(count_units(s['text']) for s in t['segments'])==r['units']
        assert np.isclose(r['units']/20,r['units_per_min'])
        # Pairwise rank definition, independently of scipy rankdata.
        components=[]
        for f in fields:
            others=[q[f] for q in rows if q['id']!=sid]
            value=100*(sum(v>r[f] for v in others)+.5*sum(v==r[f] for v in others))/(n-1)
            assert np.isclose(value,r['component_scores'][f]);components.append(value)
        assert np.isclose(np.dot(components,weights),r['score'])
        checks.append(dict(id=sid,name=r['name'],input_hash='pass',duration='pass',pitch_bounds='pass',
                  loudness_gain_invariance='pass',event_recalculation='pass',asr_count='pass',ranking='pass'))
    assert all(rows[i]['score']>=rows[i+1]['score'] for i in range(n-1))
    cpu=OUT/'transcripts'/'s01.json'
    cross=None
    if cpu.exists():
        baseline=json.loads(cpu.read_text())['units'];gpu=next(r['units'] for r in rows if r['id']=='s01')
        cross=dict(sample='s01',cpu_small_int8_units=baseline,gpu_small_float16_units=gpu,
                   relative_difference_percent=(gpu-baseline)/baseline*100,
                   meaning='Different runtimes/decoding; comparison only, not manual accuracy validation.')
    result=dict(status='passed',checks=checks,asr_crosscheck=cross,
                total_sample_minutes=20*n,pitch_search_boundary_tolerance_hz=.25,weight_scenarios=len(data['weight_sensitivity']))
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
