#!/usr/bin/env python3
"""Monta os vídeos do Episódio 1 (Parte 1 e Parte 2) em MP4 vertical 1080x1920.

Uso: python3 build.py            (gera build/parte1.mp4 e build/parte2.mp4)
Requer: node + playwright (render das cenas), ffmpeg, numpy.
"""
import json, os, re, subprocess, urllib.parse, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, 'build')
os.makedirs(B, exist_ok=True)
FPS = 30
SR = 44100
TITLE = 3.0        # segundos de título no começo
XF = 0.5           # duração da transição entre cenas
SEC_PER_WORD = 0.33

PARTS = {
  'parte1': {
    'sub': 'EP. 1 · PARTE 1 — O SONHO',
    'scenes': [
      ('p1s1', "Esse é o Benjamin. Treze anos. Um campo de terra, uma bola remendada e um sonho do tamanho do Maracanã. Todo fim de tarde, quando o sol começa a cair, ele é o último a sair do campinho."),
      ('p1s2', "A chuteira tem um furo no dedão. O gol é feito de dois chinelos. Mas, quando a bola cola no pé dele, ninguém no bairro consegue tirar. Os mais velhos já falam: esse moleque tem alguma coisa diferente."),
      ('p1s3', "Aquela cicatriz na sobrancelha? Foi aos oito anos. Uma dividida, um tombo feio, sangue na testa. Todo mundo achou que ele ia chorar e ir embora. Ele levantou, limpou o rosto… e fez o gol da vitória."),
      ('p1s4', "Em casa, a dona Lúcia, mãe dele, trabalha em dois empregos. Chega tarde, cansada, mas sempre pergunta: “E aí, meu craque, fez gol hoje?” É por ela que o Benjamin promete, todo dia, que um dia vai mudar a vida da família."),
      ('p1s5', "De noite, deitado na cama, ele olha os pôsteres colados na parede descascada e imagina: o estádio lotado, a torcida gritando o nome dele. “Benjamin! Benjamin!” Ele fecha os olhos e quase consegue ouvir."),
      ('p1s6', "Mas sonho não paga conta. E o Benjamin sabe que a chance de sair do campo de terra pode aparecer uma vez só. O que ele não sabe… é que ela vai bater na porta amanhã."),
    ],
    'end': 'next',
    'sfx': {'p1s5': 'crowd_soft'},
  },
  'parte2': {
    'sub': 'EP. 1 · PARTE 2 — A ESCOLHA',
    'scenes': [
      ('p2s1', "No dia seguinte, o campinho estava diferente. Tinha um homem de boné e prancheta na mão, parado do lado da trave. Ninguém sabia quem era. Mas ele não tirava os olhos do Benjamin."),
      ('p2s2', "Bola no pé. Um drible. Dois. Chapéu no zagueiro maior que ele. O goleiro sai desesperado… e o Benjamin toca por cima, com calma, como quem já fez isso mil vezes. Golaço. O campinho inteiro explode."),
      ('p2s3', "No fim do jogo, dois convites. O seu Zé, técnico do time da cidade, coloca a mão no ombro dele: “Vem jogar com a gente. Você vai ser titular, vai jogar todo fim de semana, perto da sua mãe.”"),
      ('p2s4', "Aí o homem da prancheta se aproxima e entrega um papel. “Sou olheiro de um clube grande. Tem peneira sábado, na capital. Quinhentos garotos, só três vagas. Se passar, você muda de vida. Se não passar… volta pra cá.”"),
      ('p2s5', "De um lado, a segurança. Jogar sempre, crescer aos poucos, ficar perto de casa. Do outro, o risco. Uma chance só, contra quinhentos. O coração do Benjamin dispara. Ele olha pra mãe na beira do campo…"),
      ('p2s6', "…e quem decide agora é você. A: time da cidade. B: peneira do clube grande. Comenta A ou B. A resposta mais comentada decide o próximo episódio!"),
    ],
    'end': 'buttons',
    'sfx': {'p2s2': 'crowd_goal'},
  },
}


