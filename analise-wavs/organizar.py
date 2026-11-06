"""Monta a pasta local de sons (fora do git): converte os takes escolhidos para Ogg mono 48 kHz a -1 dBFS sem silêncio inicial, dá a cada
arquivo o nome do item e da ação, e escreve manifest.json (formato UserSfxManifest do game-audio) e LEIA-ME.md.

Uso: python organizar.py <resumo.md> <raiz dos WAVs> <pasta de saída> <sons-sdk.json do zombiada/src> <ids do kit, um por linha>
"""
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

# ids que o zombiada usa (src/jogo/sons-sdk.json) e o kit ainda não grava: padrão do arquivo → id
EXTRAS: list[tuple[str, str]] = [
    (r'weapons/c4/c4_beep1', 'c4_beep'), (r'weapons/c4/c4_plant', 'c4_plant'), (r'weapons/c4/c4_disarm', 'c4_disarm'),
    (r'he_bounce-1|all-sounds-20250411/weapons/g_bounce[1-4]|grenade_hit1', 'grenade_bounce'),
    (r'^weapons/pinpull|aimsounds/pinpull', 'grenade_pin_pull'), (r'smokegrenade/sg_explode', 'smoke_grenade_hiss'),
    (r'flashbang_explode[12]', 'explosion_flashbang'),
    (r'knife/knife_stab|knife/knife_hit[1-4]', 'knife_stab'), (r'knife_hitwall1', 'knife_hit_wall'),
    (r'clipempty_(pistol|rifle)|all-sounds-20250411/weapons/dryfire1', 'dry_fire'),
    (r'^weapons/zoom|aimsounds/zoom', 'scope_zoom'),
    (r'aimsounds/(pistol|rifle|heavy|shotgun|smg|silenced|misc)in', 'weapon_draw'),
    (r'aimsounds/(pistol|rifle|heavy|shotgun|smg|silenced|misc)out', 'weapon_holster'),
    (r'(usp|m4a1)_silencer_on', 'suppressor_attach'), (r'(usp|m4a1)_silencer_off', 'suppressor_detach'),
    (r'm249_coverup', 'mg_cover_open'), (r'm249_coverdown', 'mg_cover_close'), (r'm249_chain', 'mg_belt_adjust'),
    (r'zombie/claw_strike', 'zombie_claw_hit'), (r'zombie/claw_miss', 'zombie_claw_miss'), (r'zombie/zo_attack', 'zombie_attack'),
    (r'zombie/zo_pain', 'zombie_pain'), (r'zombie/zo_alert', 'zombie_alert'), (r'zombie/zo_idle', 'zombie_groan'),
    (r'player/pl_tile', 'footstep_tile_walk'), (r'player/pl_grate', 'footstep_grate_walk'), (r'player/pl_duct', 'footstep_duct_walk'),
    (r'player/pl_slosh', 'footstep_water_walk'), (r'player/pl_ladder', 'ladder_climb'), (r'player/pl_fallpain', 'fall_damage'),
    (r'player/heartbeat1', 'heartbeat_critical'), (r'items/flashlight1', 'flashlight_toggle'), (r'items/smallmedkit', 'medkit_use'),
    (r'plats/elevmove', 'elevator_move_loop'), (r'fans/fan[1-5]\.wav', 'fan_loop'), (r'ambience/jetflyby1', 'jet_flyby'),
    (r'ambience/(wind[12]|des_wind[1-3])', 'wind_loop'), (r'apache/ap_rotor', 'helicopter_loop'),
]

