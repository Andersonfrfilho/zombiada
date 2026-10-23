# Imagem estática do site ZombiAdA (sem etapa de build, deploy rápido)
FROM caddy:2.8-alpine

# Configuração do servidor web
COPY Caddyfile /etc/caddy/Caddyfile

# Conteúdo do site
COPY www/ /srv