def chunks(text, maxw=7):
    """Quebra a narração em legendas curtas: primeiro por frase, depois em pedaços equilibrados."""
    sents = re.findall(r'[^.!?…]+[.!?…]+[”"]?|[^.!?…]+$', text)
    out = []
    for s in sents:
        w = s.split()
        if not w:
            continue
        # tenta cortar em vírgula/dois-pontos se a frase for longa
        if len(w) > maxw:
            parts, cur = [], []
            for x in w:
                cur.append(x)
                if re.search(r'[,:;]$', x) and len(cur) >= 3:
                    parts.append(cur); cur = []
            if cur:
                if parts and len(cur) <= 2:
                    parts[-1] += cur
                else:
                    parts.append(cur)
        else:
            parts = [w]
        for pw in parts:
            k = -(-len(pw) // maxw)  # nº de pedaços
            size = -(-len(pw) // k)
            for i in range(0, len(pw), size):
                out.append(' '.join(pw[i:i + size]))
    return out


def dur_of(chunk):
    n = len(chunk.split())
    pauses = len(re.findall(r'[.!?…]', chunk))
    return max(1.3, n * SEC_PER_WORD + 0.2 * pauses + 0.2)


def run(cmd):
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------- música
def note(n):  # n = midi
    return 440.0 * 2 ** ((n - 69) / 12)


def synth_music(total, seed, intense_from=None, sfx=()):
    t = np.arange(int(total * SR)) / SR
    out = np.zeros_like(t)
    bpm = 92
    beat = 60 / bpm
    bar = 4 * beat
    prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]  # Am F C G
    rng = np.random.default_rng(seed)
    nbars = int(total / bar) + 1
    for b in range(nbars):
        root, ch = prog[b % 4]
        t0 = b * bar
        i0, i1 = int(t0 * SR), min(len(t), int((t0 + bar) * SR))
        if i0 >= len(t):
            break
        tt = t[i0:i1] - t0
        env = np.minimum(1, tt / 0.6) * np.minimum(1, (bar - tt) / 0.4)
        pad = sum(np.sin(2 * np.pi * note(m + 12) * tt) + 0.3 * np.sin(2 * np.pi * note(m + 24) * tt + 0.3) for m in ch)
        out[i0:i1] += 0.05 * pad * env
        out[i0:i1] += 0.10 * np.sin(2 * np.pi * note(root - 12) * tt) * env
        # arpejo (pluck) em colcheias
        arp = ch + [ch[1] + 12, ch[2] + 12, ch[0] + 12, ch[2], ch[1]]
        for k in range(8):
            s0 = t0 + k * beat / 2
            j0 = int(s0 * SR); j1 = min(len(t), j0 + int(0.6 * SR))
            if j0 >= len(t):
                break
            ts = t[j0:j1] - s0
            m = arp[k % len(arp)] + 24
            out[j0:j1] += 0.06 * np.sin(2 * np.pi * note(m) * ts) * np.exp(-ts * 6)
        # bateria depois da introdução
        if t0 >= 4 * beat:
            hard = intense_from is not None and t0 >= intense_from
            for k in range(4):
                s0 = t0 + k * beat
                j0 = int(s0 * SR); j1 = min(len(t), j0 + int(0.25 * SR))
                if j0 >= len(t):
                    break
                ts = t[j0:j1] - s0
                if k in (0, 2) or hard:
                    f = 110 * np.exp(-ts * 30) + 45
                    out[j0:j1] += (0.30 if hard else 0.22) * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-ts * 12)
                if k in (1, 3):
                    n = rng.standard_normal(j1 - j0)
                    out[j0:j1] += 0.06 * n * np.exp(-ts * 22)
                for h in (0, 0.5):
                    h0 = int((s0 + h * beat) * SR); h1 = min(len(t), h0 + int(0.05 * SR))
                    if h0 < len(t):
                        out[h0:h1] += 0.025 * rng.standard_normal(h1 - h0) * np.exp(-np.arange(h1 - h0) / SR * 80)
    # efeitos de torcida
    for kind, st, ln in sfx:
        j0 = int(st * SR); j1 = min(len(t), j0 + int(ln * SR))
        n = rng.standard_normal(j1 - j0)
        # filtro passa-banda grosseiro: média móvel (passa-baixa) menos passa-baixa mais larga
        lp = np.convolve(n, np.ones(6) / 6, mode='same') - np.convolve(n, np.ones(60) / 60, mode='same')
        ts = np.arange(j1 - j0) / SR
        mod = 0.7 + 0.3 * np.sin(2 * np.pi * 2.2 * ts)  # "Ben-ja-min" ritmado
        env = np.minimum(1, ts / 0.8) * np.minimum(1, (ln - ts) / 1.2)
        amp = 0.18 if kind == 'crowd_soft' else 0.45
        out[j0:j1] += amp * lp * env * (mod if kind == 'crowd_soft' else 1)
    # fade geral
    fade = np.minimum(1, t / 1.5) * np.minimum(1, (total - t) / 2.5)
    out *= fade
    out /= max(1e-6, np.abs(out).max()) / 0.8
    return out


