import sqlite3

DB_PATH = "instance/salonconnect.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def adicionar_coluna_se_nao_existir(
    tabela,
    coluna,
    tipo
):
    colunas = [
        row[1]
        for row in cursor.execute(
            f"PRAGMA table_info({tabela})"
        ).fetchall()
    ]

    if coluna not in colunas:
        cursor.execute(
            f"""
            ALTER TABLE {tabela}
            ADD COLUMN {coluna} {tipo}
            """
        )

adicionar_coluna_se_nao_existir(
    "configuracao_contrato",
    "contratos_feitos_por",
    "TEXT"
)

adicionar_coluna_se_nao_existir(
    "contratos",
    "contrato_feito_por",
    "TEXT"
)

conn.commit()
conn.close()

print("Colunas verificadas/criadas com sucesso.")