"""Compare an additional-sample batch with the preserved five-sample baseline."""
import hashlib
import json
from paths import ROOT, OUT

def clock(s):
    s=round(s)
    return f'{s//3600:02}:{s//60%60:02}:{s%60:02}'

def main():
    current=json.loads((OUT/'results.json').read_text())
    baseline=json.loads((ROOT/'output/results.json').read_text())
    old={r['id']:r for r in baseline['rows']}
    rows=current['rows'];new=[r for r in rows if r['id'] not in old]
    assert new, 'No added samples in this batch.'
    fields=['source_sha256','sample_start_s','sample_duration_s','pitch_iqr_st','loudness_range_db','spikes_count','units','units_per_min']
    for r in rows:
        if r['id'] in old:
            for key in fields:
                assert r[key]==old[r['id']][key],f'Baseline measurement changed: {r["id"]} {key}'
    hashes=json.loads((OUT/'baseline_hashes.json').read_text())
    for path,digest in hashes.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,f'Baseline artifact changed: {path}'
    checked=dict(status='passed',unchanged_original_samples=len(old),unchanged_baseline_files=len(hashes),
                 added_ids=[r['id'] for r in new],current_batch_images=len(list(OUT.glob('*.png'))))
    (OUT/'incremental_verification.json').write_text(json.dumps(checked,ensure_ascii=False,indent=2))
    from batch_report import write_report
    write_report()
    print(json.dumps(checked,ensure_ascii=False))

if __name__=='__main__':main()
