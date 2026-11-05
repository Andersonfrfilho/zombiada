/**
 * @file audio-pool.js
 * Gerenciador de áudio assíncrono e de alto desempenho para o ZombiAdA / AdA Technology Game Kit.
 *
 * Características de Performance:
 * 1. Não bloqueia o loop de renderização (Zero Frame Drops): decodificação 100% assíncrona.
 * 2. Pré-carregamento inteligente durante tempo ocioso (requestIdleCallback).
 * 3. Fallback imediato: se o arquivo não estiver pronto, toca o som sintetizado original em 0ms.
 * 4. Configuração local protegida (lê de arquivo local se presente, com fallback para caminhos padrão).
 */

export class AdaAudioPool {
  constructor(audioContext, options = {}) {
    this.ac = audioContext;
    this.sampleCache = new Map();
    this.pendingRequests = new Map();
    this.catalog = null;
    this.options = {
      basePath: options.basePath || '../',
      maxPreloadBatch: options.maxPreloadBatch || 3,
      ...options
    };
  }

  /**
   * Inicializa o catálogo de áudio.
   */
  async initCatalog(mappingUrl = 'audio-mapping.json') {
    if (this.catalog) return this.catalog;
    try {
      const res = await fetch(mappingUrl);
      if (res.ok) {
        this.catalog = await res.json();
      }
    } catch {
      this.catalog = null;
    }
    return this.catalog;
  }

  /**
   * Obtém ou carrega um sample de forma assíncrona sem travar a thread.
   */
  async getSample(url) {
    if (this.sampleCache.has(url)) {
      return this.sampleCache.get(url);
    }
    if (this.pendingRequests.has(url)) {
      return this.pendingRequests.get(url);
    }

    const loadPromise = (async () => {
      try {
        const res = await fetch(url);
        if (!res.ok) return null;
        const arrayBuf = await res.arrayBuffer();
        const audioBuf = await this.ac.decodeAudioData(arrayBuf);
        this.sampleCache.set(url, audioBuf);
        return audioBuf;
      } catch {
        return null;
      } finally {
        this.pendingRequests.delete(url);
      }
    })();

    this.pendingRequests.set(url, loadPromise);
    return loadPromise;
  }

  /**
   * Pré-carrega um conjunto de sons durante frames ociosos (Idle Time)
   * garantindo 60 FPS contínuos no jogo.
   */
  scheduleIdlePreload(urls) {
    if (typeof window === 'undefined' || !window.requestIdleCallback) return;
    const queue = [...urls];

    const processNext = (deadline) => {
      while (deadline.timeRemaining() > 5 && queue.length > 0) {
        const nextUrl = queue.shift();
        this.getSample(nextUrl);
      }
      if (queue.length > 0) {
        window.requestIdleCallback(processNext);
      }
    };

    window.requestIdleCallback(processNext);
  }

  /**
   * Toca o sample se pronto; devolve false se ainda pendente (sinalizando fallback procedural).
   */
  playIfReady(url, destinationNode, { gain = 1, playbackRate = 1 } = {}) {
    if (!this.ac || this.ac.state === 'suspended') return false;
    const buffer = this.sampleCache.get(url);
    if (!buffer) {
      // Inicia o carregamento em background para os próximos disparos
      this.getSample(url);
      return false;
    }

    const src = this.ac.createBufferSource();
    src.buffer = buffer;
    src.playbackRate.value = playbackRate;

    const gainNode = this.ac.createGain();
    gainNode.gain.value = gain;

    src.connect(gainNode);
    gainNode.connect(destinationNode || this.ac.destination);
    src.start();
    return true;
  }
}
