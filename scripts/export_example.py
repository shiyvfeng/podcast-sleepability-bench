"""Export an allowlisted, transcript-free six-episode example for publication."""
import csv
import json
import shutil
from paths import ROOT, OUT

FIELDS = ['id','rank','score','units_per_min','pitch_iqr_st','loudness_range_db',
          'spikes_per_10min','spikes_count','units','sample_start_s','sample_duration_s',
          'full_duration_s','component_scores','weight_rank_min','weight_rank_max',
          'window_rank_min','window_rank_max']
CHARTS = ['01-播客催眠评测.png','02-语速与语调.png','03-四项指标.png']

def main():
    data=json.loads((OUT/'results.json').read_text())
    catalog=json.loads((ROOT/'sample_catalog.json').read_text())
    target=ROOT/'examples'/'six-episodes';target.mkdir(parents=True,exist_ok=True)
    assert len(data['rows'])==6, 'This exporter is for the six-episode example.'
    rows=[]
    for original in data['rows']:
        row={k:original[k] for k in FIELDS}
        row.update(name=catalog[row['id']]['name'],episode=catalog[row['id']]['episode'])
        rows.append(row)
    # Never copy raw results.json: it can contain asr_flagged_segments with text.
    public=dict(method_version=data['method_version'],scope=data['scope'],weights=data['weights'],rows=rows,
                note='Aggregate example only; no audio, transcript text, source metadata or local paths. The spike metric is a local level-rise heuristic, not perceived startle.')
    (target/'results.json').write_text(json.dumps(public,ensure_ascii=False,indent=2))
    fields=['rank','id','name','episode','score','units_per_min','pitch_iqr_st','loudness_range_db','spikes_per_10min']
    with (target/'metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    for name in CHARTS:shutil.copyfile(OUT/name,target/name)
    print(f'Exported {len(rows)} aggregate rows and {len(CHARTS)} charts to {target}')

if __name__=='__main__':main()
