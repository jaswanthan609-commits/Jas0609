"""Synthesise demo voice lines with Microsoft Edge neural voices (free, needs internet).
Writes demo/voice/out/<id>.mp3 plus <id>.json word timings, and samples of every en-IN voice."""
import asyncio, json, os, edge_tts
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
J = json.load(open(os.path.join(HERE, 'jobs.json')))

async def say(id_, voice, text, rate='+0%', pitch='+0Hz'):
    path = os.path.join(OUT, id_); os.makedirs(os.path.dirname(path), exist_ok=True)
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary='WordBoundary')
    words = []
    with open(path + '.mp3', 'wb') as f:
        async for ch in c.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] == 'WordBoundary': words.append(dict(t=ch['offset'] / 1e7, d=ch['duration'] / 1e7, w=ch['text']))
    json.dump(words, open(path + '.json', 'w'))

async def main():
    vs = await edge_tts.list_voices()
    inds = [v['ShortName'] for v in vs if v['Locale'] == 'en-IN']
    json.dump(inds, open(os.path.join(OUT, 'en-IN-voices.json'), 'w'))
    only = J.get('only_prefix')
    if not only:
        for v in inds: await say(f'samples/{v}', v, J['sample_in'])
    for j in J['jobs']:
        if only and not j['id'].startswith(tuple(only)): continue
        for k in range(3):
            try: await say(j['id'], j['voice'], j['text'], j.get('rate', '+0%'), j.get('pitch', '+0Hz')); break
            except Exception as e: print('retry', j['id'], e); await asyncio.sleep(3)
os.makedirs(OUT, exist_ok=True); asyncio.run(main())