def write_wav(path, x):
    x16 = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    st = np.stack([x16, x16], axis=1).reshape(-1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(st.tobytes())


# ---------------------------------------------------------------- build
def build(name, cfg):
    print(f'== {name}')
    # 1) linha do tempo
    timeline = []  # (scene, start, dur, [(text, s, e)])
    t = 0.0
    for i, (sc, text) in enumerate(cfg['scenes']):
        start = t
        cs = chunks(text)
        cur = start + (TITLE if i == 0 else 0.4)
        caps = []
        for c in cs:
            d = dur_of(c)
            caps.append((c, cur, cur + d))
            cur += d
        end = cur + 0.4
        if i == len(cfg['scenes']) - 1:
            end += 5.0  # tempo extra com os botões / chamada final
        timeline.append((sc, start, end - start, caps))
        t = end
    total = t
    print(f'   duração: {total:.1f}s')

    # 2) overlays (PNG transparentes)
    jobs = []
    def job(q, out):
        jobs.append({'q': urllib.parse.urlencode(q), 'out': out, 'transparent': True})
    job({'type': 'meter', 'v': 0}, f'{B}/{name}_meter.png')
    job({'type': 'title', 'sub': cfg['sub']}, f'{B}/{name}_title.png')
    job({'type': cfg['end']}, f'{B}/{name}_end.png')
    cap_files = []
    last_scene = timeline[-1][0]
    for sc, _, _, caps in timeline:
        for k, (c, s, e) in enumerate(caps):
            f = f'{B}/{name}_cap_{sc}_{k}.png'
            top = 1040 if (sc == last_scene and cfg['end'] == 'buttons') else 1290
            job({'type': 'caption', 'text': c, 'top': top}, f)
            cap_files.append((f, s, e))
    jf = f'{B}/{name}_jobs.json'
    json.dump(jobs, open(jf, 'w'))
    run(['node', f'{HERE}/render_jobs.js', jf])

    # 3) clipes de cena com zoom lento (Ken Burns)
    seg_files = []
    for i, (sc, start, dur, _) in enumerate(timeline):
        d = dur + (XF if i < len(timeline) - 1 else 0)
        n = int(round(d * FPS))
        z = "1+0.10*on/{n}".format(n=n) if i % 2 == 0 else "1.10-0.10*on/{n}".format(n=n)
        out = f'{B}/{name}_seg{i}.mp4'
        if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(f'{B}/{sc}.png'):
          run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', f'{B}/{sc}.png',
             '-vf', f"scale=1620:2880,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps={FPS},format=yuv420p",
             '-frames:v', str(n), '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '14', out])
        seg_files.append((out, d))

    # 4) junta as cenas com transição + sobreposições
    inputs, fc = [], []
    for f, _ in seg_files:
        inputs += ['-i', f]
    prev = '[0:v]'
    off = 0.0
    for i in range(1, len(seg_files)):
        off += timeline[i - 1][2]
        fc.append(f'{prev}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{i}]')
        prev = f'[x{i}]'
    nseg = len(seg_files)
    ov = [(f'{B}/{name}_meter.png', TITLE, total),
          (f'{B}/{name}_title.png', 0, TITLE)]
    ov += cap_files
    last_caps = timeline[-1][3]
    end_start = last_caps[1][1] if cfg['end'] == 'buttons' else last_caps[-1][2]
    ov.append((f'{B}/{name}_end.png', end_start, total))
    # compõe uma única trilha de sobreposição: um PNG por intervalo de tempo
    from PIL import Image
    cuts = sorted({0.0, total, *[x for _, s_, e_ in ov for x in (s_, e_)]})
    cache = {}
    lines = []
    for k in range(len(cuts) - 1):
        a_, b_ = cuts[k], cuts[k + 1]
        if b_ - a_ < 1e-3:
            continue
        mid = (a_ + b_) / 2
        active = tuple(f for f, s_, e_ in ov if s_ <= mid < e_)
        if active not in cache:
            img = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
            for f in active:
                img.alpha_composite(Image.open(f).convert('RGBA'))
            fn = f'{B}/{name}_ovl{len(cache)}.png'
            img.save(fn)
            cache[active] = fn
        lines.append(f"file '{cache[active]}'\nduration {b_ - a_:.3f}")
    lines.append(f"file '{lines[-1].split(chr(39))[1]}'")
    cl = f'{B}/{name}_ovl.txt'
    open(cl, 'w').write('\n'.join(lines) + '\n')
    inputs += ['-f', 'concat', '-safe', '0', '-i', cl]
    fc.append(f'[{nseg}:v]fps={FPS},format=rgba[ovl]')
    fc.append(f'{prev}[ovl]overlay=0:0:shortest=0:eof_action=repeat[vout]')
    prev = '[vout]'
    ov = [None]

    # 5) música
    sfx = []
    for sc, start, dur, _ in timeline:
        kind = cfg['sfx'].get(sc)
        if kind:
            sfx.append((kind, start + (2.5 if kind == 'crowd_goal' else 1.0), min(dur - 1.0, 6.0)))
    intense = timeline[3][1] if name == 'parte2' else None
    music = synth_music(total, seed=len(name) + (1 if name == 'parte1' else 2), intense_from=intense, sfx=sfx)
    wav = f'{B}/{name}_music.wav'
    write_wav(wav, music * 0.9)
    inputs += ['-i', wav]
    aidx = nseg + len(ov)

    out = os.path.join(HERE, f'{name}.mp4')
    run(['ffmpeg', '-y', '-loglevel', 'error', *inputs,
         '-filter_complex', ';'.join(fc), '-map', prev, '-map', f'{aidx}:a',
         '-t', f'{total:.3f}', '-r', str(FPS), '-c:v', 'libx264', '-preset', 'medium', '-crf', '22',
         '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', out])
    print('   ok ->', out)


if __name__ == '__main__':
    import sys
    scenes = [sc for c in PARTS.values() for sc, _ in c['scenes']]
    if '--rescenes' in sys.argv or any(not os.path.exists(f'{B}/{sc}.png') for sc in scenes):
        run(['node', f'{HERE}/render_scenes.js'])
    for name, cfg in PARTS.items():
        build(name, cfg)
