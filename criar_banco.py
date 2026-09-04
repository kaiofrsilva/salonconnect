import os
import sqlite3


# ============================================================
# CAMINHO DO BANCO
# ============================================================

CAMINHO_BANCO = os.path.join(
    "instance",
    "salonconnect.db"
)


# ============================================================
# GARANTE QUE A PASTA INSTANCE EXISTE
# ============================================================

os.makedirs(
    os.path.dirname(CAMINHO_BANCO),
    exist_ok=True
)


# ============================================================
# CONEXÃO COM O BANCO
# ============================================================

conexao = sqlite3.connect(
    CAMINHO_BANCO
)

cursor = conexao.cursor()


try:

    # ========================================================
    # CRIA A TABELA DE SERVIÇOS CONTRATADOS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servicos_contratados (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            salao_id INTEGER NOT NULL,

            contrato_id INTEGER NOT NULL,

            nome VARCHAR(150) NOT NULL,

            valor REAL NOT NULL DEFAULT 0,

            informacoes TEXT,

            status_pagamento VARCHAR(30) NOT NULL
                DEFAULT 'Pendente pagamento',

            criado_em DATETIME
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (salao_id)
                REFERENCES saloes(id),

            FOREIGN KEY (contrato_id)
                REFERENCES contratos(id)
        )
    """)


    # ========================================================
    # SALVA ALTERAÇÕES
    # ========================================================

    conexao.commit()


    print()
    print("=" * 60)
    print(" TABELA DE SERVIÇOS CONTRATADOS")
    print("=" * 60)
    print()
    print("Banco:")
    print(os.path.abspath(CAMINHO_BANCO))
    print()
    print(
        "Tabela 'servicos_contratados' "
        "criada/verificada com sucesso!"
    )
    print()
    print("Campos:")
    print("  - id")
    print("  - salao_id")
    print("  - contrato_id")
    print("  - nome")
    print("  - valor")
    print("  - informacoes")
    print("  - status_pagamento")
    print("  - criado_em")
    print()
    print("=" * 60)
    print()


except Exception as erro:

    # ========================================================
    # ERRO
    # ========================================================

    conexao.rollback()

    print()
    print("=" * 60)
    print(" ERRO AO CRIAR A TABELA DE SERVIÇOS")
    print("=" * 60)
    print()
    print(erro)
    print()
    print("=" * 60)
    print()


finally:

    # ========================================================
    # FECHA CONEXÃO
    # ========================================================

    conexao.close()