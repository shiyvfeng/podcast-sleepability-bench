"""Decode supplied files fully to obtain reliable AAC duration, then sample centres."""
from pathlib import Path
import hashlib
import json
import subprocess
import av
import imageio_ffmpeg
import soundfile as sf

from paths import ROOT, OUT
CACHE = ROOT / 'cache'
CACHE.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

def main():
    rows = []
    prior_path=OUT/'manifest.json'
    prior={r['id']:r for r in json.loads(prior_path.read_text())} if prior_path.exists() else {}
    prior_hash={r['source_sha256']:r for r in prior.values()}
    next_id=max((int(s[1:]) for s in prior),default=0)+1
    for p in sorted((ROOT / 'samples').iterdir()):
        if p.suffix.lower() not in {'.aac', '.m4a', '.mp3', '.wav', '.flac'}:
            continue
        with p.open('rb') as source:
            source_hash=hashlib.file_digest(source,'sha256').hexdigest()
        previous=prior_hash.get(source_hash)
        if previous:
            sid=previous['id']
            if (ROOT/previous['sample_file']).exists() and (CACHE/f'{sid}_full.wav').exists():
                rows.append({**previous,'source_file':p.name})
                print('Reused unchanged audio:',sid,p.name,flush=True)
                continue
        else:
            sid=f's{next_id:02d}'
            next_id+=1
        with av.open(str(p)) as container:
            metadata = dict(container.metadata)
            stream = container.streams.audio[0]
            codec, channels, sample_rate = stream.codec_context.name, stream.codec_context.channels, stream.codec_context.sample_rate
        full = CACHE / f'{sid}_full.wav'
        if not full.exists() or prior.get(sid,{}).get('source_sha256')!=source_hash:
            subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i', str(p), '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(full)], check=True)
        info = sf.info(full)
        duration = info.frames / info.samplerate
        length = min(1200.0, duration)
        start = max(0.0, (duration-length)/2)
        with sf.SoundFile(full) as f:
            f.seek(round(start * info.samplerate))
            sample = f.read(round(length * info.samplerate), dtype='float32')
        target = CACHE / f'{sid}_sample.wav'
        sf.write(target, sample, info.samplerate, subtype='PCM_16')
        # Keep a small introduction excerpt for identifying incomplete filenames.
        with sf.SoundFile(full) as f:
            intro = f.read(90 * info.samplerate, dtype='float32')
        sf.write(CACHE / f'{sid}_intro.wav', intro, info.samplerate)
        name = ('十字路口' if '十字路口' in p.name else '三五环' if '三五环' in p.name else
                '硅谷101' if '硅谷101' in p.name else '曾鸣访谈' if '曾鸣' in p.name else
                '鹿鹿鱼鱼' if '鹿鹿鱼鱼' in p.name else '葬AI' if '葬AI' in p.name else p.stem)
        row = dict(id=sid, name=name, source_file=p.name, source_sha256=source_hash,
                   metadata=metadata, codec=codec, source_channels=channels, source_sample_rate=sample_rate,
                   full_duration_s=duration, sample_start_s=start, sample_duration_s=len(sample)/info.samplerate,
                   sample_file=str(target.relative_to(ROOT)))
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    (OUT / 'manifest.json').write_text(json.dumps(sorted(rows,key=lambda r:r['id']), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
