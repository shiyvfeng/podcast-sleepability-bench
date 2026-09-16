"""Apple Silicon GPU path; all 5 samples use the same small model and settings."""
from pathlib import Path
import json
import time
import soundfile as sf
import mlx_whisper
from transcribe import count_units

from paths import ROOT, OUT as BATCH_OUT
OUT=BATCH_OUT/'transcripts_mlx'
OUT.mkdir(exist_ok=True)

def main():
    rows=json.loads((BATCH_OUT/'manifest.json').read_text())
    for row in rows:
        target=OUT/f"{row['id']}.json"
        cached=json.loads(target.read_text()) if target.exists() else {}
        cache_key=dict(source_sha256=row['source_sha256'],sample_start_s=row['sample_start_s'],sample_duration_s=row['sample_duration_s'],
                       model='mlx-community/whisper-small-mlx',settings='zh_fp16_t0_no_context_240s_v1')
        if cached.get('cache_key')==cache_key:
            print('Cached',target.name,flush=True);continue
        print('GPU transcription starting:',row['name'],flush=True)
        y,sr=sf.read(ROOT/row['sample_file'],dtype='float32')
        begin=time.monotonic();collected=[]
        for start in range(0,len(y),sr*240):
            chunk=y[start:start+sr*240];offset=start/sr
            r=mlx_whisper.transcribe(chunk,path_or_hf_repo=str(ROOT/'models'/'whisper-small-mlx'),language='zh',
                 temperature=0,condition_on_previous_text=False,word_timestamps=False,verbose=None)
            for s in r['segments']:
                collected.append(dict(start=offset+s['start'],end=min(len(y)/sr,offset+s['end']),text=s['text'],
                   avg_logprob=s['avg_logprob'],no_speech_prob=s['no_speech_prob'],compression_ratio=s['compression_ratio'],
                   words=[],units=count_units(s['text'])))
            print(row['id'],f'{(start+len(chunk))/sr/60:.0f}/20 min, elapsed {time.monotonic()-begin:.0f}s',flush=True)
        result=dict(id=row['id'],model='mlx-community/whisper-small-mlx',compute_type='float16',language='zh',
                   duration_s=len(y)/sr,units=sum(s['units'] for s in collected),segments=collected,
                   elapsed_s=time.monotonic()-begin,chunk_seconds=240,cache_key=cache_key)
        target.write_text(json.dumps(result,ensure_ascii=False,indent=2))
        (OUT/f"{row['id']}.txt").write_text('\n'.join(f"[{s['start']:.1f}–{s['end']:.1f}] {s['text']}" for s in collected))
        print('GPU complete',row['name'],result['units'],flush=True)

if __name__=='__main__':main()
