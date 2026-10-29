# ZombiAdA — regras do repositório

## O SDK primeiro — **OBRIGATÓRIO** (dono, 2026-10-29)

Todo desenvolvimento de jogo do nosso lado parte do SDK `Andersonfrfilho/adatechnology-game-kit`, para nunca escrever código à toa.
Antes de escrever qualquer código de jogo (modelo 3D, animação, comportamento, efeito, tela, cena ou ambiente de teste), nesta ordem:

1. **Procure no SDK.** A skill `game-kit` do kit (`.claude/skills/game-kit/SKILL.md`) diz qual pacote faz o quê. Com o kit clonado ao lado
   deste repositório, o MCP do kit responde direto: `node ../adatechnology-game-kit/tools/kit-audit/mcp.mjs` (ferramentas `kit_owner`, para
   saber qual pacote é dono de uma peça, e `kit_origin`, para saber de onde ela veio). Sem o clone, leia os `README.md` dos pacotes do kit no GitHub.
2. **Existe:** use o pacote do kit, importado. Nunca copie o modelo ou o código do kit para cá: a mudança no SDK tem que aparecer no jogo.
3. **Não existe:** crie primeiro no pacote certo do kit (com teste e área de teste, seguindo o `CLAUDE.md` do kit) e só então use aqui.
   O que é só deste jogo (histórias, personagens nomeados, Vale Cinzento, sangue e marcas da horda) fica neste repositório, consumindo o kit.

**Cada peça vem do SDK dono:** carro e veículo do SDK de veículos (`game-vehicles-three` com a frota), parede e casa do `game-floorplan`,
móvel do catálogo de móveis, pessoa do `game-characters`, planta do `game-vegetation`, item do `game-items-goods`, arma e explosivo do
`game-weapons`. Nada de caixa ou geometria "parecida" no lugar de uma peça que o kit já tem.

As páginas que os times entregaram em `site/pages/` são a origem do que foi migrado para o kit (`specs/001-migracao-entregas-dos-times` do
kit). Antes de mexer numa peça delas, veja se ela já está no kit: se estiver, a mudança vai para o kit.

## Site

Como gerar, servir e publicar o site: `README.md` (fluxo `staging` → PR → `main`; o build roda a checagem offline).
