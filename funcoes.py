import os
import unicodedata
import time
import threading
import http.server
import socketserver
from datetime import datetime
from functools import partial
from playwright.sync_api import expect

PASTA_SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site_exemplo")
PASTA_RESULTADOS = "resultados"
PORTA = 0  # 0 = o sistema escolhe uma porta livre


# Sobe o site de exemplo numa porta local (assim roda sem internet e no GitHub Actions)
class SemLog(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def subir_site(porta=PORTA):
    handler = partial(SemLog, directory=PASTA_SITE)
    servidor = socketserver.TCPServer(("127.0.0.1", porta), handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, f"http://127.0.0.1:{servidor.server_address[1]}"


def abrir_navegador(p, mostrar=False):
    navegador = p.chromium.launch(headless=not mostrar)
    contexto = navegador.new_context(viewport={"width": 1280, "height": 800})
    pagina = contexto.new_page()
    return navegador, pagina


class Teste:
    """Guarda os passos de um teste, com print de cada um."""

    def __init__(self, nome, pagina):
        self.nome = nome
        self.pagina = pagina
        self.passos = []
        self.status = "passou"
        self.erro = ""
        self.inicio = time.time()

    def passo(self, descricao):
        pasta = os.path.join(PASTA_RESULTADOS, "prints")
        os.makedirs(pasta, exist_ok=True)
        sem_acento = unicodedata.normalize("NFKD", self.nome).encode("ascii", "ignore").decode()
        nome_arquivo = f"{sem_acento}_{len(self.passos) + 1}.png".replace(" ", "_").lower()
        try:
            self.pagina.screenshot(path=os.path.join(pasta, nome_arquivo))
        except Exception:
            nome_arquivo = ""
        self.passos.append({"descricao": descricao, "print": f"prints/{nome_arquivo}" if nome_arquivo else ""})
        print(f"   ✔ {descricao}")

    def falhou(self, erro):
        self.status = "falhou"
        self.erro = str(erro).split("\n")[0][:300]
        self.passo("Tela no momento do erro")
        print(f"   ✘ {self.erro}")

    def duracao(self):
        return round(time.time() - self.inicio, 1)


# ------------------------------------------------------------ testes

def teste_login_valido(pagina, url):
    t = Teste("Login válido", pagina)
    try:
        pagina.goto(url + "/index.html")
        t.passo("Abriu a tela de login")
        pagina.get_by_label("E-mail").fill("teste@exemplo.com")
        pagina.get_by_label("Senha").fill("senha123")
        t.passo("Preencheu e-mail e senha")
        pagina.get_by_role("button", name="Entrar").click()
        expect(pagina.get_by_role("heading", name="Produtos")).to_be_visible()
        t.passo("Entrou e viu a lista de produtos")
    except Exception as e:
        t.falhou(e)
    return t


def teste_login_senha_errada(pagina, url):
    t = Teste("Login senha errada", pagina)
    try:
        pagina.goto(url + "/index.html")
        pagina.get_by_label("E-mail").fill("teste@exemplo.com")
        pagina.get_by_label("Senha").fill("errada")
        pagina.get_by_role("button", name="Entrar").click()
        expect(pagina.get_by_role("alert")).to_have_text("E-mail ou senha incorretos.")
        t.passo("Mostrou a mensagem de senha errada")
    except Exception as e:
        t.falhou(e)
    return t


def teste_cadastro(pagina, url):
    t = Teste("Cadastro", pagina)
    email = f"pedro{int(time.time())}@exemplo.com"
    try:
        pagina.goto(url + "/cadastro.html")
        t.passo("Abriu a tela de cadastro")
        pagina.get_by_label("Nome").fill("Pedro")
        pagina.get_by_label("E-mail").fill(email)
        pagina.get_by_label("Senha").fill("123")
        pagina.get_by_role("button", name="Criar conta").click()
        expect(pagina.get_by_role("alert")).to_contain_text("pelo menos 6")
        t.passo("Barrou senha curta")
        pagina.get_by_label("Senha").fill("minhasenha")
        pagina.get_by_role("button", name="Criar conta").click()
        expect(pagina.get_by_role("alert")).to_contain_text("Conta criada")
        t.passo("Criou a conta")
        # confere se a conta nova consegue entrar
        pagina.goto(url + "/index.html")
        pagina.get_by_label("E-mail").fill(email)
        pagina.get_by_label("Senha").fill("minhasenha")
        pagina.get_by_role("button", name="Entrar").click()
        expect(pagina.get_by_role("heading", name="Produtos")).to_be_visible()
        t.passo("Entrou com a conta nova")
    except Exception as e:
        t.falhou(e)
    return t


def teste_compra(pagina, url):
    t = Teste("Compra", pagina)
    try:
        pagina.goto(url + "/index.html")
        pagina.get_by_label("E-mail").fill("teste@exemplo.com")
        pagina.get_by_label("Senha").fill("senha123")
        pagina.get_by_role("button", name="Entrar").click()
        pagina.get_by_role("button", name="Adicionar Caderno").click()
        pagina.get_by_role("button", name="Adicionar Mochila").click()
        expect(pagina.locator("#qtd")).to_have_text("2")
        t.passo("Colocou 2 produtos no carrinho")
        pagina.get_by_role("link", name="Carrinho").click()
        expect(pagina.locator("#total")).to_have_text("R$ 154,90")
        t.passo("Conferiu o total (R$ 25,90 + R$ 129,00)")
        pagina.get_by_role("button", name="Finalizar compra").click()
        expect(pagina.get_by_role("heading", name="Pedido confirmado!")).to_be_visible()
        t.passo("Finalizou a compra")
    except Exception as e:
        t.falhou(e)
    return t


def teste_carrinho_vazio(pagina, url):
    t = Teste("Carrinho vazio", pagina)
    try:
        pagina.goto(url + "/index.html")
        pagina.evaluate("localStorage.setItem('carrinho', '[]')")
        pagina.goto(url + "/carrinho.html")
        pagina.get_by_role("button", name="Finalizar compra").click()
        expect(pagina.get_by_role("alert")).to_have_text("Seu carrinho está vazio.")
        t.passo("Não deixou finalizar com o carrinho vazio")
    except Exception as e:
        t.falhou(e)
    return t


TESTES = {
    "1": ("Login válido", teste_login_valido),
    "2": ("Login com senha errada", teste_login_senha_errada),
    "3": ("Cadastro", teste_cadastro),
    "4": ("Compra completa", teste_compra),
    "5": ("Carrinho vazio", teste_carrinho_vazio),
}


# ------------------------------------------------------------ relatório

def gerar_relatorio(resultados, url):
    passou = sum(1 for r in resultados if r.status == "passou")
    falhou = len(resultados) - passou
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    blocos = ""
    for r in resultados:
        passos = ""
        for i, p in enumerate(r.passos, 1):
            img = f'<a href="{p["print"]}"><img src="{p["print"]}" alt="{p["descricao"]}"></a>' if p["print"] else ""
            passos += f'<li><span>{i}. {p["descricao"]}</span>{img}</li>'
        erro = f'<p class="erro">Erro: {r.erro}</p>' if r.erro else ""
        blocos += f'''
        <details class="teste {r.status}" {"open" if r.status == "falhou" else ""}>
          <summary><b>{r.nome}</b> <span class="selo">{r.status}</span> <small>{r.duracao()} s</small></summary>
          {erro}<ol>{passos}</ol>
        </details>'''

    html = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Relatório de testes</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;margin:0;background:#f4f6fa;color:#1b2333}}
header{{background:#1b2a4a;color:#fff;padding:20px}}main{{max-width:960px;margin:20px auto;padding:0 16px}}
.resumo{{display:flex;gap:12px;margin-bottom:16px}}.resumo div{{background:#fff;border-radius:10px;padding:14px 18px}}
.resumo b{{font-size:28px;display:block}}.teste{{background:#fff;border-radius:10px;margin-bottom:10px;padding:12px 16px}}
summary{{cursor:pointer;font-size:17px}}.selo{{padding:2px 8px;border-radius:6px;font-size:13px;color:#fff}}
.passou .selo{{background:#0e7a4d}}.falhou .selo{{background:#a3231a}}.erro{{color:#a3231a}}
ol{{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}}
li span{{display:block;margin-bottom:6px}}img{{width:100%;border:1px solid #dde3ee;border-radius:6px}}
</style></head><body>
<header><h1>Relatório de testes E2E</h1><p>Site testado: {url} · {agora}</p></header>
<main><div class="resumo"><div><b>{len(resultados)}</b>testes</div><div><b>{passou}</b>passaram</div><div><b>{falhou}</b>falharam</div></div>
{blocos}</main></body></html>'''

    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    caminho = os.path.join(PASTA_RESULTADOS, "relatorio.html")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(html)
    return caminho, falhou
