import sqlite3


conn = sqlite3.connect("instance/salonconnect.db")
cursor = conn.cursor()


# ==========================================================
# ADICIONA A COLUNA dados_contrato NA TABELA contratos
# ==========================================================

try:
    cursor.execute("""
        ALTER TABLE contratos
        ADD COLUMN dados_contrato TEXT
    """)
    print("Coluna dados_contrato adicionada com sucesso.")

except Exception as e:
    print("dados_contrato:", e)


# ==========================================================
# TABELA DE ITENS DO ESTOQUE
# ==========================================================

try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            salao_id INTEGER NOT NULL,

            nome TEXT NOT NULL,
            categoria TEXT,
            unidade TEXT DEFAULT 'unidade',

            quantidade REAL DEFAULT 0,

            estoque_minimo REAL DEFAULT 0,
            estoque_medio REAL DEFAULT 0,

            preco REAL DEFAULT 0,

            consumo_por_pessoa REAL DEFAULT 0,

            ativo INTEGER DEFAULT 1,

            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (salao_id)
                REFERENCES saloes(id)
        )
    """)

    print("Tabela estoque_itens criada/verificada com sucesso.")

except Exception as e:
    print("estoque_itens:", e)


# ==========================================================
# TABELA DE MOVIMENTAÇÕES DO ESTOQUE
# ==========================================================

try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            salao_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,

            tipo TEXT NOT NULL,

            quantidade REAL NOT NULL,

            quantidade_anterior REAL DEFAULT 0,
            quantidade_nova REAL DEFAULT 0,

            preco_unitario REAL DEFAULT 0,

            contrato_id INTEGER,

            observacao TEXT,

            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (salao_id)
                REFERENCES saloes(id),

            FOREIGN KEY (item_id)
                REFERENCES estoque_itens(id),

            FOREIGN KEY (contrato_id)
                REFERENCES contratos(id)
        )
    """)

    print("Tabela estoque_movimentacoes criada/verificada com sucesso.")

except Exception as e:
    print("estoque_movimentacoes:", e)


# ==========================================================
# ÍNDICES PARA MELHORAR AS CONSULTAS
# ==========================================================

try:
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_estoque_itens_salao
        ON estoque_itens(salao_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_estoque_movimentacoes_salao
        ON estoque_movimentacoes(salao_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_estoque_movimentacoes_item
        ON estoque_movimentacoes(item_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_estoque_movimentacoes_contrato
        ON estoque_movimentacoes(contrato_id)
    """)

    print("Índices do estoque criados/verificados com sucesso.")

except Exception as e:
    print("Índices:", e)


# ==========================================================
# FINALIZA
# ==========================================================

conn.commit()
conn.close()

print("")
print("Banco de dados atualizado com sucesso!")