# Gera dist/ a partir de site/ + vendor/ e garante que nada depende de internet.
.PHONY: site check serve image

site:
	node tools/build/build-site.mjs
	node tools/build/check-offline.mjs

check:
	node tools/build/check-offline.mjs

serve: site
	python3 -m http.server 4800 --directory dist

image:
	docker build -t zombiada-site .
