"""Converte a exportação de produtos da Drezi para o modelo de importação.

Uso:
    python3 converter.py exportacao.csv saida.csv [--imagem-base URL] [--imagem-tamanho 1600x2000] [--so-primeira-imagem]

--imagem-base troca o prefixo "media://" das imagens pela URL pública da loja
(ex.: https://cdn.dooca.store/184072/). Sem ela, a coluna imagem_url fica vazia.
--imagem-tamanho acrescenta o sufixo de tamanho do CDN (ex.: 1600x2000 vira foto_1600x2000.jpeg).
"""
import argparse
import csv
import re

COLUNAS = ["nome", "sku", "preco", "preco_promocional", "variacoes", "visivel",
           "frete_gratis", "tags", "descricao", "imagem_url"]
ORDEM_TAMANHOS = ["PP", "P", "M", "G", "GG", "XG"]


def preco(valor):
    valor = valor.strip().replace(",", ".")
    return f"{float(valor):.2f}" if valor else ""


def estoque(valor):
    valor = valor.strip().replace(",", ".")
    return str(int(float(valor))) if valor else "0"


def descricao(produto):
    longa = produto["description"].strip()
    curta = produto["short_description"].strip()
    if curta and re.sub(r"<[^>]+>", "", curta).strip() not in longa:
        return f"{curta}<br><br>{longa}" if longa else curta
    return longa


def imagens(produto, base, tamanho, so_primeira):
    if not base:
        return ""
    urls = []
    for img in produto["images"].split(","):
        caminho = img.strip().removeprefix("media://")
        if not caminho:
            continue
        if tamanho:
            nome, ponto, ext = caminho.rpartition(".")
            caminho = f"{nome}_{tamanho}.{ext}" if ponto else f"{caminho}_{tamanho}"
        urls.append(base.rstrip("/") + "/" + caminho)
    return ";".join(urls[:1] if so_primeira else urls)


def variacoes(produto, filhas):
    itens = [(f["first_attribute_value"].strip() or "Único", estoque(f["stock"])) for f in filhas]
    if not itens:
        itens = [("Único", estoque(produto["stock"]))]
    itens.sort(key=lambda i: ORDEM_TAMANHOS.index(i[0]) if i[0] in ORDEM_TAMANHOS else len(ORDEM_TAMANHOS))
    return ";".join(f"{nome}:{qtd}" for nome, qtd in itens)


def sku(produto, filhas):
    skus = [f["sku"].strip() for f in filhas if f["sku"].strip()]
    if produto["sku"].strip():
        return produto["sku"].strip()
    if len(filhas) == 1 and skus:
        return f"DRZ-{skus[0]}"
    return f"DRZ-{produto['product_id'].strip()}"


def converter(entrada, saida, base, tamanho, so_primeira):
    with open(entrada, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))

    produtos, filhas = {}, {}
    for linha in linhas:
        pid = linha["product_id"].strip()
        if linha["variation_id"].strip():
            filhas.setdefault(pid, []).append(linha)
        else:
            produtos[pid] = linha

    with open(saida, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, quoting=csv.QUOTE_ALL)
        escritor.writerow(COLUNAS)
        for pid, p in produtos.items():
            vs = filhas.get(pid, [])
            # Na exportação, "price" é o valor cobrado e "price_compare" o "de" riscado.
            cheio, cobrado = preco(p["price_compare"]), preco(p["price"])
            promocional = cobrado if cheio and float(cheio) > float(cobrado) else ""
            tags = [c.strip() for c in (p["category_1"], p["category_2"], p["category_3"]) if c.strip()]
            escritor.writerow([
                p["name"].strip(),
                sku(p, vs),
                cheio if promocional else cobrado,
                promocional,
                variacoes(p, vs),
                "sim" if p["active"].strip() == "1" else "nao",
                "nao",
                ";".join(dict.fromkeys(tags)),
                descricao(p),
                imagens(p, base, tamanho, so_primeira),
            ])
    return len(produtos)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--imagem-base", default="")
    ap.add_argument("--imagem-tamanho", default="")
    ap.add_argument("--so-primeira-imagem", action="store_true")
    a = ap.parse_args()
    print(converter(a.entrada, a.saida, a.imagem_base, a.imagem_tamanho, a.so_primeira_imagem), "produtos convertidos")
