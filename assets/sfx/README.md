# Sons do jogo

Os arquivos de som do ZombiAdA e do game-kit moram aqui. O game-kit (SDK público) não guarda nenhum áudio: ele só tem as referências
(`packages/game-audio/assets/sfx/manifest.json`, id → caminho relativo a esta pasta, com fonte, autor e licença) e cai no som sintetizado quando o
arquivo não existe.

- `assets/sfx/<categoria>/<id>_<camada>_<nn>.ogg`: os arquivos convertidos (Ogg Vorbis, 48 kHz, mono, pico −1 dBFS). Os caminhos são os do manifesto do kit.
- `assets/sfx/CREDITOS.md`: quem gravou cada arquivo e a licença.
- `assets/sfx-originais/<categoria>/`: os originais baixados (wav etc.) e o `CREDITOS.md` que o conversor lê.

## Som novo

1. Ponha o original em `assets/sfx-originais/<categoria>/` com o nome `<id>_<camada>_<nn>` (ex.: `pistol_9mm_close_01.wav`) e a linha dele em
   `assets/sfx-originais/CREDITOS.md` (`arquivo | link da página | autor | licença`).
2. No game-kit, com `.sfx-local.json` apontando para cá (abaixo), rode `pnpm --filter @adatechnology/game-audio sfx:convert`. O `.ogg` sai em
   `assets/sfx/<categoria>/` deste repositório e o manifesto e os créditos atualizam no kit.

## Ligar o game-kit a esta pasta (sala de testes da 4280)

Na raiz do game-kit, `.sfx-local.json` (ignorado pelo git):

```json
{ "kit": "../zombiada/assets/sfx", "inbox": "../zombiada/assets/sfx-originais" }
```

Ou as variáveis `KIT_SFX_DIR` e `KIT_SFX_INBOX`.

## Licença

Este repositório também é público. Só entram aqui arquivos CC0 ou CC-BY (com crédito). Sonniss e Pixabay não podem ser publicados soltos num
repositório público.
