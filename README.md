# ZombiAdA — site das equipes

Portal das equipes e documentação offline do jogo, publicados em https://zombiada.adatechnology.com.br.
Tudo abre sem internet: three.js e fontes vêm de `vendor/`, e nenhuma página aponta para o Claude.

## Pastas

| Pasta | O que guarda |
|---|---|
| `site/pages/<seção>/` | Páginas do jogo, uma pasta por seção. Publicadas em `/docs/offline/<seção>/` |
| `site/portal/` | Portal das equipes. Publicado em `/` e `/portal/portal-equipes.html` |
| `site/kit/` | Kit de peças (template). As peças vêm da Galeria do Vale Cinzento a cada build |
| `site/templates/` | Índice da documentação offline, montado a partir do `site.config.json` |
| `tools/build/` | Pipeline: gera `dist/`, troca links de artefato por páginas locais, embute libs, checa offline |
| `vendor/` | three.js r128 e fontes (Barlow Condensed, IBM Plex, JetBrains Mono) |
| `deploy/` | Configuração do Caddy |
| `dist/` | Saída gerada. Fora do git |

`site.config.json` define seções, páginas, descrições e tags do índice e, em `artifacts`, o mapa
de cada artefato publicado para a página local que o substitui.

## Comandos

```bash
make site    # gera dist/ e roda a checagem offline
make serve   # gera e serve em http://localhost:4800
make image   # build da mesma imagem que o Railway usa
```

## Página nova

1. Salve o `.html` em `site/pages/<seção>/`.
2. Acrescente a página na seção certa de `site.config.json`. Se ela veio de um artefato do Claude,
   acrescente o id em `artifacts`.
3. `make site`. O build avisa se a página ficou fora do índice; a checagem falha se ela carregar algo
   da internet ou apontar para `claude.ai`.

## Publicação

Fluxo: branch `staging` → PR → `main`. O Railway (projeto `zombiada`, serviço `site`, workspace
AdA Technology) faz o build do `Dockerfile` a cada push na `main`. O próprio build roda a checagem
offline, então uma página que dependa da internet impede o deploy.
