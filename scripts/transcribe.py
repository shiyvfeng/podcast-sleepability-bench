"""Local Whisper small transcription; audio never leaves the machine."""
from pathlib import Path
import argparse
import json
import os
import re
import time
from faster_whisper import WhisperModel

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'/'transcripts'
OUT.mkdir(exist_ok=True)

def count_units(text):
    return len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff]|[A-Za-z]+(?:[\x27-][A-Za-z]+)*|\d+(?:\.\d+)?',text))

def main():
    p=argparse.ArgumentParser();p.add_argument('--intro',action='store_true');p.add_argument('--ids',nargs='*');args=p.parse_args()
    model=WhisperModel(str(ROOT/'models'/'faster-whisper-small'),device='cpu',compute_type='int8',cpu_threads=8,num_workers=1)
    rows=json.loads((ROOT/'output'/'manifest.json').read_text())
    for row in rows:
        if args.ids and row['id'] not in args.ids:continue
        suffix='_intro' if args.intro else ''
        target=OUT/f"{row['id']}{suffix}.json"
        if target.exists():
            print('Cached',target.name,flush=True);continue
        source=ROOT/'cache'/f"{row['id']}_intro.wav" if args.intro else ROOT/row['sample_file']
        print('Transcription starting:',row['name'],flush=True);begin=time.monotonic()
        segments,info=model.transcribe(str(source),language='zh',beam_size=3,temperature=0,
            condition_on_previous_text=False,vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),word_timestamps=True)
        collected=[]
        for s in segments:
            d=dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,
                   no_speech_prob=s.no_speech_prob,compression_ratio=s.compression_ratio,
                   words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in (s.words or [])])
            d['units']=count_units(s.text)
            collected.append(d)
            if len(collected)%30==0:
                print(row['id'],f'{s.end/60:.1f} min audio decoded; {time.monotonic()-begin:.0f}s elapsed',flush=True)
        result=dict(id=row['id'],model='Systran/faster-whisper-small',compute_type='int8',language=info.language,
                    duration_s=info.duration,duration_after_vad_s=info.duration_after_vad,
                    units=sum(s['units'] for s in collected),segments=collected,elapsed_s=time.monotonic()-begin)
        target.write_text(json.dumps(result,ensure_ascii=False,indent=2))
        (OUT/f"{row['id']}{suffix}.txt").write_text('\n'.join(f"[{s['start']:.1f}–{s['end']:.1f}] {s['text']}" for s in collected))
        print('Transcription complete',row['name'],result['units'],f"{result['elapsed_s']:.0f}s",flush=True)

if __name__=='__main__':main()