# id → (pasta do kit, nome do item e da ação em português)
NAMES: dict[str, tuple[str, str]] = {
    'revolver_44_50ae': ('armas', 'deagle_tiro'), 'antimateriel_50bmg': ('armas', 'fuzil_50_tiro'), 'bullet_whiz': ('armas', 'bala_passando'),
    'bolt_pull_heavy': ('armas', 'ferrolho_puxar_pesado'), 'bolt_pull_medium': ('armas', 'ferrolho_puxar_medio'),
    'charging_handle_pull_medium': ('armas', 'alavanca_de_manejo_puxar'), 'slide_release_light': ('armas', 'ferrolho_soltar_leve'),
    'mag_out_light': ('armas', 'carregador_tirar_leve'), 'mag_out_medium': ('armas', 'carregador_tirar_medio'), 'mag_out_heavy': ('armas', 'carregador_tirar_pesado'),
    'mag_seat_light': ('armas', 'carregador_por_leve'), 'mag_seat_medium': ('armas', 'carregador_por_medio'), 'mag_seat_heavy': ('armas', 'carregador_por_pesado'),
    'casing_drop_concreto': ('armas', 'capsula_cair_concreto'), 'casing_drop_metal': ('armas', 'cartucho_cair_metal'),
    'cylinder_open_light': ('armas', 'tambor_abrir'), 'suppressed_pistol': ('armas', 'pistola_silenciada_tiro'),
    'swing_whoosh_alt': ('personagem', 'golpe_no_ar'), 'switch_click': ('itens-portas', 'interruptor_clicar'), 'lever_pull': ('itens-portas', 'alavanca_puxar'),
    'door_lock_unlock': ('itens-portas', 'trinco_destrancar'), 'door_locked_rattle': ('itens-portas', 'porta_trancada_forcar'),
    'door_wood_open': ('itens-portas', 'porta_abrir'), 'item_drop_metal': ('itens-portas', 'arma_largar'), 'item_pickup_generic': ('itens-portas', 'arma_pegar'),
    'c4_beep': ('armas', 'c4_bipe'), 'c4_plant': ('armas', 'c4_plantar'), 'c4_disarm': ('armas', 'c4_desarmar'),
    'grenade_bounce': ('armas', 'granada_quicar'), 'grenade_pin_pull': ('armas', 'granada_tirar_pino'), 'smoke_grenade_hiss': ('armas', 'granada_fumaca_chiar'),
    'explosion_flashbang': ('explosoes-fogo', 'granada_atordoante_explodir'), 'knife_stab': ('armas', 'faca_esfaquear'), 'knife_hit_wall': ('armas', 'faca_bater_parede'),
    'dry_fire': ('armas', 'gatilho_vazio'), 'scope_zoom': ('armas', 'luneta_zoom'), 'weapon_draw': ('armas', 'arma_sacar'), 'weapon_holster': ('armas', 'arma_guardar'),
    'suppressor_attach': ('armas', 'silenciador_colocar'), 'suppressor_detach': ('armas', 'silenciador_tirar'),
    'mg_cover_open': ('armas', 'metralhadora_tampa_abrir'), 'mg_cover_close': ('armas', 'metralhadora_tampa_fechar'), 'mg_belt_adjust': ('armas', 'metralhadora_fita_ajustar'),
    'zombie_claw_hit': ('personagem', 'zumbi_garra_acertar'), 'zombie_claw_miss': ('personagem', 'zumbi_garra_errar'), 'zombie_attack': ('personagem', 'zumbi_atacar'),
    'zombie_pain': ('personagem', 'zumbi_dor'), 'zombie_alert': ('personagem', 'zumbi_alerta'), 'zombie_groan': ('personagem', 'zumbi_gemer'),
    'footstep_tile_walk': ('personagem', 'passo_ladrilho'), 'footstep_grate_walk': ('personagem', 'passo_grade'), 'footstep_duct_walk': ('personagem', 'passo_duto'),
    'footstep_water_walk': ('personagem', 'passo_agua'), 'ladder_climb': ('personagem', 'escada_subir'), 'fall_damage': ('personagem', 'queda_dor'),
    'heartbeat_critical': ('personagem', 'coracao_batendo'), 'flashlight_toggle': ('itens-portas', 'lanterna_ligar'), 'medkit_use': ('itens-portas', 'kit_medico_usar'),
    'elevator_move_loop': ('itens-portas', 'elevador_mover'), 'fan_loop': ('ambiente', 'ventilador'), 'jet_flyby': ('veiculos', 'jato_passando'),
    'wind_loop': ('ambiente', 'vento'), 'helicopter_loop': ('veiculos', 'helicoptero_rotor'),
}

# arma do Counter-Strike (pasta) → nome do item no arquivo
WEAPON_NAMES = {'deagle': 'deagle', 'awp': 'awp', 'glock': 'glock', 'usp': 'usp', 'p228': 'p228', 'fiveseven': 'fiveseven', 'elite': 'beretta_dupla',
                'm4a1': 'm4a1', 'ak47': 'ak47', 'famas': 'famas', 'galil': 'galil', 'aug': 'aug', 'sg552': 'sg552', 'sg550': 'sg550', 'g3sg1': 'g3sg1',
                'scout': 'scout', 'mp5navy': 'mp5', 'mac10': 'mac10', 'ump45': 'ump45', 'tmp': 'tmp', 'p90': 'p90', 'm249': 'm249', 'm3': 'm3', 'xm1014': 'xm1014'}


def picks_from_summary(summary: Path) -> list[tuple[str, str]]:
    picks = []
    for line in summary.read_text().splitlines():
        match = re.match(r'\| `(\w+)` \| (.+) \| .+ \| (novo id|juntar[^|]*) \|$', line)
        if match:
            picks += [(match[1], f) for f in re.findall(r'`([^`]+\.wav)`', match[2])]
    return picks


