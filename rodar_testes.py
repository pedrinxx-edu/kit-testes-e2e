import sys
import shutil
from playwright.sync_api import sync_playwright
from funcoes import subir_site, abrir_navegador, gerar_relatorio, TESTES, PASTA_RESULTADOS


def escolher_testes():
    print("\n=== Kit de testes E2E ===")
    for numero, (nome, _) in TESTES.items():
        print(f"{numero} - {nome}")
    print("0 - Rodar todos")
    while True:
        opcao = input("\nQual teste? ").strip()
        if opcao == "0":
            return list(TESTES.keys())
        if opcao in TESTES:
            return [opcao]
        print("Opção inválida, tenta de novo.")


def main():
    # --todos: roda tudo sem perguntar (usado no GitHub Actions)
    # --mostrar: abre o navegador na tela pra ver os testes rodando
    escolhidos = list(TESTES.keys()) if "--todos" in sys.argv else escolher_testes()
    mostrar = "--mostrar" in sys.argv

    shutil.rmtree(PASTA_RESULTADOS, ignore_errors=True)
    servidor, url = subir_site()
    resultados = []

    with sync_playwright() as p:
        navegador, pagina = abrir_navegador(p, mostrar)
        for numero in escolhidos:
            nome, funcao = TESTES[numero]
            print(f"\n▶ {nome}")
            resultados.append(funcao(pagina, url))
        navegador.close()

    servidor.shutdown()
    caminho, falhou = gerar_relatorio(resultados, url)
    print(f"\nRelatório: {caminho}")
    print(f"{len(resultados) - falhou} passaram, {falhou} falharam")
    sys.exit(1 if falhou else 0)


if __name__ == "__main__":
    main()
