// Extrai as imagens de cada produto da loja aluzz.com.br.
// Como usar: abra https://aluzz.com.br no Chrome, aperte F12 (ou Cmd+Option+J no Mac),
// vá na aba "Console", cole este código inteiro e aperte Enter.
// No fim, o navegador baixa o arquivo "aluzz-imagens.json".
(async () => {
  const handles = ["regata-jack-bqcx8", "calca-dora-mcuo0", "calca-marta-1obk9", "blusa-milena-1x457", "trijunto-bia", "camisa-selena", "blusa-nina", "conjunto-gloria", "conjunto-julieta", "conjunto-grazy", "conjunto-lilia", "conjunto-laila", "trijunto-melissa", "trijunto-cora", "conjunto-eloise", "conjunto-cintia", "camisa-nivia", "vestido-cris", "calca-taina", "vestido-eva", "conjuinto-alice", "blusa-betina", "blusa-sarah", "conjunto-hanna", "camisa-emilia", "blusa-isabella", "conjunto-alana", "conjunto-izabel", "camisa-mirela", "macaquito-sol", "conjunto-larissa", "calca-rebeca", "top-monique", "conjunto-mariah", "short-nina1", "calca-aline", "t-shirt-poa", "calca-isadora", "regata-ju", "regata-maria", "baby-tee-sofia", "calca-bandana", "blusa-trico-lara", "corset-cindy", "calca-julia", "blusa-sabrina", "camisa-manuela", "calca-manuela", "conjunto-louise", "blazer-zara", "vestido-charlote", "calca-karen", "blusa-claudia", "calca-lolla", "calca-chloe", "regata-adele", "blusa-alana", "cropped-isadora", "vestido-luna", "vestido-gabriela", "conjunto-eduarda", "conjunto-jana", "conjunto-marcela", "conjunto-barbie", "conjunto-yasmin", "camisa-heloisa", "calca-mila", "calca-catarina", "calca-susi", "conjunto-luiza", "conjunto-duda", "cropped-iara", "blusa-livia", "blusa-elisa", "body-celine", "blusa-flora", "blusa-aurora", "blusa-olivia", "blusa-valentina", "blusa-vitoria", "blusa-laressa", "blusa-serena", "blusa-jade", "regata-mila", "blusa-bianca", "trijunto-marina", "conjunto-camila", "macacao-zoe", "conjunto-july", "regata-ana", "blusa-clara", "blusa-iza", "regata-bruna", "conjunto-mel", "conjunto-mari", "conjunto-lore", "conjunto-lais", "regata-laura", "body-victoria", "blusa-samela", "blusa-luana", "blusa-lola", "t-shirt-cleo", "regata-liz", "blusa-brenda", "regata-suzi", "body-clea"];

  const IMG_RE = /(?:https?:)?\/\/[a-z0-9.-]*mitiendanube\.com\/stores\/[^\s"'()<>,]+?\/products\/[^\s"'()<>,]+?\.(?:jpe?g|png|webp|gif)/gi;
  const RELATED_RE = /related|relacionad|recomend|similar|cross|upsell/i;

  const isRelated = (el) => {
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const marks = [e.id, typeof e.className === "string" ? e.className : "", e.getAttribute("data-store") || ""].join(" ");
      if (RELATED_RE.test(marks)) return true;
    }
    return false;
  };

  const result = [];
  for (const [i, handle] of handles.entries()) {
    const entry = { handle, status: null, title: null, og_image: null, images: [] };
    try {
      const res = await fetch(`/produtos/${handle}/`, { credentials: "include" });
      entry.status = res.status;
      if (res.ok) {
        const doc = new DOMParser().parseFromString(await res.text(), "text/html");
        entry.title = doc.querySelector("h1")?.textContent.trim() || doc.title;
        entry.og_image = doc.querySelector('meta[property="og:image"]')?.content || null;
        const seen = new Set();
        for (const el of doc.querySelectorAll("*")) {
          for (const attr of el.attributes) {
            for (const url of attr.value.match(IMG_RE) || []) {
              const key = url + "|" + isRelated(el);
              if (seen.has(key)) continue;
              seen.add(key);
              entry.images.push({ url, related: isRelated(el) });
            }
          }
        }
      }
    } catch (err) {
      entry.status = "erro: " + err.message;
    }
    result.push(entry);
    console.log(`${i + 1}/${handles.length} ${handle} -> ${entry.status}, ${entry.images.length} URLs`);
    await new Promise((r) => setTimeout(r, 400));
  }

  const blob = new Blob([JSON.stringify(result, null, 1)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "aluzz-imagens.json";
  a.click();
  console.log("Pronto! Arquivo aluzz-imagens.json baixado.");
})();