def picks_from_extras(root: Path) -> list[tuple[str, str]]:
    files = sorted(str(p.relative_to(root)) for p in root.rglob('*.wav'))
    return [(sound_id, f) for pattern, sound_id in EXTRAS for f in files if re.search(pattern, f.lower())]


def file_stem(sound_id: str, source: str) -> tuple[str, str]:
    category, name = NAMES[sound_id]
    weapon = re.match(r'weapons/(\w+)/', source)
    if weapon and weapon[1] in WEAPON_NAMES and category == 'armas' and not name.startswith(('c4', 'granada', 'faca', 'metralhadora')):
        action = name.split('_', 1)[1] if name.startswith(('deagle', 'fuzil_50', 'pistola_silenciada')) else name
        shot = 'tiro_silenciado' if sound_id == 'suppressed_pistol' else 'tiro'
        name = f"{WEAPON_NAMES[weapon[1]]}_{shot if 'tiro' in action else action}"
    return category, name


def convert(source: Path, target: Path) -> tuple[float, float]:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix='.wav') as trimmed:
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(source), '-af', 'silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.005',
                        '-ac', '1', '-ar', '48000', trimmed.name], check=True)
        level = subprocess.run(['ffmpeg', '-nostats', '-i', trimmed.name, '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True).stderr
        peak = float(re.search(r'max_volume: (-?[\d.]+) dB', level)[1])
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', trimmed.name, '-af', f'volume={-1 - peak}dB', '-c:a', 'libvorbis', '-q:a', '6',
                        '-ac', '1', '-ar', '48000', str(target)], check=True)
    seconds = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(target)], capture_output=True, text=True).stdout)
    return round(seconds, 3), -1.0


def main() -> None:
    summary, root, output, game_manifest, kit_ids_file = map(Path, sys.argv[1:6])
    kit_ids = set(kit_ids_file.read_text().split())
    seen: set[str] = set()
    picks = [(i, f) for i, f in picks_from_summary(summary) + picks_from_extras(root) if not (f in seen or seen.add(f))]
    counters: dict[str, int] = defaultdict(int)
    sounds: dict[str, dict] = {}
    readme = ['# Sons locais (fora do git)', '', 'Gerado por `analise-wavs/organizar.py` (branch `claude/analise-wavs`). Cada arquivo: Ogg mono 48 kHz, pico a -1 dBFS, sem silêncio inicial.',
              'O game-kit lê esta pasta pelo `.sfx-local.json` ("root" e "manifest"). `primary`: o id toca este arquivo; `fallback`: o kit toca a gravação dele e este fica em `user:<id>`.',
              '', '| arquivo | original | id | papel |', '|---|---|---|---|']
    for sound_id, source in picks:
        category, stem = file_stem(sound_id, source)
        counters[f'{category}/{stem}'] += 1
        file = f'{category}/{stem}_{counters[f"{category}/{stem}"]:02d}.ogg'
        seconds, peak = convert(root / source, output / file)
        role = 'fallback' if sound_id in kit_ids else 'primary'
        entry = sounds.setdefault(sound_id, {'id': sound_id, 'category': category, 'role': role, 'label': stem.replace('_', ' '), 'layers': {'close': []}})
        entry['layers']['close'].append({'file': file, 'sampleRate': 48000, 'channels': 1, 'peak': peak, 'seconds': seconds,
                                         'source': str(root / source), 'author': 'pacote local', 'license': 'proprietary'})
        readme.append(f'| `{file}` | `{source}` | `{sound_id}` | {role} |')
    # os sons que o jogo já tinha em zombiada/src (sons-sdk.json) seguem tocando: a pasta tem um link `zombiada-src` para lá
    for sound in json.loads(game_manifest.read_text())['sounds']:
        layers = {layer: [{**take, 'file': f"zombiada-src/{take['file']}"} for take in takes] for layer, takes in sound['layers'].items()}
        if sound['id'] in sounds:
            sounds[sound['id']]['layers']['close'] += [t for takes in layers.values() for t in takes]
            if sound['role'] == 'primary':
                sounds[sound['id']]['role'] = 'primary'
        else:
            sounds[sound['id']] = {**sound, 'layers': layers}
    (output / 'manifest.json').write_text(json.dumps({'version': 1, 'sounds': list(sounds.values())}, ensure_ascii=False, indent=1) + '\n')
    (output / 'LEIA-ME.md').write_text('\n'.join(readme) + '\n')
    print(f'{len(picks)} arquivos convertidos, {len(sounds)} ids no manifest')


if __name__ == '__main__':
    main()
