"""Junta as medições (medir.py) em analise.csv e resumo.md: categoria, qualidade, duplicatas (entre si e com o que já está em
zombiada assets/sfx) e, para cada id do SDK e as três lacunas, os melhores takes.

Uso: python relatorio.py <novos.json> <sdk.json> <manifest.json> <raiz dos novos> <raiz do assets/sfx> <pasta de saída>
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from regras import SDK_USES, classify

SAME_AUDIO = 0.9
GAPS = ('revolver_44_50ae', 'antimateriel_50bmg', 'bullet_flyby')


def quality(row: dict) -> int:
    row['piso_ruido_dbfs'] = max(row['piso_ruido_dbfs'], -90.0)
    score = 100
    if row['amostras_clipadas'] > 0:
        score -= min(30, 6 + row['amostras_clipadas'] // 20)
    rate = row['taxa_hz']
    score -= 25 if rate < 16000 else 12 if rate < 22050 else 4 if rate < 44100 else 0
    dynamic = row['pico_dbfs'] - row['piso_ruido_dbfs']
    score -= 15 if dynamic < 30 else 6 if dynamic < 45 else 0
    if row['pico_dbfs'] < -12:
        score -= 8
    if row['duracao_s'] < 0.05:
        score -= 20
    return max(score, 0)


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    if not len(a) or not len(b):
        return 0.0
    size = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    corr = np.fft.irfft(np.fft.rfft(a, size) * np.conj(np.fft.rfft(b, size)), size)
    norm = np.sqrt((a ** 2).sum() * (b ** 2).sum())
    return float(np.abs(corr).max() / norm) if norm > 0 else 0.0


def mark_duplicates(rows: list[dict], sdk: list[dict]) -> None:
    first_by_hash: dict[str, str] = {}
    for row in rows:
        row['duplicata_de'] = first_by_hash.setdefault(row['hash'], row['arquivo'])
        if row['duplicata_de'] == row['arquivo']:
            row['duplicata_de'] = ''
    by_folder = defaultdict(list)
    for row in rows:
        by_folder[str(Path(row['arquivo']).parent)].append(row)
    for siblings in by_folder.values():
        for index, row in enumerate(siblings):
            if row['duplicata_de']:
                continue
            for earlier in siblings[:index]:
                if not earlier['duplicata_de'] and abs(earlier['duracao_s'] - row['duracao_s']) < 0.05 * max(row['duracao_s'], 0.1) and similarity(row['fp'], earlier['fp']) > 0.97:
                    row['duplicata_de'] = earlier['arquivo'] + ' (quase igual)'
                    break
    for row in rows:
        row['igual_a_sdk'] = ''
        for take in sdk:
            if abs(take['duracao_s'] - row['duracao_s']) > 0.25 * max(row['duracao_s'], 0.2):
                continue
            if similarity(row['fp'], take['fp']) >= SAME_AUDIO:
                row['igual_a_sdk'] = take['arquivo']
                break


def load(path: str, root: Path) -> list[dict]:
    rows = []
    for row in json.loads(Path(path).read_text()):
        fingerprint = np.array(row.pop('impressao'), dtype=np.float32)
        row['arquivo'] = str(Path(row.pop('caminho')).resolve().relative_to(root.resolve()))
        row['fp'] = fingerprint - fingerprint.mean() if len(fingerprint) else fingerprint
        row['qualidade'] = quality(row)
        rows.append(row)
    return rows


def sdk_takes(manifest: dict) -> dict[str, list[str]]:
    takes = {}
    for sound in manifest['sounds']:
        takes[sound['id']] = [entry['file'] for layer in sound['layers'].values() for entry in layer]
    return takes


def why(row: dict) -> str:
    parts = [f"{row['taxa_hz'] // 1000} kHz", f"{row['duracao_s']:.2f} s"]
    parts.append('sem clipping' if not row['amostras_clipadas'] else f"{row['amostras_clipadas']} amostras clipadas")
    parts.append(f"faixa {row['pico_dbfs'] - row['piso_ruido_dbfs']:.0f} dB acima do ruído")
    return ', '.join(parts)


def recommend(rows: list[dict], sdk_by_file: dict[str, dict], takes: dict[str, list[str]]) -> list[tuple]:
    table = []
    for sound_id in [*GAPS, *sorted(set(takes) - set(GAPS))]:
        pattern = SDK_USES.get(sound_id)
        if not pattern:
            continue
        found = [r for r in rows if re.search(pattern, r['arquivo'].lower()) and not r['duplicata_de'] and not r['igual_a_sdk']]
        found.sort(key=lambda r: (-r['qualidade'], -r['duracao_s']))
        best = found[:6]
        if not best:
            table.append((sound_id, '—', 'nenhum arquivo dos três pacotes faz esse som', 'manter'))
            continue
        current = [sdk_by_file[f]['qualidade'] for f in takes.get(sound_id, []) if f in sdk_by_file]
        mean_new = sum(r['qualidade'] for r in best) / len(best)
        if not current:
            action = 'novo id'
        elif mean_new >= sum(current) / len(current) + 10:
            action = f'substituir os {len(current)} atuais'
        elif mean_new >= sum(current) / len(current) - 10:
            action = f'juntar aos {len(current)} atuais'
        else:
            action = f'só para variar: abaixo dos {len(current)} atuais'
        names = '<br>'.join(f"`{r['arquivo']}` ({r['qualidade']})" for r in best)
        table.append((sound_id, names, why(best[0]), action))
    return table


def write_csv(rows: list[dict], path: Path) -> None:
    fields = ['arquivo', 'categoria', 'detalhe', 'duracao_s', 'taxa_hz', 'canais', 'pico_dbfs', 'rms_dbfs', 'amostras_clipadas', 'piso_ruido_dbfs',
              'centroide_hz', 'largura_banda_hz', 'grave_150hz', 'ataque_s', 'pico_relativo', 'som_util_s', 'qualidade', 'hash', 'duplicata_de', 'igual_a_sdk']
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows: list[dict], table: list[tuple], path: Path) -> None:
    lines = ['# Análise dos WAVs novos', '', f'{len(rows)} arquivos em `all-sounds-20250411/`, `weapons/` e `1632476553_next_gen_weapon_sounds/`.',
             'Qualidade de 0 a 100: desconta clipping, taxa de amostragem baixa, pouca distância entre o pico e o ruído de fundo, volume baixo e arquivo curto demais.',
             '', '## Por categoria', '', '| categoria | arquivos | qualidade média | com clipping | abaixo de 22 kHz | duplicatas | já no SDK |', '|---|---|---|---|---|---|---|']
    for category, items in sorted(defaultdict(list, {c: [r for r in rows if r['categoria'] == c] for c in {r['categoria'] for r in rows}}).items(), key=lambda kv: -len(kv[1])):
        lines.append(f"| {category} | {len(items)} | {sum(r['qualidade'] for r in items) / len(items):.0f} | {sum(r['amostras_clipadas'] > 0 for r in items)} | "
                     f"{sum(r['taxa_hz'] < 22050 for r in items)} | {sum(bool(r['duplicata_de']) for r in items)} | {sum(bool(r['igual_a_sdk']) for r in items)} |")
    rates = Counter(r['taxa_hz'] for r in rows)
    lines += ['', 'Taxas de amostragem: ' + ', '.join(f'{rate} Hz: {count}' for rate, count in sorted(rates.items())), '',
              '## Recomendação por id do SDK', '', 'Até 6 takes por id, do melhor para o pior (nota entre parênteses), sem duplicatas e sem o que já está no SDK. '
              'O motivo descreve o primeiro da lista. A ação compara a nota média dos recomendados com a dos takes atuais do id.', '',
              '| id | arquivos recomendados | motivo | substituir/juntar |', '|---|---|---|---|']
    lines += [f'| `{sound_id}` | {names} | {reason} | {action} |' for sound_id, names, reason, action in table]
    path.write_text('\n'.join(lines) + '\n')


def main() -> None:
    new_json, sdk_json, manifest_path, new_root, sdk_root, output = sys.argv[1:7]
    rows = load(new_json, Path(new_root))
    sdk = load(sdk_json, Path(sdk_root))
    for row in rows:
        row['categoria'], row['detalhe'] = classify(row['arquivo'])
    mark_duplicates(rows, sdk)
    takes = sdk_takes(json.loads(Path(manifest_path).read_text()))
    table = recommend(rows, {take['arquivo']: take for take in sdk}, takes)
    out = Path(output)
    write_csv(rows, out / 'analise.csv')
    write_summary(rows, table, out / 'resumo.md')
    print(f"{len(rows)} linhas, {sum(bool(r['duplicata_de']) for r in rows)} duplicatas, {sum(bool(r['igual_a_sdk']) for r in rows)} iguais ao SDK, {len(table)} ids")


if __name__ == '__main__':
    main()
