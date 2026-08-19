from flask import Flask, render_template, request, jsonify, redirect, send_file, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from config import Config

import io
import re
import json
import unicodedata
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "salonconnect123456"

db = SQLAlchemy(app)

# ===========================
# MODELOS
# ===========================

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    cargo = db.Column(db.String(50), default="Administrador")
    ativo = db.Column(db.Boolean, default=True)

class Salao(db.Model):
    __tablename__ = "saloes"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(150), nullable=False)
    responsavel = db.Column(db.String(150), nullable=False)

    email = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)

    telefone = db.Column(db.String(20))
    cnpj = db.Column(db.String(20))
    cidade = db.Column(db.String(100))

    plano = db.Column(db.String(30), nullable=False)

    ativo = db.Column(db.Boolean, default=True)

    data_cadastro = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )
class Permissao(db.Model):
    __tablename__ = "permissoes"

    id = db.Column(db.Integer, primary_key=True)

    salao_id = db.Column(
        db.Integer,
        db.ForeignKey("saloes.id"),
        nullable=False
    )

    dashboard = db.Column(db.Boolean, default=True)

    agenda = db.Column(db.Boolean, default=True)

    contratos = db.Column(db.Boolean, default=True)

    estoque = db.Column(db.Boolean, default=False)

    financeiro = db.Column(db.Boolean, default=False)

    funcionarios = db.Column(db.Boolean, default=False)

    relatorios = db.Column(db.Boolean, default=False)

    configuracoes = db.Column(db.Boolean, default=False)

class Orcamento(db.Model):
    __tablename__ = "orcamentos"

    id = db.Column(db.Integer, primary_key=True)

    gestao = db.Column(db.Text, nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    whatsapp = db.Column(db.String(30), nullable=False)
    salao = db.Column(db.String(150), nullable=False)
    tamanho = db.Column(db.String(100))
    funcionarios = db.Column(db.Integer)
    origem = db.Column(db.String(100))
    plano = db.Column(db.String(100))
    data = db.Column(db.DateTime, default=datetime.utcnow)

class ConfiguracaoContrato(db.Model):
    __tablename__ = "configuracao_contrato"

    id = db.Column(db.Integer, primary_key=True)

    salao_id = db.Column(
        db.Integer,
        db.ForeignKey("saloes.id"),
        nullable=False
    )

    servicos = db.Column(db.Text)

    buffet = db.Column(db.Text)

    doces = db.Column(db.Text)

    adicionais = db.Column(db.Text)

    pacotes = db.Column(db.Text)

    valor_extra = db.Column(db.Float)
# ===========================
# CRIA BANCO E ADMIN
# ===========================

with app.app_context():

    db.create_all()

    if not Usuario.query.filter_by(email="admin@admin.com").first():

        admin = Usuario(
            nome="Administrador",
            email="admin@admin.com",
            senha=generate_password_hash("admin123")
        )

        db.session.add(admin)
        db.session.commit()

class Contrato(db.Model):
    __tablename__ = "contratos"

    id = db.Column(db.Integer, primary_key=True)

    salao_id = db.Column(
        db.Integer,
        db.ForeignKey("saloes.id"),
        nullable=False
    )

    # ==========================
    # DADOS DO CONTRATANTE
    # ==========================

    cliente = db.Column(db.String(150))

    telefone = db.Column(db.String(30))

    email = db.Column(db.String(150))

    cpf = db.Column(db.String(20))

    aniversariante = db.Column(db.String(150))

    data_evento = db.Column(db.String(20))

    data_aniversario = db.Column(db.String(20))

    hora_inicio = db.Column(db.String(10))

    hora_fim = db.Column(db.String(10))

    responsavel1 = db.Column(db.String(150))

    responsavel2 = db.Column(db.String(150))

    # ==========================
    # EVENTO
    # ==========================

    convidados = db.Column(db.Integer)

    pacote = db.Column(db.String(100))

    convidado_extra = db.Column(db.Boolean, default=False)

    qtd_extra = db.Column(db.Integer, default=0)

    valor_extra = db.Column(db.Float, default=0)

    # ==========================
    # PAGAMENTO
    # ==========================

    forma_pagamento = db.Column(db.String(50))

    desconto = db.Column(db.String(20))

    valor_total = db.Column(db.Float)

    valor_pago = db.Column(db.Float)

    valor_restante = db.Column(db.Float)

    # Guarda todos os sinais em JSON
    sinais = db.Column(db.Text)

    # ==========================
    # OBSERVAÇÕES
    # ==========================

    observacoes = db.Column(db.Text)

    # ==========================
    # STATUS
    # ==========================

    status = db.Column(
        db.String(30),
        default="Aberto"
    )

    criado_em = db.Column(
    db.DateTime,
    server_default=db.func.current_timestamp()
)

    dados_contrato = db.Column(db.Text)


def valor_numero(valor):
    try:
        if valor is None:
            return 0.0

        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor).strip()

        if not texto:
            return 0.0

        texto = (
            texto
            .replace("R$", "")
            .replace(" ", "")
        )

        # 1.234,56
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")

        return float(texto)

    except Exception:
        return 0.0


def formatar_moeda(valor):
    valor = valor_numero(valor)

    texto = f"{valor:,.2f}"

    texto = (
        texto
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"R$ {texto}"


def obter_salao_logado():
    """
    Descobre o salão através da sessão atual.
    Adapte somente esta função se sua sessão
    utilizar outro nome de variável.
    """

    salao_id = session.get("salao_id")

    if not salao_id:
        return None

    try:
        return Salao.query.get(int(salao_id))
    except Exception:
        return None


def dados_assistente_salao(salao_id):

    contratos = (
        Contrato.query
        .filter_by(salao_id=salao_id)
        .all()
    )

    dados_contratos = []

    faturamento = 0
    recebido = 0
    a_receber = 0

    for contrato in contratos:

        total = valor_numero(contrato.valor_total)
        pago = valor_numero(contrato.valor_pago)
        restante = valor_numero(contrato.valor_restante)

        if restante == 0 and total > pago:
            restante = total - pago

        faturamento += total
        recebido += pago
        a_receber += restante

        dados_contratos.append({
            "id": contrato.id,
            "cliente": contrato.cliente,
            "telefone": contrato.telefone,
            "aniversariante": contrato.aniversariante,
            "data_evento": contrato.data_evento,
            "hora_inicio": contrato.hora_inicio,
            "hora_fim": contrato.hora_fim,
            "convidados": contrato.convidados,
            "valor_total": total,
            "valor_pago": pago,
            "valor_restante": restante,
            "status": contrato.status
        })

    return {
        "salao": {
            "id": salao_id
        },

        "financeiro": {
            "faturamento": faturamento,
            "recebido": recebido,
            "a_receber": a_receber,
            "quantidade_contratos": len(contratos)
        },

        "contratos": dados_contratos
    }

@app.route("/api/assistente", methods=["POST"])
def api_assistente():

    try:

        # =====================================================
        # VERIFICA SALÃO LOGADO
        # =====================================================

        salao = obter_salao_logado()

        if not salao:

            return jsonify({
                "sucesso": False,
                "mensagem": "Sessão do salão não encontrada."
            }), 401

        # =====================================================
        # RECEBE PERGUNTA
        # =====================================================

        dados = request.get_json(silent=True) or {}

        pergunta_original = str(
            dados.get("mensagem", "")
        ).strip()

        if not pergunta_original:

            return jsonify({
                "sucesso": False,
                "mensagem": "Digite uma pergunta."
            }), 400

        # =====================================================
        # NORMALIZA PERGUNTA
        # =====================================================

        pergunta = pergunta_original.lower()

        pergunta = unicodedata.normalize(
            "NFD",
            pergunta
        )

        pergunta = "".join(
            c for c in pergunta
            if unicodedata.category(c) != "Mn"
        )

        pergunta = "".join(
            c if c.isalnum() or c.isspace() else " "
            for c in pergunta
        )

        pergunta = " ".join(
            pergunta.split()
        )

        # =====================================================
        # CARREGA DADOS DO SALÃO
        # =====================================================

        contexto = dados_assistente_salao(
            salao.id
        )

        contratos = contexto.get(
            "contratos",
            []
        )

        financeiro = contexto.get(
            "financeiro",
            {}
        )

        # =====================================================
        # FUNÇÕES AUXILIARES
        # =====================================================

        def moeda(valor):

            return formatar_moeda(
                valor_numero(valor)
            )

        # -----------------------------------------------------
        # OBTÉM VALORES CORRETOS DO CONTRATO
        # -----------------------------------------------------

        def valores_contrato(contrato):

            total = valor_numero(
                contrato.get("valor_total")
            )

            pago = valor_numero(
                contrato.get("valor_pago")
            )

            restante_banco = valor_numero(
                contrato.get("valor_restante")
            )

            # Calcula novamente o restante
            # para evitar inconsistências no banco.

            restante_calculado = total - pago

            if restante_calculado < 0:
                restante_calculado = 0

            # Se total e pago existem, o cálculo
            # mais seguro é sempre Total - Pago.

            if total > 0:

                restante = restante_calculado

            else:

                restante = restante_banco

            return (
                total,
                pago,
                restante
            )

        # -----------------------------------------------------
        # CONTRATO QUITADO
        # -----------------------------------------------------

        def contrato_quitado(contrato):

            total, pago, restante = valores_contrato(
                contrato
            )

            if total <= 0:
                return False

            return restante <= 0

        # -----------------------------------------------------
        # CONTRATO PARCIAL
        # -----------------------------------------------------

        def contrato_parcial(contrato):

            total, pago, restante = valores_contrato(
                contrato
            )

            return (
                total > 0
                and pago > 0
                and restante > 0
            )

        # -----------------------------------------------------
        # CONTRATO PENDENTE SEM PAGAMENTO
        # -----------------------------------------------------

        def contrato_pendente(contrato):

            total, pago, restante = valores_contrato(
                contrato
            )

            return (
                total > 0
                and pago <= 0
                and restante > 0
            )

        # -----------------------------------------------------
        # CONTRATO NÃO TOTALMENTE PAGO
        # -----------------------------------------------------

        def contrato_nao_totalmente_pago(contrato):

            total, pago, restante = valores_contrato(
                contrato
            )

            return (
                total > 0
                and restante > 0
            )

        # =====================================================
        # SAUDAÇÃO
        # =====================================================

        palavras_saudacao = [
            "oi",
            "ola",
            "bom dia",
            "boa tarde",
            "boa noite",
            "tudo bem"
        ]

        if pergunta in palavras_saudacao:

            return jsonify({
                "sucesso": True,
                "resposta": (
                    "Olá! 👋 Sou o assistente do "
                    "SalonConnect.\n\n"
                    "Posso consultar contratos, "
                    "pagamentos, agenda e financeiro "
                    "do seu salão."
                )
            })

        # =====================================================
        # QUANTIDADE DE CONTRATOS
        # =====================================================

        if (
            "quantos contratos" in pergunta
            or "quantidade de contratos" in pergunta
            or "numero de contratos" in pergunta
            or "quantos contrato" in pergunta
        ):

            quantidade = len(contratos)

            return jsonify({
                "sucesso": True,
                "resposta": (
                    f"📄 O salão possui "
                    f"**{quantidade} contrato(s)** "
                    f"cadastrado(s)."
                )
            })

        # =====================================================
        # CONTRATOS QUITADOS / PAGOS
        # =====================================================
        #
        # IMPORTANTE:
        # Esta verificação fica ANTES da busca pelo nome.
        #
        # Assim:
        #
        # "Quais contratos estão quitados?"
        #
        # será entendido como uma consulta geral,
        # e não como uma pesquisa de cliente.
        # =====================================================

        pergunta_quitados = (

            "contratos quitados" in pergunta

            or "contratos quitado" in pergunta

            or "contratos pagos" in pergunta

            or "contratos pago" in pergunta

            or "contratos ja pagos" in pergunta

            or "contratos ja pago" in pergunta

            or "contratos totalmente pagos" in pergunta

            or "contratos totalmente pago" in pergunta

            or "quais contratos estao quitados" in pergunta

            or "quais contratos estao quitado" in pergunta

            or "quais contratos estao pagos" in pergunta

            or "quais contratos estao pago" in pergunta

            or "quais contratos ja foram pagos" in pergunta

            or "quais contratos ja foram pagos" in pergunta

            or "quais contratos foram pagos" in pergunta

            or "quais contratos foram quitados" in pergunta

            or "quais contratos ja estao pagos" in pergunta

            or "quais contratos ja estao quitados" in pergunta

            or "festas quitadas" in pergunta

            or "festas quitado" in pergunta

            or "festas pagas" in pergunta

            or "festas pago" in pergunta

            or "pagamentos completos" in pergunta

            or "quais pagamentos estao completos" in pergunta

            or "quais festas estao pagas" in pergunta
        )

        if pergunta_quitados:

            quitados = [
                contrato
                for contrato in contratos
                if contrato_quitado(contrato)
            ]

            # -------------------------------------------------
            # NENHUM QUITADO
            # -------------------------------------------------

            if not quitados:

                return jsonify({
                    "sucesso": True,
                    "resposta": (
                        "ℹ️ Não encontrei nenhum contrato "
                        "totalmente pago no momento."
                    )
                })

            # -------------------------------------------------
            # LISTA QUITADOS
            # -------------------------------------------------

            resposta = (
                "✅ **Contratos quitados:**\n\n"
            )

            for contrato in quitados:

                nome = (
                    contrato.get("aniversariante")
                    or contrato.get("cliente")
                    or "Evento"
                )

                total, pago, restante = valores_contrato(
                    contrato
                )

                resposta += (
                    f"🎂 **{nome}**\n"
                    f"💰 Total: **{moeda(total)}**\n"
                    f"💳 Pago: **{moeda(pago)}**\n"
                    f"✅ Situação: **Quitado**\n\n"
                )

            return jsonify({
                "sucesso": True,
                "resposta": resposta
            })

        # =====================================================
        # CONTRATOS PENDENTES
        # =====================================================

        pergunta_pendentes = (

            "contratos pendentes" in pergunta

            or "contrato pendente" in pergunta

            or "festas pendentes" in pergunta

            or "festa pendente" in pergunta

            or "quem nao pagou" in pergunta

            or "quem ainda nao pagou" in pergunta

            or "quais contratos nao foram pagos" in pergunta

            or "quais contratos nao estao pagos" in pergunta

            or "quais contratos estao pendentes" in pergunta

            or "quais contratos ainda nao foram pagos" in pergunta

            or "contratos sem pagamento" in pergunta
        )

        if pergunta_pendentes:

            pendentes = [
                contrato
                for contrato in contratos
                if contrato_pendente(contrato)
            ]

            if not pendentes:

                return jsonify({
                    "sucesso": True,
                    "resposta": (
                        "🎉 Não encontrei contratos "
                        "com pagamento pendente."
                    )
                })

            resposta = (
                "⚠️ **Contratos com pagamento pendente:**\n\n"
            )

            for contrato in pendentes:

                nome = (
                    contrato.get("aniversariante")
                    or contrato.get("cliente")
                    or "Evento"
                )

                total, pago, restante = valores_contrato(
                    contrato
                )

                resposta += (
                    f"🎂 **{nome}**\n"
                    f"💰 Total: **{moeda(total)}**\n"
                    f"💳 Pago: **{moeda(pago)}**\n"
                    f"💵 Falta pagar: **{moeda(restante)}**\n"
                    f"🔴 Situação: **Pendente**\n\n"
                )

            return jsonify({
                "sucesso": True,
                "resposta": resposta
            })

        # =====================================================
        # EXISTE ALGUM CONTRATO NÃO TOTALMENTE PAGO?
        # =====================================================

        pergunta_nao_totalmente_pago = (

            "existe algum contrato que ainda nao foi totalmente pago"
            in pergunta

            or "existe algum contrato ainda nao totalmente pago"
            in pergunta

            or "algum contrato ainda nao foi totalmente pago"
            in pergunta

            or "algum contrato nao foi totalmente pago"
            in pergunta

            or "tem algum contrato que ainda nao foi totalmente pago"
            in pergunta

            or "tem algum contrato ainda nao totalmente pago"
            in pergunta

            or "existe contrato que ainda nao foi totalmente pago"
            in pergunta

            or "algum contrato ainda nao foi pago totalmente"
            in pergunta

            or "tem contrato que ainda nao foi pago totalmente"
            in pergunta

            or "algum contrato esta pendente"
            in pergunta

            or "algum contrato esta em aberto"
            in pergunta

            or "existe algum contrato pendente de pagamento"
            in pergunta

            or "existe contrato pendente de pagamento"
            in pergunta

            or "tem contrato pendente de pagamento"
            in pergunta
        )

        if pergunta_nao_totalmente_pago:

            nao_totalmente_pagos = [
                contrato
                for contrato in contratos
                if contrato_nao_totalmente_pago(contrato)
            ]

            if not nao_totalmente_pagos:

                return jsonify({
                    "sucesso": True,
                    "resposta": (
                        "✅ Não. Todos os contratos "
                        "estão totalmente pagos."
                    )
                })

            resposta = (
                "⚠️ **Sim. Existem contratos que ainda "
                "não foram totalmente pagos:**\n\n"
            )

            for contrato in nao_totalmente_pagos:

                nome = (
                    contrato.get("aniversariante")
                    or contrato.get("cliente")
                    or "Evento"
                )

                total, pago, restante = valores_contrato(
                    contrato
                )

                if pago > 0:

                    situacao = "🟡 Parcialmente pago"

                else:

                    situacao = "🔴 Ainda não pago"

                resposta += (
                    f"🎂 **{nome}**\n"
                    f"💰 Total: **{moeda(total)}**\n"
                    f"💳 Pago: **{moeda(pago)}**\n"
                    f"💵 Falta pagar: **{moeda(restante)}**\n"
                    f"Situação: **{situacao}**\n\n"
                )

            return jsonify({
                "sucesso": True,
                "resposta": resposta
            })

        # =====================================================
        # CONTRATOS PARCIALMENTE PAGOS
        # =====================================================

        if (
            "parcial" in pergunta
            or "parcialmente pago" in pergunta
            or "parcialmente pagos" in pergunta
            or "pagamento parcial" in pergunta
            or "pagamentos parciais" in pergunta
        ):

            parciais = [
                contrato
                for contrato in contratos
                if contrato_parcial(contrato)
            ]

            if not parciais:

                return jsonify({
                    "sucesso": True,
                    "resposta": (
                        "ℹ️ Não encontrei contratos "
                        "parcialmente pagos."
                    )
                })

            resposta = (
                "🟡 **Contratos parcialmente pagos:**\n\n"
            )

            for contrato in parciais:

                nome = (
                    contrato.get("aniversariante")
                    or contrato.get("cliente")
                    or "Evento"
                )

                total, pago, restante = valores_contrato(
                    contrato
                )

                resposta += (
                    f"🎂 **{nome}**\n"
                    f"💰 Total: **{moeda(total)}**\n"
                    f"💳 Pago: **{moeda(pago)}**\n"
                    f"💵 Restante: **{moeda(restante)}**\n\n"
                )

            return jsonify({
                "sucesso": True,
                "resposta": resposta
            })

        # =====================================================
        # MOSTRAR / LISTAR CONTRATOS
        # =====================================================

        frases_mostrar_contratos = [
            "me mostre os contratos",
            "me mostre os contrato",
            "mostre os contratos",
            "mostrar os contratos",
            "listar os contratos",
            "liste os contratos",
            "listar contratos",
            "liste contratos",
            "ver contratos",
            "ver os contratos",
            "mostrar contratos",
            "quais contratos temos",
            "quais contratos tem",
            "quais sao os contratos",
            "quais os contratos",
            "quais contratos existem",
            "quais sao os contratos que temos",
            "quais sao os contratos cadastrados",
            "quais contratos estao cadastrados",
            "me mostre os contratos cadastrados",
            "me mostre todos os contratos",
            "mostrar todos os contratos",
            "listar todos os contratos"
        ]

        if any(
            frase in pergunta
            for frase in frases_mostrar_contratos
        ):

            if not contratos:

                return jsonify({
                    "sucesso": True,
                    "resposta": (
                        "📄 Não encontrei nenhum contrato "
                        "cadastrado para este salão."
                    )
                })

            resposta = (
                f"📄 **Contratos cadastrados "
                f"({len(contratos)}):**\n\n"
            )

            for contrato in contratos:

                nome = (
                    contrato.get("aniversariante")
                    or contrato.get("cliente")
                    or "Evento"
                )

                data_evento = (
                    contrato.get("data_evento")
                    or "Data não informada"
                )

                hora_inicio = (
                    contrato.get("hora_inicio")
                    or "--"
                )

                hora_fim = (
                    contrato.get("hora_fim")
                    or "--"
                )

                total, pago, restante = valores_contrato(
                    contrato
                )

                if restante <= 0:

                    situacao = "✅ Quitado"

                elif pago > 0:

                    situacao = "🟡 Parcialmente pago"

                else:

                    situacao = "🔴 Pendente"

                resposta += (
                    f"🎂 **{nome}**\n"
                    f"📅 Data: **{data_evento}**\n"
                    f"🕐 Horário: **{hora_inicio} às {hora_fim}**\n"
                    f"💰 Total: **{moeda(total)}**\n"
                    f"💳 Pago: **{moeda(pago)}**\n"
                    f"💵 Restante: **{moeda(restante)}**\n"
                    f"Situação: **{situacao}**\n\n"
                )

            return jsonify({
                "sucesso": True,
                "resposta": resposta
            })

        # =====================================================
        # FATURAMENTO
        # =====================================================

        if (
            "quanto vendemos" in pergunta
            or "quanto faturamos" in pergunta
            or "faturamento" in pergunta
            or "vendas" in pergunta
        ):

            faturamento = valor_numero(
                financeiro.get("faturamento")
            )

            recebido = valor_numero(
                financeiro.get("recebido")
            )

            a_receber = valor_numero(
                financeiro.get("a_receber")
            )

            return jsonify({
                "sucesso": True,
                "resposta": (
                    "💰 **Resumo financeiro**\n\n"
                    f"Faturamento: **{moeda(faturamento)}**\n"
                    f"Recebido: **{moeda(recebido)}**\n"
                    f"A receber: **{moeda(a_receber)}**"
                )
            })

        # =====================================================
        # QUANTO TEMOS A RECEBER
        # =====================================================

        if (
            "quanto temos a receber" in pergunta
            or "quanto falta receber" in pergunta
            or "valor a receber" in pergunta
            or "a receber" in pergunta
        ):

            a_receber = valor_numero(
                financeiro.get("a_receber")
            )

            return jsonify({
                "sucesso": True,
                "resposta": (
                    "💳 **Valores a receber**\n\n"
                    f"Você ainda tem "
                    f"**{moeda(a_receber)}** "
                    f"a receber."
                )
            })

        # =====================================================
        # PROCURAR FESTA / CONTRATO PELO NOME
        # =====================================================

        encontrados = []

        for contrato in contratos:

            nome = str(
                contrato.get("aniversariante") or ""
            ).lower()

            cliente = str(
                contrato.get("cliente") or ""
            ).lower()

            if (
                nome
                and nome in pergunta
            ) or (
                cliente
                and cliente in pergunta
            ):

                encontrados.append(
                    contrato
                )

        # =====================================================
        # RESULTADO DO CONTRATO PESQUISADO
        # =====================================================

        if encontrados:

            if len(encontrados) > 1:

                resposta = (
                    "🔎 Encontrei mais de um contrato "
                    "relacionado à sua pesquisa:\n\n"
                )

                for contrato in encontrados:

                    nome = (
                        contrato.get("aniversariante")
                        or contrato.get("cliente")
                        or "Evento"
                    )

                    resposta += (
                        f"• **{nome}** — "
                        f"{contrato.get('data_evento') or 'Data não informada'}\n"
                    )

                return jsonify({
                    "sucesso": True,
                    "resposta": resposta
                })

            contrato = encontrados[0]

            nome = (
                contrato.get("aniversariante")
                or contrato.get("cliente")
                or "Evento"
            )

            total, pago, restante = valores_contrato(
                contrato
            )

            # =================================================
            # PERGUNTA ESPECÍFICA:
            # "A festa da Ana está paga?"
            # "O contrato da Ana está quitado?"
            # =================================================

            pergunta_sobre_pagamento = (

                "paga" in pergunta

                or "pago" in pergunta

                or "pagou" in pergunta

                or "quitada" in pergunta

                or "quitado" in pergunta

                or "quitou" in pergunta

                or "totalmente paga" in pergunta

                or "totalmente pago" in pergunta
            )

            if pergunta_sobre_pagamento:

                if restante <= 0:

                    situacao_pagamento = (
                        "✅ Sim! Este contrato está "
                        "totalmente pago."
                    )

                elif pago > 0:

                    situacao_pagamento = (
                        "🟡 Não totalmente. Este contrato "
                        "está parcialmente pago."
                    )

                else:

                    situacao_pagamento = (
                        "🔴 Não. Este contrato ainda "
                        "não possui pagamento."
                    )

                resposta = (
                    f"🎂 **{nome}**\n\n"
                    f"💰 Total: **{moeda(total)}**\n"
                    f"💳 Pago: **{moeda(pago)}**\n"
                    f"💵 Restante: **{moeda(restante)}**\n\n"
                    f"{situacao_pagamento}"
                )

                return jsonify({
                    "sucesso": True,
                    "resposta": resposta
                })

            # =================================================
            # CONSULTA NORMAL DO CONTRATO
            # =================================================

            if restante <= 0:

                situacao = "✅ Quitado"

            elif pago > 0:

                situacao = "🟡 Parcialmente pago"

            else:

                situacao = "🔴 Pendente"

            resposta = (
                f"🎂 **{nome}**\n\n"
                f"📅 Data: "
                f"{contrato.get('data_evento') or 'Não informada'}\n"
                f"🕐 Horário: "
                f"{contrato.get('hora_inicio') or '--'}"
                f" às "
                f"{contrato.get('hora_fim') or '--'}\n\n"
                f"💰 Total: **{moeda(total)}**\n"
                f"💳 Pago: **{moeda(pago)}**\n"
                f"💵 Restante: **{moeda(restante)}**\n\n"
                f"Situação: **{situacao}**"
            )

            return jsonify({
                "sucesso": True,
                "resposta": resposta
            })

        # =====================================================
        # AGENDA
        # =====================================================

        if (
            "agenda" in pergunta
            or "eventos" in pergunta
            or "festas" in pergunta
            or "proximas festas" in pergunta
        ):

            contratos_ordenados = sorted(
                contratos,
                key=lambda c: str(
                    c.get("data_evento") or ""
                )
            )

            if not contratos_ordenados:

                return jsonify({
                    "sucesso": True,
                    "resposta": (
                        "📅 Não encontrei eventos "
                        "cadastrados."
                    )
                })

            resposta = (
                "📅 **Agenda de eventos:**\n\n"
            )

            for contrato in contratos_ordenados[:10]:

                nome = (
                    contrato.get("aniversariante")
                    or contrato.get("cliente")
                    or "Evento"
                )

                resposta += (
                    f"• **{nome}**\n"
                    f"📅 {contrato.get('data_evento') or '--'}\n"
                    f"🕐 {contrato.get('hora_inicio') or '--'}"
                    f" às "
                    f"{contrato.get('hora_fim') or '--'}\n\n"
                )

            return jsonify({
                "sucesso": True,
                "resposta": resposta
            })

        # =====================================================
        # NÃO ENTENDEU
        # =====================================================

        return jsonify({
            "sucesso": True,
            "resposta": (
                "🤔 Ainda não consegui identificar "
                "essa solicitação.\n\n"
                "Você pode perguntar, por exemplo:\n\n"
                "💰 Quanto vendemos este mês?\n"
                "💳 Quanto temos a receber?\n"
                "🎂 A festa da Ana está paga?\n"
                "📄 Quantos contratos temos?\n"
                "📄 Me mostre os contratos.\n"
                "📄 Quais contratos temos?\n"
                "⚠️ Existe algum contrato que ainda "
                "não foi totalmente pago?\n"
                "✅ Quais contratos estão quitados?\n"
                "⚠️ Quais contratos estão pendentes?\n"
                "🟡 Quais contratos estão parcialmente pagos?"
            )
        })

    except Exception as e:

        import traceback

        print("\n====================================")
        print("ERRO NO ASSISTENTE LOCAL")
        print("====================================")

        print(type(e).__name__)
        print(str(e))

        traceback.print_exc()

        print("====================================\n")

        return jsonify({
            "sucesso": False,
            "mensagem": (
                "Não foi possível processar "
                "sua pergunta."
            )
        }), 500
# ===========================
# ROTAS
# ===========================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/salvar_contrato", methods=["POST"])
def salvar_contrato():

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    dados = request.get_json()

    if not dados:
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhum dado foi recebido."
        }), 400

    # ==========================================================
    # CONVERSÃO DE VALORES
    # Aceita:
    # 1234.56
    # "1234.56"
    # "1.234,56"
    # "R$ 1.234,56"
    # ==========================================================

    def converter_valor(valor):

        if valor is None or valor == "":
            return 0.0

        if isinstance(valor, (int, float)):
            return float(valor)

        valor = str(valor).strip()

        if not valor:
            return 0.0

        valor = valor.replace("R$", "")
        valor = valor.replace(" ", "")

        if "," in valor:
            valor = valor.replace(".", "")
            valor = valor.replace(",", ".")

        try:
            return float(valor)
        except (ValueError, TypeError):
            return 0.0

    # ==========================================================
    # ID DO CONTRATO
    # ==========================================================

    contrato_id = dados.get("id")

    # ==========================================================
    # EDITAR CONTRATO EXISTENTE
    # OU CRIAR NOVO
    # ==========================================================

    if contrato_id:

        try:
            contrato_id = int(contrato_id)
        except (ValueError, TypeError):

            return jsonify({
                "sucesso": False,
                "mensagem": "ID do contrato inválido."
            }), 400

        contrato = Contrato.query.filter_by(
            id=contrato_id,
            salao_id=session["salao_id"]
        ).first()

        if not contrato:

            return jsonify({
                "sucesso": False,
                "mensagem": "Contrato não encontrado."
            }), 404

    else:

        contrato = Contrato(
            salao_id=session["salao_id"]
        )

        db.session.add(contrato)

    # ==========================================================
    # DADOS DO CONTRATANTE
    # ==========================================================

    contrato.cliente = dados.get("cliente", "")
    contrato.aniversariante = dados.get("aniversariante", "")
    contrato.telefone = dados.get("telefone", "")
    contrato.email = dados.get("email", "")
    contrato.cpf = dados.get("cpf", "")

    contrato.responsavel1 = dados.get("responsavel1", "")
    contrato.responsavel2 = dados.get("responsavel2", "")

    # ==========================================================
    # DATA E HORÁRIO
    # ==========================================================

    contrato.data_evento = dados.get("dataEvento", "")
    contrato.data_aniversario = dados.get("dataAniversario", "")

    contrato.hora_inicio = dados.get("horaInicio", "")
    contrato.hora_fim = dados.get("horaFim", "")

    # ==========================================================
    # EVENTO
    # ==========================================================

    try:
        contrato.convidados = int(
            dados.get("convidados") or 0
        )
    except (ValueError, TypeError):
        contrato.convidados = 0

    contrato.pacote = dados.get("pacote", "")

    contrato.convidado_extra = bool(
        dados.get("convidadoExtra", False)
    )

    try:
        contrato.qtd_extra = int(
            dados.get("qtdConvidadosExtras") or 0
        )
    except (ValueError, TypeError):
        contrato.qtd_extra = 0

    contrato.valor_extra = converter_valor(
        dados.get("valorExtra")
    )

    # ==========================================================
    # PAGAMENTO
    # ==========================================================

    contrato.forma_pagamento = dados.get(
        "formaPagamento",
        ""
    )

    contrato.desconto = dados.get(
        "desconto",
        ""
    )

    contrato.valor_total = converter_valor(
        dados.get("valorTotal")
    )

    contrato.valor_pago = converter_valor(
        dados.get("valorPago")
    )

    contrato.valor_restante = converter_valor(
        dados.get("valorRestante")
    )

    # ==========================================================
    # OBSERVAÇÕES
    # ==========================================================

    contrato.observacoes = dados.get(
        "observacoes",
        ""
    )

    # ==========================================================
    # SINAIS
    # ==========================================================

    sinais = dados.get("sinais", [])

    if not isinstance(sinais, list):
        sinais = []

    contrato.sinais = json.dumps(
        sinais,
        ensure_ascii=False
    )

    # ==========================================================
    # GUARDA TODOS OS DADOS DO CONTRATO EM JSON
    # ==========================================================

    contrato.dados_contrato = json.dumps(
        dados,
        ensure_ascii=False
    )

    # ==========================================================
    # STATUS
    # ==========================================================

    contrato.status = "Finalizado"

    # ==========================================================
    # SALVAR NO BANCO
    # ==========================================================

    try:

        db.session.commit()

    except Exception as erro:

        db.session.rollback()

        print(
            "ERRO AO SALVAR CONTRATO:",
            erro
        )

        return jsonify({
            "sucesso": False,
            "mensagem": "Erro ao salvar contrato no banco de dados."
        }), 500

    # ==========================================================
    # RESPOSTA
    # ==========================================================

    return jsonify({
        "sucesso": True,
        "mensagem": "Contrato salvo com sucesso!",
        "id": contrato.id,
        "valorTotal": contrato.valor_total,
        "valorPago": contrato.valor_pago,
        "valorRestante": contrato.valor_restante
    })
# ===========================
# LOGIN
# ===========================

@app.route("/login", methods=["POST"])
def login():

    dados = request.get_json()

    email = dados.get("email")
    senha = dados.get("senha")

    # ADMIN
    usuario = Usuario.query.filter_by(email=email).first()

    if usuario and check_password_hash(usuario.senha, senha):

        session["tipo"] = "admin"
        session["usuario"] = usuario.nome

        return jsonify({
            "sucesso": True,
            "redirect": "/admin",
            "nome": usuario.nome
        })

    # SALÃO
    salao = Salao.query.filter_by(email=email).first()

    if salao and check_password_hash(salao.senha, senha):

        session["tipo"] = "salao"
        session["salao_id"] = salao.id
        session["nome"] = salao.nome

        return jsonify({
            "sucesso": True,
            "redirect": "/pagina_inicial",
            "nome": salao.nome
        })

    return jsonify({
        "sucesso": False,
        "mensagem": "Email ou senha inválidos."
    })

# ===========================
# SALVAR ORÇAMENTO
# ===========================

@app.route("/orcamento", methods=["POST"])
def salvar_orcamento():

    dados = request.get_json()

    novo = Orcamento(

        gestao=dados["gestao"],
        nome=dados["nome"],
        email=dados["email"],
        whatsapp=dados["whatsapp"],
        salao=dados["salao"],
        tamanho=dados["tamanho"],
        funcionarios=int(dados["funcionarios"]) if dados["funcionarios"] else None,
        origem=dados["origem"],
        plano=dados["plano"]

    )

    db.session.add(novo)
    db.session.commit()

    return jsonify({
        "mensagem": "Orçamento enviado com sucesso!"
    })


# ===========================
# LISTAR ORÇAMENTOS
# ===========================

@app.route("/orcamentos")
def listar_orcamentos():

    lista = Orcamento.query.order_by(Orcamento.id.desc()).all()

    return render_template(
        "orcamentos.html",
        lista=lista
    )

@app.route("/excluir_orcamento/<int:id>")
def excluir_orcamento(id):

    orcamento = Orcamento.query.get_or_404(id)

    db.session.delete(orcamento)

    db.session.commit()

    return redirect("/orcamentos")

@app.route("/salvar_configuracao", methods=["POST"])
def salvar_configuracao():

    if "salao_id" not in session:
        return jsonify({"erro": "Usuário não autenticado"}), 401

    dados = request.get_json()

    configuracao = ConfiguracaoContrato.query.filter_by(
        salao_id=session["salao_id"]
    ).first()

    if not configuracao:
        configuracao = ConfiguracaoContrato(
            salao_id=session["salao_id"]
        )
        db.session.add(configuracao)

    configuracao.servicos = dados.get("servicos")
    configuracao.buffet = json.dumps(dados.get("buffet", []))
    configuracao.doces = json.dumps(dados.get("doces", []))
    configuracao.adicionais = json.dumps(dados.get("adicionais", []))
    configuracao.pacotes = json.dumps(dados.get("pacotes", []))
    configuracao.valor_extra = dados.get("valorExtra", 0)

    db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Configuração salva com sucesso!"
    })

@app.route("/configuracao")
def obter_configuracao():

    if "salao_id" not in session:
        return jsonify({"erro": "Usuário não autenticado"}), 401

    configuracao = ConfiguracaoContrato.query.filter_by(
        salao_id=session["salao_id"]
    ).first()

    if not configuracao:
        return jsonify({
            "servicos": "",
            "buffet": [],
            "doces": [],
            "adicionais": [],
            "pacotes": [],
            "valorExtra": 0
        })

    return jsonify({
        "servicos": configuracao.servicos or "",
        "buffet": json.loads(configuracao.buffet or "[]"),
        "doces": json.loads(configuracao.doces or "[]"),
        "adicionais": json.loads(configuracao.adicionais or "[]"),
        "pacotes": json.loads(configuracao.pacotes or "[]"),
        "valorExtra": configuracao.valor_extra or 0
    })
@app.route("/contrato_json/<int:id>")
def contrato_json(id):

    if "salao_id" not in session:
        return jsonify({
            "erro": "Usuário não autenticado"
        }), 401

    contrato = Contrato.query.filter_by(
        id=id,
        salao_id=session["salao_id"]
    ).first_or_404()

    dados_salvos = {}

    if contrato.dados_contrato:

        try:
            dados_salvos = json.loads(
                contrato.dados_contrato
            )

        except Exception:
            dados_salvos = {}

    resposta = dict(dados_salvos)

    # ==============================
    # DADOS PRINCIPAIS
    # ==============================

    resposta["id"] = contrato.id

    resposta["cliente"] = contrato.cliente or ""
    resposta["aniversariante"] = contrato.aniversariante or ""
    resposta["telefone"] = contrato.telefone or ""
    resposta["email"] = contrato.email or ""
    resposta["cpf"] = contrato.cpf or ""

    resposta["responsavel1"] = contrato.responsavel1 or ""
    resposta["responsavel2"] = contrato.responsavel2 or ""

    resposta["dataEvento"] = contrato.data_evento or ""
    resposta["dataAniversario"] = contrato.data_aniversario or ""

    resposta["horaInicio"] = contrato.hora_inicio or ""
    resposta["horaFim"] = contrato.hora_fim or ""

    # ==============================
    # EVENTO
    # ==============================

    resposta["convidados"] = contrato.convidados or 0

    resposta["pacote"] = contrato.pacote or ""

    resposta["convidadoExtra"] = bool(
        contrato.convidado_extra
    )

    resposta["qtdConvidadosExtras"] = (
        contrato.qtd_extra or 0
    )

    resposta["valorExtra"] = (
        contrato.valor_extra or 0
    )

    # ==============================
    # PAGAMENTO
    # ==============================

    resposta["formaPagamento"] = (
        contrato.forma_pagamento or ""
    )

    resposta["desconto"] = (
        contrato.desconto or ""
    )

    resposta["valorTotal"] = (
        contrato.valor_total or 0
    )

    resposta["valorPago"] = (
        contrato.valor_pago or 0
    )

    resposta["valorRestante"] = (
        contrato.valor_restante or 0
    )

    # ==============================
    # OBSERVAÇÕES
    # ==============================

    resposta["observacoes"] = (
        contrato.observacoes or ""
    )

    # ==============================
    # SINAIS
    # ==============================

    if contrato.sinais:

        try:
            resposta["sinais"] = json.loads(
                contrato.sinais
            )

        except Exception:
            resposta["sinais"] = []

    else:

        resposta["sinais"] = []

    # ==============================
    # ITENS SELECIONADOS
    # ==============================

    resposta["servicosSelecionados"] = (
        dados_salvos.get(
            "servicosSelecionados",
            []
        )
    )

    resposta["buffetSelecionado"] = (
        dados_salvos.get(
            "buffetSelecionado",
            []
        )
    )

    resposta["docesSelecionados"] = (
        dados_salvos.get(
            "docesSelecionados",
            []
        )
    )

    resposta["adicionaisSelecionados"] = (
        dados_salvos.get(
            "adicionaisSelecionados",
            []
        )
    )

    # ==============================
    # CONFIGURAÇÃO ATUAL
    # ==============================

    configuracao = ConfiguracaoContrato.query.filter_by(
        salao_id=session["salao_id"]
    ).first()

    if configuracao:

        resposta["servicos"] = (
            configuracao.servicos or ""
        )

        resposta["buffet"] = json.loads(
            configuracao.buffet or "[]"
        )

        resposta["doces"] = json.loads(
            configuracao.doces or "[]"
        )

        resposta["adicionais"] = json.loads(
            configuracao.adicionais or "[]"
        )

        resposta["pacotes"] = json.loads(
            configuracao.pacotes or "[]"
        )

        resposta["valorExtraConfiguracao"] = (
            configuracao.valor_extra or 0
        )

    return jsonify(resposta)
@app.route("/contrato")
def contrato():

    if "salao_id" not in session:
        return redirect("/")

    return render_template(
        "contrato.html"
    )
@app.route("/novo_contrato")
def novo_contrato():

    if "salao_id" not in session:
        return redirect("/login")

    contrato_id = request.args.get("id", type=int)
    modo = request.args.get("modo", "editar")

    contrato = None

    if contrato_id:

        contrato = Contrato.query.filter_by(
            id=contrato_id,
            salao_id=session["salao_id"]
        ).first()

        if not contrato:
            return redirect("/contratos")

    return render_template(
        "novo_contrato.html",
        contrato=contrato,
        modo=modo
    )
@app.route("/logout")
def logout():

    session.clear()

    resposta = redirect("/")

    # Remove o cookie/localStorage não pode ser removido pelo Flask,
    # mas a página index vai executar a limpeza abaixo.

    return resposta
@app.route("/novo_salao")
def novo_salao():
    return render_template("novo_salao.html")
@app.route("/gerar_pdf_contrato/<int:id>")
def gerar_pdf_contrato(id):

    if "salao_id" not in session:
        return jsonify({
            "erro": "Usuário não autenticado."
        }), 401

    contrato = Contrato.query.filter_by(
        id=id,
        salao_id=session["salao_id"]
    ).first()

    if not contrato:
        return jsonify({
            "erro": "Contrato não encontrado."
        }), 404

    # Recupera todos os dados salvos no JSON
    try:
        dados = json.loads(
            contrato.dados_contrato or "{}"
        )
    except Exception:
        dados = {}

    # Dados principais
    dados["id"] = contrato.id
    dados["cliente"] = contrato.cliente or ""
    dados["aniversariante"] = contrato.aniversariante or ""
    dados["telefone"] = contrato.telefone or ""
    dados["email"] = contrato.email or ""
    dados["cpf"] = contrato.cpf or ""

    dados["responsavel1"] = contrato.responsavel1 or ""
    dados["responsavel2"] = contrato.responsavel2 or ""

    # Evento
    dados["dataEvento"] = contrato.data_evento or ""
    dados["dataAniversario"] = contrato.data_aniversario or ""
    dados["horaInicio"] = contrato.hora_inicio or ""
    dados["horaFim"] = contrato.hora_fim or ""

    dados["convidados"] = contrato.convidados or 0
    dados["pacote"] = contrato.pacote or ""

    dados["convidadoExtra"] = bool(
        contrato.convidado_extra
    )

    dados["qtdConvidadosExtras"] = (
        contrato.qtd_extra or 0
    )

    dados["valorExtra"] = (
        contrato.valor_extra or 0
    )

    # Pagamento
    dados["formaPagamento"] = (
        contrato.forma_pagamento or ""
    )

    dados["desconto"] = (
        contrato.desconto or ""
    )

    dados["valorTotal"] = (
        contrato.valor_total or 0
    )

    dados["valorPago"] = (
        contrato.valor_pago or 0
    )

    dados["valorRestante"] = (
        contrato.valor_restante or 0
    )

    # Observações
    dados["observacoes"] = (
        contrato.observacoes or ""
    )

    # Sinais
    if contrato.sinais:
        try:
            dados["sinais"] = json.loads(
                contrato.sinais
            )
        except Exception:
            dados["sinais"] = []
    else:
        dados["sinais"] = []

    # ==========================
    # FUNÇÕES AUXILIARES
    # ==========================

    def texto(valor):
        if valor is None or valor == "":
            return "-"

        return str(valor)

    def moeda(valor):
        try:
            valor = float(valor or 0)
        except (ValueError, TypeError):
            valor = 0

        return (
            f"R$ {valor:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def safe(valor):
        return (
            texto(valor)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    # ==========================
    # CRIA PDF
    # ==========================

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloContrato",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=10
    )

    normal = ParagraphStyle(
        "NormalContrato",
        parent=styles["Normal"],
        fontSize=9,
        leading=13
    )

    secao = ParagraphStyle(
        "SecaoContrato",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=10,
        spaceAfter=6
    )

    pequeno = ParagraphStyle(
        "PequenoContrato",
        parent=normal,
        fontSize=8,
        leading=11
    )

    story = []

    # ==========================
    # CABEÇALHO
    # ==========================

    salao = Salao.query.get(
        session["salao_id"]
    )

    nome_salao = (
        salao.nome
        if salao
        else "SalonConnect"
    )

    story.append(
        Paragraph(
            safe(nome_salao),
            titulo
        )
    )

    story.append(
        Paragraph(
            f"<b>CONTRATO Nº {contrato.id}</b>",
            normal
        )
    )

    story.append(
        Spacer(1, 8)
    )

    # ==========================
    # DADOS DO CONTRATANTE
    # ==========================

    story.append(
        Paragraph(
            "1. Dados do contratante",
            secao
        )
    )

    dados_cliente = [
        ["Cliente", dados["cliente"]],
        ["Aniversariante", dados["aniversariante"]],
        ["Telefone", dados["telefone"]],
        ["E-mail", dados["email"]],
        ["CPF", dados["cpf"]],
        ["Responsável 1", dados["responsavel1"]],
        ["Responsável 2", dados["responsavel2"]]
    ]

    tabela = Table(
        [
            [
                Paragraph(
                    f"<b>{safe(rotulo)}</b>",
                    pequeno
                ),
                Paragraph(
                    safe(valor),
                    pequeno
                )
            ]
            for rotulo, valor in dados_cliente
        ],
        colWidths=[
            45 * mm,
            135 * mm
        ]
    )

    tabela.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
        ])
    )

    story.append(tabela)

    # ==========================
    # DADOS DO EVENTO
    # ==========================

    story.append(
        Paragraph(
            "2. Dados do evento",
            secao
        )
    )

    evento = [
        ["Data do evento", dados["dataEvento"]],
        ["Data de aniversário", dados["dataAniversario"]],
        [
            "Horário",
            f'{texto(dados["horaInicio"])} às '
            f'{texto(dados["horaFim"])}'
        ],
        ["Convidados", dados["convidados"]],
        ["Pacote", dados["pacote"]],
        [
            "Convidados extras",
            "Sim" if dados["convidadoExtra"]
            else "Não"
        ],
        [
            "Quantidade extra",
            dados["qtdConvidadosExtras"]
        ],
        [
            "Valor por extra",
            moeda(dados["valorExtra"])
        ]
    ]

    tabela_evento = Table(
        [
            [
                Paragraph(
                    f"<b>{safe(rotulo)}</b>",
                    pequeno
                ),
                Paragraph(
                    safe(valor),
                    pequeno
                )
            ]
            for rotulo, valor in evento
        ],
        colWidths=[
            45 * mm,
            135 * mm
        ]
    )

    tabela_evento.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
        ])
    )

    story.append(tabela_evento)

    # ==========================
    # ITENS SELECIONADOS
    # ==========================

    story.append(
        Paragraph(
            "3. Itens selecionados",
            secao
        )
    )

    servicos = dados.get(
        "servicosSelecionados",
        []
    ) or []

    story.append(
        Paragraph(
            "<b>Serviços</b>",
            normal
        )
    )

    if servicos:

        for item in servicos:

            if isinstance(item, dict):
                nome = item.get("nome", "")
            else:
                nome = item

            story.append(
                Paragraph(
                    f"• {safe(nome)}",
                    normal
                )
            )

    else:

        story.append(
            Paragraph(
                "Nenhum serviço selecionado.",
                normal
            )
        )

    # Buffet
    buffet = dados.get(
        "buffetSelecionado",
        []
    ) or []

    story.append(
        Paragraph(
            "<b>Buffet</b>",
            normal
        )
    )

    if buffet:

        for item in buffet:

            if isinstance(item, dict):

                categoria = item.get(
                    "categoria",
                    ""
                )

                nome = item.get(
                    "nome",
                    ""
                )

                texto_item = (
                    f"{categoria} — {nome}"
                )

            else:

                texto_item = item

            story.append(
                Paragraph(
                    f"• {safe(texto_item)}",
                    normal
                )
            )

    else:

        story.append(
            Paragraph(
                "Nenhum buffet selecionado.",
                normal
            )
        )

    # Doces
    doces = dados.get(
        "docesSelecionados",
        []
    ) or []

    story.append(
        Paragraph(
            "<b>Doces</b>",
            normal
        )
    )

    if doces:

        for item in doces:

            if isinstance(item, dict):

                categoria = item.get(
                    "categoria",
                    ""
                )

                nome = item.get(
                    "nome",
                    ""
                )

                texto_item = (
                    f"{categoria} — {nome}"
                )

            else:

                texto_item = item

            story.append(
                Paragraph(
                    f"• {safe(texto_item)}",
                    normal
                )
            )

    else:

        story.append(
            Paragraph(
                "Nenhum doce selecionado.",
                normal
            )
        )

    # Adicionais
    adicionais = dados.get(
        "adicionaisSelecionados",
        []
    ) or []

    story.append(
        Paragraph(
            "<b>Adicionais</b>",
            normal
        )
    )

    if adicionais:

        for item in adicionais:

            if isinstance(item, dict):

                categoria = item.get(
                    "categoria",
                    ""
                )

                nome = item.get(
                    "nome",
                    ""
                )

                valor = moeda(
                    item.get("valor", 0)
                )

                texto_item = (
                    f"{categoria} — "
                    f"{nome} ({valor})"
                )

            else:

                texto_item = item

            story.append(
                Paragraph(
                    f"• {safe(texto_item)}",
                    normal
                )
            )

    else:

        story.append(
            Paragraph(
                "Nenhum adicional selecionado.",
                normal
            )
        )

    # ==========================
    # PAGAMENTO
    # ==========================

    story.append(
        Paragraph(
            "4. Pagamento",
            secao
        )
    )

    pagamento = [
        [
            "Forma de pagamento",
            dados["formaPagamento"]
        ],
        [
            "Desconto",
            dados["desconto"]
        ],
        [
            "Valor total",
            moeda(dados["valorTotal"])
        ],
        [
            "Valor pago",
            moeda(dados["valorPago"])
        ],
        [
            "Valor restante",
            moeda(dados["valorRestante"])
        ]
    ]

    tabela_pagamento = Table(
        [
            [
                Paragraph(
                    f"<b>{safe(rotulo)}</b>",
                    pequeno
                ),
                Paragraph(
                    safe(valor),
                    pequeno
                )
            ]
            for rotulo, valor in pagamento
        ],
        colWidths=[
            45 * mm,
            135 * mm
        ]
    )

    tabela_pagamento.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
        ])
    )

    story.append(
        tabela_pagamento
    )

    # ==========================
    # SINAIS
    # ==========================

    story.append(
        Paragraph(
            "5. Sinais / pagamentos",
            secao
        )
    )

    sinais = dados.get(
        "sinais",
        []
    ) or []

    if sinais:

        linhas = [
            ["Valor", "Data", "Forma"]
        ]

        for sinal in sinais:

            if isinstance(sinal, dict):

                linhas.append([
                    moeda(
                        sinal.get(
                            "valor",
                            0
                        )
                    ),
                    sinal.get(
                        "data",
                        "-"
                    ),
                    sinal.get(
                        "forma",
                        "-"
                    )
                ])

        tabela_sinais = Table(
            linhas,
            colWidths=[
                50 * mm,
                60 * mm,
                70 * mm
            ]
        )

        tabela_sinais.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
            ])
        )

        story.append(
            tabela_sinais
        )

    else:

        story.append(
            Paragraph(
                "Nenhum sinal registrado.",
                normal
            )
        )

    # ==========================
    # OBSERVAÇÕES
    # ==========================

    story.append(
        Paragraph(
            "6. Observações",
            secao
        )
    )

    observacoes = safe(
        dados.get(
            "observacoes",
            ""
        )
    )

    story.append(
        Paragraph(
            observacoes.replace(
                "\n",
                "<br/>"
            ),
            normal
        )
    )

    # ==========================================================
    # CLÁUSULAS CONTRATUAIS
    # ==========================================================

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "CLÁUSULA 1ª — DO OBJETO DA CONTRATAÇÃO",
            secao
        )
    )

    story.append(
        Paragraph(
            "O CONTRATANTE reserva o espaço para realização de evento "
            "no salão de festas, na data e horário previamente acordados, "
            "incluindo a utilização das áreas e serviços especificados "
            "no orçamento e no resumo da contratação. A utilização do "
            "espaço deverá respeitar as condições estabelecidas pelo "
            "CONTRATADO.",
            normal
        )
    )

    story.append(Spacer(1, 6))

    story.append(
        Paragraph(
            "CLÁUSULA 2ª — DO PAGAMENTO",
            secao
        )
    )

    story.append(
        Paragraph(
            "O valor total da contratação será aquele informado no "
            "orçamento e aceito pelo CONTRATANTE. O pagamento poderá "
            "ser realizado conforme as condições previamente acordadas "
            "entre as partes, sendo que eventuais valores adicionais "
            "decorrentes da inclusão de serviços, convidados ou produtos "
            "deverão ser pagos pelo CONTRATANTE conforme negociação "
            "realizada.",
            normal
        )
    )

    story.append(Spacer(1, 6))

    story.append(
        Paragraph(
            "CLÁUSULA 3ª — DA DATA E DO HORÁRIO DO EVENTO",
            secao
        )
    )

    story.append(
        Paragraph(
            "O evento ocorrerá na data e nos horários registrados neste "
            "contrato. O CONTRATANTE deverá respeitar os horários de "
            "início e término estabelecidos, ficando sujeito à cobrança "
            "de valor adicional caso permaneça no espaço após o horário "
            "contratado, desde que previamente previsto ou autorizado "
            "pelo CONTRATADO.",
            normal
        )
    )

    story.append(Spacer(1, 6))

    story.append(
        Paragraph(
            "CLÁUSULA 4ª — DA RESPONSABILIDADE PELA CONSERVAÇÃO DO ESPAÇO",
            secao
        )
    )

    story.append(
        Paragraph(
            "O CONTRATANTE compromete-se a utilizar o espaço, móveis, "
            "equipamentos, utensílios e demais itens disponibilizados "
            "pelo CONTRATADO de forma adequada. Eventuais danos "
            "causados durante o evento por convidados ou prestadores "
            "contratados pelo CONTRATANTE poderão ser cobrados, "
            "mediante apuração e comprovação dos prejuízos.",
            normal
        )
    )

    story.append(Spacer(1, 6))

    story.append(
        Paragraph(
            "CLÁUSULA 5ª — DO CANCELAMENTO E DA ALTERAÇÃO DO EVENTO",
            secao
        )
    )

    story.append(
        Paragraph(
            "Qualquer solicitação de cancelamento, alteração de data, "
            "horário, quantidade de convidados ou serviços contratados "
            "deverá ser comunicada ao CONTRATADO com antecedência. "
            "Eventuais valores, taxas ou condições decorrentes do "
            "cancelamento ou alteração serão aplicados conforme as "
            "condições previamente estabelecidas entre as partes e "
            "registradas no contrato.",
            normal
        )
    )

    story.append(Spacer(1, 6))

    story.append(
        Paragraph(
            "<b>Parágrafo único:</b> A confirmação da contratação "
            "representa a concordância do CONTRATANTE com as condições "
            "comerciais e operacionais apresentadas pelo CONTRATADO.",
            normal
        )
    )
    # ==========================================================
    # IDENTIFICAÇÃO FINAL DO CONTRATO
    # ==========================================================

    story.append(Spacer(1, 18))

    # Número e data do contrato
    data_contrato = datetime.now().strftime("%d/%m/%Y")

    identificacao = Table(
        [
            [
                Paragraph(
                    f"<b>NÚMERO DO CONTRATO</b><br/>"
                    f"{contrato.id:06d}",
                    normal
                ),
                Paragraph(
                    f"<b>DATA DE EMISSÃO</b><br/>"
                    f"{data_contrato}",
                    normal
                )
            ]
        ],
        colWidths=[
            90 * mm,
            80 * mm
        ]
    )

    identificacao.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),

            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),

            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6)
        ])
    )

    story.append(identificacao)

    # ==========================================================
    # LOCAL E DATA
    # ==========================================================

    story.append(Spacer(1, 16))

    cidade_salao = (
        salao.cidade
        if salao and salao.cidade
        else ""
    )

    # ==========================================================
    # ASSINATURAS
    # ==========================================================

    story.append(Spacer(1, 28))

    story.append(
        Paragraph(
            "ASSINATURAS",
            secao
        )
    )

    responsavel_salao = (
        salao.responsavel
        if salao and salao.responsavel
        else "Responsável pelo salão"
    )

    nome_cliente = (
        dados.get("cliente")
        or "Contratante"
    )

    cpf_cliente = (
        dados.get("cpf")
        or ""
    )

    # Linha para CPF
    cpf_texto = (
        f"CPF: {safe(cpf_cliente)}"
        if cpf_cliente
        else "CPF: __________________________________"
    )

    assinaturas = Table(
        [
            [
                Paragraph(
                    "<b>CONTRATANTE</b>",
                    normal
                ),
                Paragraph(
                    "<b>CONTRATADO</b>",
                    normal
                )
            ],
            [
                Spacer(1, 30),
                Spacer(1, 30)
            ],
            [
                Paragraph(
                    "________________________________________",
                    pequeno
                ),
                Paragraph(
                    "________________________________________",
                    pequeno
                )
            ],
            [
                Paragraph(
                    safe(nome_cliente),
                    pequeno
                ),
                Paragraph(
                    safe(responsavel_salao),
                    pequeno
                )
            ],
            [
                Paragraph(
                    cpf_texto,
                    pequeno
                ),
                Paragraph(
                    "Gerente / Responsável pelo salão",
                    pequeno
                )
            ]
        ],
        colWidths=[
            85 * mm,
            85 * mm
        ]
    )

    assinaturas.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID", (0, 0), (-1, 0), 0.5, colors.grey),

            ("TOPPADDING", (0, 0), (-1, 0), 7),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 7),

            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),

            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6)
        ])
    )

    story.append(assinaturas)

    # ==========================================================
    # FINALIZA PDF
    # ==========================================================

    doc.build(story)

    buffer.seek(0)

    nome_cliente = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        str(
            dados.get(
                "cliente",
                "Contrato"
            )
        )
    )

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=(
            f"Contrato_{contrato.id}_"
            f"{nome_cliente}.pdf"
        )
    )

@app.route("/contratos")
def contratos():

    if "salao_id" not in session:
        return redirect("/")

    contratos = Contrato.query.filter_by(
        salao_id=session["salao_id"]
    ).order_by(Contrato.id.desc()).all()

    return render_template(
        "contratos.html",
        contratos=contratos
    )

@app.route("/cadastrar_salao", methods=["POST"])
def cadastrar_salao():

    try:

        # =====================================================
        # RECEBE OS DADOS
        # =====================================================

        if request.is_json:
            dados = request.get_json()

            nome = dados.get("nome", "").strip()
            responsavel = dados.get("responsavel", "").strip()
            telefone = dados.get("telefone", "").strip()
            cnpj = dados.get("cnpj", "").strip()
            cidade = dados.get("cidade", "").strip()
            plano = dados.get("plano", "").strip()
            senha = dados.get("senha", "").strip()
            email = dados.get("email", "").strip()

        else:

            nome = request.form.get("nome", "").strip()
            responsavel = request.form.get("responsavel", "").strip()
            telefone = request.form.get("telefone", "").strip()
            cnpj = request.form.get("cnpj", "").strip()
            cidade = request.form.get("cidade", "").strip()
            plano = request.form.get("plano", "").strip()
            senha = request.form.get("senha", "").strip()
            email = request.form.get("email", "").strip()


        # =====================================================
        # VALIDAÇÕES
        # =====================================================

        if not nome:
            return jsonify({
                "sucesso": False,
                "mensagem": "Informe o nome do salão."
            }), 400

        if not responsavel:
            return jsonify({
                "sucesso": False,
                "mensagem": "Informe o responsável."
            }), 400

        if not senha:
            return jsonify({
                "sucesso": False,
                "mensagem": "Informe uma senha."
            }), 400

        if plano not in [
            "Essencial",
            "Profissional",
            "Premium"
        ]:
            return jsonify({
                "sucesso": False,
                "mensagem": "Plano inválido."
            }), 400


        # =====================================================
        # EMAIL
        # =====================================================

        if not email:

            email = (
                nome
                .lower()
                .replace(" ", "")
                + "@salon.com.br"
            )

        else:

            email = email.lower().strip()


        # =====================================================
        # VERIFICA SE EMAIL JÁ EXISTE
        # =====================================================

        if Salao.query.filter_by(email=email).first():

            return jsonify({
                "sucesso": False,
                "mensagem": "Já existe um salão cadastrado com este email."
            }), 400


        # =====================================================
        # CRIA O SALÃO
        # =====================================================

        novo = Salao(

            nome=nome,

            responsavel=responsavel,

            telefone=telefone,

            cnpj=cnpj,

            cidade=cidade,

            plano=plano,

            email=email,

            senha=generate_password_hash(senha),

            ativo=True

        )


        db.session.add(novo)

        db.session.commit()


        # =====================================================
        # CRIA AS PERMISSÕES
        # =====================================================

        permissao = Permissao(

            salao_id=novo.id,

            dashboard=False,

            agenda=False,

            contratos=False,

            estoque=False,

            financeiro=False,

            funcionarios=False,

            relatorios=False,

            configuracoes=False

        )


        # =====================================================
        # PLANO ESSENCIAL
        # =====================================================

        if plano == "Essencial":

            permissao.dashboard = True

            permissao.agenda = True

            permissao.contratos = True


        # =====================================================
        # PLANO PROFISSIONAL
        # =====================================================

        elif plano == "Profissional":

            permissao.dashboard = True

            permissao.agenda = True

            permissao.contratos = True

            permissao.estoque = True

            permissao.financeiro = True

            permissao.relatorios = True


        # =====================================================
        # PLANO PREMIUM
        # =====================================================

        elif plano == "Premium":

            permissao.dashboard = True

            permissao.agenda = True

            permissao.contratos = True

            permissao.estoque = True

            permissao.financeiro = True

            permissao.funcionarios = True

            permissao.relatorios = True

            permissao.configuracoes = True


        db.session.add(permissao)

        db.session.commit()


        # =====================================================
        # LOGIN AUTOMÁTICO APÓS PAGAMENTO
        # =====================================================

        session["tipo"] = "salao"

        session["salao_id"] = novo.id

        session["nome"] = novo.nome


        # =====================================================
        # RESPOSTA
        # =====================================================

        return jsonify({

            "sucesso": True,

            "mensagem": "Salão cadastrado com sucesso!",

            "salao_id": novo.id,

            "nome": novo.nome,

            "email": novo.email,

            "plano": novo.plano,

            "redirect": "/pagina_inicial"

        })


    except Exception as e:

        db.session.rollback()

        print("ERRO AO CADASTRAR SALÃO:", e)

        return jsonify({

            "sucesso": False,

            "mensagem": "Erro ao cadastrar o salão."

        }), 500


@app.route("/pagina_inicial")
def pagina_inicial():

    if "salao_id" not in session:
        return redirect("/")

    # Busca o salão logado
    salao = Salao.query.get_or_404(session["salao_id"])

    # Busca as permissões desse salão diretamente no banco
    permissao = Permissao.query.filter_by(
        salao_id=salao.id
    ).first()

    # Permissões padrão
    modulos = {
        "dashboard": False,
        "agenda": False,
        "contratos": False,
        "estoque": False,
        "financeiro": False,
        "funcionarios": False,
        "relatorios": False,
        "configuracoes": False,
        "novo_contrato": False,
        "pre_contrato": False
    }

    # Carrega as permissões salvas no banco
    if permissao:
        modulos["dashboard"] = bool(permissao.dashboard)
        modulos["agenda"] = bool(permissao.agenda)
        modulos["contratos"] = bool(permissao.contratos)
        modulos["estoque"] = bool(permissao.estoque)
        modulos["financeiro"] = bool(permissao.financeiro)
        modulos["funcionarios"] = bool(permissao.funcionarios)
        modulos["relatorios"] = bool(permissao.relatorios)
        modulos["configuracoes"] = bool(permissao.configuracoes)

        # Não existem colunas próprias para estes módulos na tabela permissoes.
        # Por enquanto, ambos seguem a permissão de contratos.
        modulos["novo_contrato"] = bool(permissao.contratos)
        modulos["pre_contrato"] = bool(permissao.contratos)

    return render_template(
        "pagina_inicial.html",
        salao=salao,
        modulos=modulos
    )

@app.route("/saloes")
def listar_saloes():

    saloes = Salao.query.order_by(Salao.nome).all()

    return render_template(
        "saloes.html",
        saloes=saloes
    )
@app.route("/editar_salao/<int:id>")
def editar_salao(id):
    return "Tela de edição em construção"

@app.route("/permissoes/<int:id>")
def permissoes(id):
    return "Tela de permissões em construção"

@app.route("/excluir_salao/<int:id>")
def excluir_salao(id):

    salao = Salao.query.get_or_404(id)

    permissao = Permissao.query.filter_by(
        salao_id=id
    ).first()

    if permissao:
        db.session.delete(permissao)

    db.session.delete(salao)

    db.session.commit()

    return redirect("/saloes")

@app.route("/excluir_contrato/<int:id>")
def excluir_contrato(id):

    if "salao_id" not in session:
        return redirect("/")

    contrato = Contrato.query.filter_by(
        id=id,
        salao_id=session["salao_id"]
    ).first_or_404()

    db.session.delete(contrato)
    db.session.commit()

    return redirect("/contratos")

# ===========================
# EXECUTAR
# ===========================
# ===========================
# AGENDA
# ===========================

@app.route("/agenda")
def agenda():

    if "salao_id" not in session:
        return redirect("/")

    salao = Salao.query.get_or_404(
        session["salao_id"]
    )

    return render_template(
        "agenda.html",
        salao=salao
    )
@app.route("/api/agenda")
def api_agenda():

    if "salao_id" not in session:
        return jsonify({
            "erro": "Usuário não autenticado."
        }), 401

    contratos = Contrato.query.filter_by(
        salao_id=session["salao_id"]
    ).order_by(Contrato.id.asc()).all()

    eventos = []

    for contrato in contratos:

        data_evento = (contrato.data_evento or "").strip()

        # ==============================
        # CONVERTE A DATA
        # ==============================

        if "/" in data_evento:

            partes = data_evento.split("/")

            if len(partes) == 3:
                dia = partes[0].zfill(2)
                mes = partes[1].zfill(2)
                ano = partes[2]

                data_formatada = f"{ano}-{mes}-{dia}"
            else:
                data_formatada = data_evento

        elif "-" in data_evento:

            partes = data_evento.split("-")

            if len(partes) == 3:
                ano = partes[0]
                mes = partes[1].zfill(2)
                dia = partes[2].zfill(2)

                data_formatada = f"{ano}-{mes}-{dia}"
            else:
                data_formatada = data_evento

        else:
            data_formatada = data_evento

        # ==============================
        # HORÁRIOS DA FESTA
        # ==============================

        hora_inicio = (contrato.hora_inicio or "").strip()
        hora_fim = (contrato.hora_fim or "").strip()

        # ==============================
        # EVENTO
        # ==============================

        eventos.append({
            "id": contrato.id,
            "aniversariante": contrato.aniversariante or "",
            "data_evento": data_formatada,
            "hora_inicio": hora_inicio,
            "hora_fim": hora_fim
        })

    return jsonify(eventos)
# ==========================================================
# ======================= ESTOQUE ===========================
# ==========================================================


# ==========================================================
# MODELO: ITENS DO ESTOQUE
# ==========================================================

class EstoqueItem(db.Model):
    __tablename__ = "estoque_itens"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    salao_id = db.Column(
        db.Integer,
        db.ForeignKey("saloes.id"),
        nullable=False
    )

    nome = db.Column(
        db.String(150),
        nullable=False
    )

    categoria = db.Column(
        db.String(100)
    )

    unidade = db.Column(
        db.String(50),
        default="unidade"
    )

    quantidade = db.Column(
        db.Float,
        default=0
    )

    estoque_minimo = db.Column(
        db.Float,
        default=0
    )

    estoque_medio = db.Column(
        db.Float,
        default=0
    )

    preco = db.Column(
        db.Float,
        default=0
    )

    consumo_por_pessoa = db.Column(
        db.Float,
        default=0
    )

    ativo = db.Column(
        db.Integer,
        default=1
    )

    criado_em = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )

    atualizado_em = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )


# ==========================================================
# MODELO: MOVIMENTAÇÕES DO ESTOQUE
# ==========================================================

class EstoqueMovimentacao(db.Model):
    __tablename__ = "estoque_movimentacoes"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    salao_id = db.Column(
        db.Integer,
        db.ForeignKey("saloes.id"),
        nullable=False
    )

    item_id = db.Column(
        db.Integer,
        db.ForeignKey("estoque_itens.id"),
        nullable=False
    )

    tipo = db.Column(
        db.String(30),
        nullable=False
    )

    quantidade = db.Column(
        db.Float,
        nullable=False
    )

    quantidade_anterior = db.Column(
        db.Float,
        default=0
    )

    quantidade_nova = db.Column(
        db.Float,
        default=0
    )

    preco_unitario = db.Column(
        db.Float,
        default=0
    )

    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("contratos.id"),
        nullable=True
    )

    observacao = db.Column(
        db.Text
    )

    criado_em = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )


# ==========================================================
# ROTA: PÁGINA DO ESTOQUE
# ==========================================================

@app.route("/estoque")
def estoque():

    if "salao_id" not in session:
        return redirect("/")

    salao = Salao.query.get_or_404(
        session["salao_id"]
    )

    return render_template(
        "estoque.html",
        salao=salao
    )


# ==========================================================
# ROTA: LISTAR ESTOQUE
# ==========================================================

@app.route("/api/estoque")
def api_estoque():

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    itens = EstoqueItem.query.filter_by(
        salao_id=session["salao_id"],
        ativo=1
    ).order_by(
        EstoqueItem.nome.asc()
    ).all()

    resultado = []

    for item in itens:

        if item.quantidade <= item.estoque_minimo:
            nivel = "baixo"

        elif item.quantidade <= item.estoque_medio:
            nivel = "medio"

        else:
            nivel = "alto"

        resultado.append({
            "id": item.id,
            "nome": item.nome,
            "categoria": item.categoria or "",
            "unidade": item.unidade or "unidade",
            "quantidade": item.quantidade or 0,
            "estoque_minimo": item.estoque_minimo or 0,
            "estoque_medio": item.estoque_medio or 0,
            "preco": item.preco or 0,
            "consumo_por_pessoa":
                item.consumo_por_pessoa or 0,
            "nivel": nivel
        })

    return jsonify({
        "sucesso": True,
        "itens": resultado
    })


# ==========================================================
# ROTA: ADICIONAR ITEM
# ==========================================================

@app.route(
    "/api/estoque/adicionar",
    methods=["POST"]
)
def adicionar_estoque():

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    dados = request.get_json()

    if not dados:
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhum dado recebido."
        }), 400

    nome = str(
        dados.get("nome", "")
    ).strip()

    if not nome:
        return jsonify({
            "sucesso": False,
            "mensagem": "Informe o nome do item."
        }), 400

    try:
        quantidade = float(
            dados.get("quantidade", 0)
        )

        estoque_minimo = float(
            dados.get("estoque_minimo", 0)
        )

        estoque_medio = float(
            dados.get("estoque_medio", 0)
        )

        preco = float(
            dados.get("preco", 0)
        )

        consumo_por_pessoa = float(
            dados.get("consumo_por_pessoa", 0)
        )

    except (ValueError, TypeError):

        return jsonify({
            "sucesso": False,
            "mensagem": "Existem valores numéricos inválidos."
        }), 400

    if quantidade < 0:
        return jsonify({
            "sucesso": False,
            "mensagem": "A quantidade não pode ser negativa."
        }), 400

    item = EstoqueItem(
        salao_id=session["salao_id"],
        nome=nome,
        categoria=dados.get(
            "categoria",
            ""
        ),
        unidade=dados.get(
            "unidade",
            "unidade"
        ),
        quantidade=quantidade,
        estoque_minimo=estoque_minimo,
        estoque_medio=estoque_medio,
        preco=preco,
        consumo_por_pessoa=consumo_por_pessoa,
        ativo=1
    )

    db.session.add(item)
    db.session.commit()

    # Registra a quantidade inicial
    if quantidade > 0:

        movimentacao = EstoqueMovimentacao(
            salao_id=session["salao_id"],
            item_id=item.id,
            tipo="entrada",
            quantidade=quantidade,
            quantidade_anterior=0,
            quantidade_nova=quantidade,
            preco_unitario=preco,
            observacao="Cadastro inicial do item"
        )

        db.session.add(movimentacao)
        db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Item adicionado com sucesso.",
        "id": item.id
    })


# ==========================================================
# ROTA: EDITAR ITEM
# ==========================================================

@app.route(
    "/api/estoque/editar/<int:id>",
    methods=["PUT"]
)
def editar_estoque(id):

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    item = EstoqueItem.query.filter_by(
        id=id,
        salao_id=session["salao_id"],
        ativo=1
    ).first()

    if not item:
        return jsonify({
            "sucesso": False,
            "mensagem": "Item não encontrado."
        }), 404

    dados = request.get_json()

    if not dados:
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhum dado recebido."
        }), 400

    quantidade_anterior = item.quantidade

    try:
        nova_quantidade = float(
            dados.get(
                "quantidade",
                item.quantidade
            )
        )

        novo_minimo = float(
            dados.get(
                "estoque_minimo",
                item.estoque_minimo
            )
        )

        novo_medio = float(
            dados.get(
                "estoque_medio",
                item.estoque_medio
            )
        )

        novo_preco = float(
            dados.get(
                "preco",
                item.preco
            )
        )

        novo_consumo = float(
            dados.get(
                "consumo_por_pessoa",
                item.consumo_por_pessoa
            )
        )

    except (ValueError, TypeError):

        return jsonify({
            "sucesso": False,
            "mensagem": "Existem valores numéricos inválidos."
        }), 400

    if nova_quantidade < 0:
        return jsonify({
            "sucesso": False,
            "mensagem": "A quantidade não pode ser negativa."
        }), 400

    item.nome = str(
        dados.get(
            "nome",
            item.nome
        )
    ).strip()

    item.categoria = dados.get(
        "categoria",
        item.categoria
    )

    item.unidade = dados.get(
        "unidade",
        item.unidade
    )

    item.quantidade = nova_quantidade
    item.estoque_minimo = novo_minimo
    item.estoque_medio = novo_medio
    item.preco = novo_preco
    item.consumo_por_pessoa = novo_consumo
    item.atualizado_em = datetime.now()

    # Registra alteração de quantidade
    if quantidade_anterior != nova_quantidade:

        movimentacao = EstoqueMovimentacao(
            salao_id=session["salao_id"],
            item_id=item.id,
            tipo="ajuste",
            quantidade=abs(
                nova_quantidade -
                quantidade_anterior
            ),
            quantidade_anterior=quantidade_anterior,
            quantidade_nova=nova_quantidade,
            preco_unitario=novo_preco,
            observacao="Ajuste manual do estoque"
        )

        db.session.add(movimentacao)

    db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Item atualizado com sucesso."
    })


# ==========================================================
# ROTA: REMOVER ITEM
# ==========================================================

@app.route(
    "/api/estoque/remover/<int:id>",
    methods=["DELETE"]
)
def remover_estoque(id):

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    item = EstoqueItem.query.filter_by(
        id=id,
        salao_id=session["salao_id"],
        ativo=1
    ).first()

    if not item:
        return jsonify({
            "sucesso": False,
            "mensagem": "Item não encontrado."
        }), 404

    # Não apaga fisicamente.
    # Apenas desativa para preservar o histórico.
    item.ativo = 0
    item.atualizado_em = datetime.now()

    db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Item removido do estoque."
    })


# ==========================================================
# ROTA: DAR BAIXA NO ESTOQUE
# ==========================================================

@app.route(
    "/api/estoque/baixa",
    methods=["POST"]
)
def baixa_estoque():

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    dados = request.get_json()

    if not dados:
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhum dado recebido."
        }), 400

    item_id = dados.get("item_id")

    try:
        quantidade = float(
            dados.get("quantidade", 0)
        )
    except (ValueError, TypeError):

        quantidade = 0

    if quantidade <= 0:
        return jsonify({
            "sucesso": False,
            "mensagem": "Informe uma quantidade válida."
        }), 400

    item = EstoqueItem.query.filter_by(
        id=item_id,
        salao_id=session["salao_id"],
        ativo=1
    ).first()

    if not item:
        return jsonify({
            "sucesso": False,
            "mensagem": "Item não encontrado."
        }), 404

    if quantidade > item.quantidade:

        return jsonify({
            "sucesso": False,
            "mensagem": (
                "A quantidade informada é maior "
                "que o estoque disponível."
            )
        }), 400

    quantidade_anterior = item.quantidade

    item.quantidade = (
        item.quantidade - quantidade
    )

    item.atualizado_em = datetime.now()

    movimentacao = EstoqueMovimentacao(
        salao_id=session["salao_id"],
        item_id=item.id,
        tipo="saida",
        quantidade=quantidade,
        quantidade_anterior=quantidade_anterior,
        quantidade_nova=item.quantidade,
        preco_unitario=item.preco,
        contrato_id=dados.get("contrato_id"),
        observacao=dados.get(
            "observacao",
            "Baixa de estoque"
        )
    )

    db.session.add(movimentacao)
    db.session.commit()

    return jsonify({
        "sucesso": True,
        "mensagem": "Baixa realizada com sucesso.",
        "quantidade_atual": item.quantidade
    })


# ==========================================================
# ROTA: HISTÓRICO DO ESTOQUE
# ==========================================================

@app.route(
    "/api/estoque/movimentacoes"
)
def estoque_movimentacoes():

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    movimentacoes = (
        EstoqueMovimentacao.query
        .filter_by(
            salao_id=session["salao_id"]
        )
        .order_by(
            EstoqueMovimentacao.id.desc()
        )
        .all()
    )

    resultado = []

    for mov in movimentacoes:

        item = EstoqueItem.query.get(
            mov.item_id
        )

        resultado.append({
            "id": mov.id,
            "item_id": mov.item_id,
            "item": (
                item.nome
                if item
                else "Item removido"
            ),
            "tipo": mov.tipo,
            "quantidade": mov.quantidade,
            "quantidade_anterior":
                mov.quantidade_anterior,
            "quantidade_nova":
                mov.quantidade_nova,
            "preco_unitario":
                mov.preco_unitario,
            "contrato_id":
                mov.contrato_id,
            "observacao":
                mov.observacao or "",
            "criado_em": (
                mov.criado_em.strftime(
                    "%d/%m/%Y %H:%M"
                )
                if mov.criado_em
                else ""
            )
        })

    return jsonify({
        "sucesso": True,
        "movimentacoes": resultado
    })


# ==========================================================
# ROTA: PREVISÃO DE CONSUMO DAS FESTAS
# ==========================================================
# ==========================================================
# ROTA: GERAR PDF DOS GASTOS DO ESTOQUE
# ==========================================================

@app.route("/api/estoque/relatorio-pdf")
def relatorio_pdf_estoque():

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    # ======================================================
    # BUSCA SOMENTE AS BAIXAS REAIS
    # ======================================================

    movimentacoes = (
        EstoqueMovimentacao.query
        .filter_by(
            salao_id=session["salao_id"],
            tipo="saida"
        )
        .order_by(
            EstoqueMovimentacao.criado_em.asc()
        )
        .all()
    )

    # ======================================================
    # PDF
    # ======================================================

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloEstoque",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=8
    )

    subtitulo = ParagraphStyle(
        "SubtituloEstoque",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceAfter=15
    )

    normal = ParagraphStyle(
        "NormalEstoque",
        parent=styles["Normal"],
        fontSize=8,
        leading=10
    )

    story = []

    # ======================================================
    # CABEÇALHO
    # ======================================================

    salao = Salao.query.get(
        session["salao_id"]
    )

    nome_salao = (
        salao.nome
        if salao
        else "Salão"
    )

    story.append(
        Paragraph(
            "RELATÓRIO DE GASTOS DO ESTOQUE",
            titulo
        )
    )

    story.append(
        Paragraph(
            f"Salão: {nome_salao}",
            subtitulo
        )
    )

    # ======================================================
    # TABELA
    # ======================================================

    dados_tabela = [
        [
            "Data",
            "Hora",
            "Festa",
            "Item",
            "Qtd.",
            "Preço",
            "Total"
        ]
    ]

    total_geral = 0

    for mov in movimentacoes:

        # ----------------------------------------------
        # ITEM
        # ----------------------------------------------

        item = EstoqueItem.query.get(
            mov.item_id
        )

        nome_item = (
            item.nome
            if item
            else "Item removido"
        )

        unidade = (
            item.unidade
            if item
            else ""
        )

        # ----------------------------------------------
        # FESTA
        # ----------------------------------------------

        festa = "-"

        if mov.contrato_id:

            contrato = Contrato.query.filter_by(
                id=mov.contrato_id,
                salao_id=session["salao_id"]
            ).first()

            if contrato:

                nome_festa = (
                    contrato.aniversariante
                    or contrato.cliente
                    or "Festa"
                )

                festa = (
                    f"#{contrato.id} - "
                    f"{nome_festa}"
                )

        # ----------------------------------------------
        # DATA E HORA
        # ----------------------------------------------

        if mov.criado_em:

            data = mov.criado_em.strftime(
                "%d/%m/%Y"
            )

            hora = mov.criado_em.strftime(
                "%H:%M"
            )

        else:

            data = "-"
            hora = "-"

        # ----------------------------------------------
        # VALORES
        # ----------------------------------------------

        quantidade = float(
            mov.quantidade or 0
        )

        preco = float(
            mov.preco_unitario or 0
        )

        valor_total = (
            quantidade * preco
        )

        total_geral += valor_total

        dados_tabela.append(
            [
                data,
                hora,
                Paragraph(
                    str(festa),
                    normal
                ),
                Paragraph(
                    str(nome_item),
                    normal
                ),
                f"{quantidade:g} {unidade}",
                (
                    f"R$ {preco:,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                ),
                (
                    f"R$ {valor_total:,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
            ]
        )

    # ======================================================
    # SE NÃO EXISTIR NENHUM GASTO
    # ======================================================

    if len(dados_tabela) == 1:

        dados_tabela.append(
            [
                "-",
                "-",
                "-",
                "Nenhuma baixa registrada",
                "-",
                "-",
                "-"
            ]
        )

    # ======================================================
    # CRIA TABELA
    # ======================================================

    tabela = Table(
        dados_tabela,
        colWidths=[
            22 * mm,
            16 * mm,
            42 * mm,
            42 * mm,
            22 * mm,
            25 * mm,
            27 * mm
        ],
        repeatRows=1
    )

    tabela.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.black
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.grey
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "ALIGN",
                (4, 1),
                (-1, -1),
                "RIGHT"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )

    story.append(tabela)

    # ======================================================
    # TOTAL GERAL
    # ======================================================

    total_formatado = (
        f"R$ {total_geral:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    story.append(
        Spacer(
            1,
            12
        )
    )

    story.append(
        Paragraph(
            f"<b>TOTAL GERAL GASTO: {total_formatado}</b>",
            ParagraphStyle(
                "Total",
                parent=styles["Normal"],
                fontSize=12,
                alignment=2
            )
        )
    )

    # ======================================================
    # RODAPÉ
    # ======================================================

    story.append(
        Spacer(
            1,
            10
        )
    )

    agora = datetime.now().strftime(
        "%d/%m/%Y às %H:%M"
    )

    story.append(
        Paragraph(
            f"Relatório gerado em {agora}",
            ParagraphStyle(
                "Rodape",
                parent=styles["Normal"],
                fontSize=7,
                textColor=colors.grey,
                alignment=TA_CENTER
            )
        )
    )

    # ======================================================
    # FINALIZA
    # ======================================================

    doc.build(story)

    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=(
            "Relatorio_Gastos_Estoque.pdf"
        )
    )
@app.route("/api/estoque/relatorio-festa/<int:contrato_id>")
def relatorio_pdf_festa(contrato_id):

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    # ==========================================
    # CONTRATO
    # ==========================================

    contrato = Contrato.query.filter_by(
        id=contrato_id,
        salao_id=session["salao_id"]
    ).first()

    if not contrato:
        return jsonify({
            "sucesso": False,
            "mensagem": "Festa não encontrada."
        }), 404

    # ==========================================
    # BAIXAS DA FESTA
    # ==========================================

    movimentacoes = (
        EstoqueMovimentacao.query
        .filter_by(
            salao_id=session["salao_id"],
            contrato_id=contrato_id,
            tipo="saida"
        )
        .order_by(
            EstoqueMovimentacao.criado_em.asc()
        )
        .all()
    )

    # ==========================================
    # PDF
    # ==========================================

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()

    story = []

    titulo = ParagraphStyle(
        "Titulo",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18
    )

    normal = ParagraphStyle(
        "Normal",
        parent=styles["Normal"],
        fontSize=9
    )

    # ==========================================
    # CABEÇALHO
    # ==========================================

    story.append(
        Paragraph(
            "RELATÓRIO DE CONSUMO DA FESTA",
            titulo
        )
    )

    story.append(Spacer(1,10))

    dados = [
        ["Contrato", f"#{contrato.id}"],
        ["Cliente", contrato.cliente or "-"],
        ["Aniversariante", contrato.aniversariante or "-"],
        ["Data da Festa", contrato.data_evento or "-"],
        ["Convidados", str(
            (contrato.convidados or 0) +
            (contrato.qtd_extra or 0)
        )]
    ]

    tabela_info = Table(
        dados,
        colWidths=[50*mm,120*mm]
    )

    tabela_info.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ("BACKGROUND",(0,0),(0,-1),colors.lightgrey)
    ]))

    story.append(tabela_info)
    story.append(Spacer(1,15))

    # ==========================================
    # TABELA DE ITENS
    # ==========================================

    tabela = [[
        "Item",
        "Categoria",
        "Qtd",
        "Unidade",
        "Valor Unit.",
        "Total"
    ]]

    total_geral = 0

    for mov in movimentacoes:

        item = EstoqueItem.query.get(
            mov.item_id
        )

        nome = item.nome if item else "-"
        categoria = item.categoria if item else "-"
        unidade = item.unidade if item else ""

        quantidade = float(mov.quantidade or 0)

        preco = float(
            mov.preco_unitario or 0
        )

        total = quantidade * preco

        total_geral += total

        tabela.append([
            nome,
            categoria,
            f"{quantidade:g}",
            unidade,
            f"R$ {preco:.2f}".replace(".", ","),
            f"R$ {total:.2f}".replace(".", ",")
        ])

    if len(tabela) == 1:

        tabela.append([
            "Nenhum item utilizado",
            "-",
            "-",
            "-",
            "-",
            "-"
        ])

    t = Table(
        tabela,
        colWidths=[
            50*mm,
            35*mm,
            20*mm,
            25*mm,
            30*mm,
            30*mm
        ],
        repeatRows=1
    )

    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.black),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ("FONTSIZE",(0,0),(-1,-1),8)
    ]))

    story.append(t)

    story.append(Spacer(1,15))

    total_formatado = (
        f"R$ {total_geral:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X",".")
    )

    story.append(
        Paragraph(
            f"<b>TOTAL GASTO NO ESTOQUE: {total_formatado}</b>",
            styles["Heading2"]
        )
    )

    story.append(Spacer(1,10))

    story.append(
        Paragraph(
            "Relatório gerado em "
            + datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            ),
            normal
        )
    )

    doc.build(story)

    buffer.seek(0)

    nome = re.sub(
        r'[^A-Za-z0-9]',
        '_',
        contrato.aniversariante or "Festa"
    )

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=
        f"Estoque_Festa_{contrato.id}_{nome}.pdf"
    )
@app.route("/api/estoque/previsao")
def estoque_previsao():

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    contratos = Contrato.query.filter_by(
        salao_id=session["salao_id"]
    ).order_by(
        Contrato.id.asc()
    ).all()

    itens = EstoqueItem.query.filter_by(
        salao_id=session["salao_id"],
        ativo=1
    ).all()

    resultado = []

    for contrato in contratos:

        try:
            convidados = int(
                contrato.convidados or 0
            )
        except (ValueError, TypeError):
            convidados = 0

        try:
            extras = int(
                contrato.qtd_extra or 0
            )
        except (ValueError, TypeError):
            extras = 0

        total_convidados = (
            convidados + extras
        )

        produtos = []

        for item in itens:

            # ==========================================
            # QUANTO A FESTA DEVE PRECISAR
            # ==========================================

            necessario = (
                total_convidados *
                (item.consumo_por_pessoa or 0)
            )

            # ==========================================
            # QUANTO JÁ FOI REALMENTE UTILIZADO
            # NESSA FESTA E SOMENTE NESSA FESTA
            # ==========================================

            movimentacoes = (
                EstoqueMovimentacao.query
                .filter_by(
                    salao_id=session["salao_id"],
                    contrato_id=contrato.id,
                    item_id=item.id,
                    tipo="saida"
                )
                .all()
            )

            utilizado = sum(
                mov.quantidade or 0
                for mov in movimentacoes
            )

            # ==========================================
            # QUANTO AINDA FALTA REGISTRAR
            # ==========================================

            restante = max(
                0,
                necessario - utilizado
            )

            produtos.append({

                "item_id": item.id,

                "item": item.nome,

                "categoria":
                    item.categoria or "",

                "unidade":
                    item.unidade or "",

                "consumo_por_pessoa":
                    item.consumo_por_pessoa or 0,

                "necessario":
                    necessario,

                "utilizado":
                    utilizado,

                "restante":
                    restante,

                "estoque_atual":
                    item.quantidade or 0,

                "faltante_estoque":
                    max(
                        0,
                        necessario -
                        item.quantidade
                    ),

                "suficiente":
                    item.quantidade >= necessario,

                "baixa_realizada":
                    utilizado > 0
            })

        resultado.append({

            "contrato_id":
                contrato.id,

            "aniversariante":
                contrato.aniversariante or "",

            "data_evento":
                contrato.data_evento or "",

            "convidados":
                total_convidados,

            "produtos":
                produtos
        })

    return jsonify({
        "sucesso": True,
        "festas": resultado
    })
@app.route("/financeiro")
def financeiro():
    if "salao_id" not in session:
        return redirect("/")

    salao = Salao.query.get_or_404(session["salao_id"])

    # Segurança: o salão só acessa o financeiro se o módulo
    # estiver liberado para ele.
    permissao = Permissao.query.filter_by(
        salao_id=salao.id
    ).first()

    if permissao and not permissao.financeiro:
        return redirect("/pagina_inicial")

    return render_template(
        "financeiro.html",
        salao=salao
    )


# ==========================================================
# API - DADOS DO FINANCEIRO
# ==========================================================

@app.route("/api/financeiro")
def api_financeiro():

    if "salao_id" not in session:
        return jsonify({
            "sucesso": False,
            "mensagem": "Usuário não autenticado."
        }), 401

    salao_id = session["salao_id"]

    # ------------------------------------------------------
    # MÊS SELECIONADO
    # Exemplo: 2026-08
    # ------------------------------------------------------

    mes = request.args.get("mes")

    agora = datetime.now()

    if not mes:
        mes = agora.strftime("%Y-%m")

    try:
        ano, numero_mes = mes.split("-")
        ano = int(ano)
        numero_mes = int(numero_mes)

        if numero_mes < 1 or numero_mes > 12:
            raise ValueError

        inicio_mes = datetime(
            ano,
            numero_mes,
            1
        )

        if numero_mes == 12:
            fim_mes = datetime(
                ano + 1,
                1,
                1
            )
        else:
            fim_mes = datetime(
                ano,
                numero_mes + 1,
                1
            )

    except Exception:
        return jsonify({
            "sucesso": False,
            "mensagem": "Mês inválido."
        }), 400


    # ------------------------------------------------------
    # FUNÇÃO PARA CONVERTER DATA DO CONTRATO
    # Aceita:
    # 2026-08-20
    # 20/08/2026
    # ------------------------------------------------------

    def converter_data(data):

        if not data:
            return None

        data = str(data).strip()

        formatos = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%Y/%m/%d"
        ]

        for formato in formatos:

            try:
                return datetime.strptime(
                    data,
                    formato
                )

            except ValueError:
                pass

        return None


    # ------------------------------------------------------
    # CONTRATOS DO SALÃO
    # ------------------------------------------------------

    contratos_todos = Contrato.query.filter_by(
        salao_id=salao_id
    ).order_by(
        Contrato.id.desc()
    ).all()

    contratos_periodo = []

    for contrato in contratos_todos:

        data_evento = converter_data(
            contrato.data_evento
        )

        if not data_evento:
            continue

        if inicio_mes <= data_evento < fim_mes:
            contratos_periodo.append(
                contrato
            )


    # ------------------------------------------------------
    # RESUMO FINANCEIRO
    # ------------------------------------------------------

    faturamento = 0.0
    recebido = 0.0
    a_receber = 0.0

    qtd_quitados = 0
    qtd_pendentes = 0

    maior_contrato = 0.0
    maior_pendente = 0.0

    hoje = datetime.now().date()
    proximos_eventos = 0


    for contrato in contratos_periodo:

        total = float(
            contrato.valor_total or 0
        )

        pago = float(
            contrato.valor_pago or 0
        )

        restante = contrato.valor_restante

        if restante is None:
            restante = max(
                0,
                total - pago
            )

        restante = float(restante)

        faturamento += total
        recebido += pago
        a_receber += max(
            0,
            restante
        )

        maior_contrato = max(
            maior_contrato,
            total
        )

        maior_pendente = max(
            maior_pendente,
            restante
        )

        if total > 0 and restante <= 0.01:
            qtd_quitados += 1
        else:
            qtd_pendentes += 1

        data_evento = converter_data(
            contrato.data_evento
        )

        if data_evento:
            if data_evento.date() >= hoje:
                proximos_eventos += 1


    qtd_contratos = len(
        contratos_periodo
    )

    ticket_medio = (
        faturamento / qtd_contratos
        if qtd_contratos
        else 0
    )

    percentual_recebido = (
        (recebido / faturamento) * 100
        if faturamento > 0
        else 0
    )


    # ------------------------------------------------------
    # CONTRATOS PARA A TABELA
    # ------------------------------------------------------

    contratos_json = []

    for contrato in contratos_periodo:

        total = float(
            contrato.valor_total or 0
        )

        pago = float(
            contrato.valor_pago or 0
        )

        restante = contrato.valor_restante

        if restante is None:
            restante = max(
                0,
                total - pago
            )

        contratos_json.append({
            "id": contrato.id,
            "cliente": contrato.cliente or "",
            "aniversariante":
                contrato.aniversariante or "",
            "data_evento":
                contrato.data_evento or "",
            "forma_pagamento":
                contrato.forma_pagamento or "",
            "valor_total": total,
            "valor_pago": pago,
            "valor_restante":
                max(0, float(restante)),
            "status":
                contrato.status or "Aberto"
        })


    # ------------------------------------------------------
    # FORMAS DE PAGAMENTO
    # ------------------------------------------------------

    pagamentos = {}

    for contrato in contratos_periodo:

        forma = (
            contrato.forma_pagamento
            or "Não informado"
        ).strip()

        valor = float(
            contrato.valor_pago or 0
        )

        pagamentos[forma] = (
            pagamentos.get(forma, 0)
            + valor
        )

    formas_pagamento = [
        {
            "forma": forma,
            "valor": valor
        }
        for forma, valor in sorted(
            pagamentos.items(),
            key=lambda item: item[1],
            reverse=True
        )
    ]


    # ------------------------------------------------------
    # ESTOQUE ATUAL
    # ------------------------------------------------------

    itens = EstoqueItem.query.filter_by(
        salao_id=salao_id,
        ativo=1
    ).order_by(
        EstoqueItem.nome.asc()
    ).all()

    estoque_json = []

    valor_estoque = 0.0
    estoque_baixo = 0

    for item in itens:

        quantidade = float(
            item.quantidade or 0
        )

        preco = float(
            item.preco or 0
        )

        valor_item = (
            quantidade * preco
        )

        valor_estoque += valor_item

        if quantidade <= float(
            item.estoque_minimo or 0
        ):
            nivel = "baixo"
            nivel_label = "Baixo"
            estoque_baixo += 1

        elif quantidade <= float(
            item.estoque_medio or 0
        ):
            nivel = "medio"
            nivel_label = "Médio"

        else:
            nivel = "alto"
            nivel_label = "Alto"

        estoque_json.append({
            "id": item.id,
            "nome": item.nome or "",
            "categoria":
                item.categoria or "",
            "unidade":
                item.unidade or "unidade",
            "quantidade": quantidade,
            "preco": preco,
            "valor_total": valor_item,
            "nivel": nivel,
            "nivel_label": nivel_label
        })


    # ------------------------------------------------------
    # MOVIMENTAÇÕES DE ESTOQUE DO MÊS
    # ------------------------------------------------------

    movimentacoes = (
        EstoqueMovimentacao.query
        .filter_by(
            salao_id=salao_id
        )
        .all()
    )

    qtd_saidas = 0
    valor_saidas = 0.0

    for mov in movimentacoes:

        if mov.tipo != "saida":
            continue

        data_mov = mov.criado_em

        if not data_mov:
            continue

        if not (
            inicio_mes <= data_mov < fim_mes
        ):
            continue

        quantidade = float(
            mov.quantidade or 0
        )

        preco = float(
            mov.preco_unitario or 0
        )

        qtd_saidas += 1

        valor_saidas += (
            quantidade * preco
        )


    # ------------------------------------------------------
    # EVOLUÇÃO DOS ÚLTIMOS 6 MESES
    # ------------------------------------------------------

    evolucao = []

    for deslocamento in range(5, -1, -1):

        primeiro = (
            inicio_mes
        )

        ano_ev = primeiro.year
        mes_ev = primeiro.month - deslocamento

        while mes_ev <= 0:
            mes_ev += 12
            ano_ev -= 1

        inicio_ev = datetime(
            ano_ev,
            mes_ev,
            1
        )

        if mes_ev == 12:
            fim_ev = datetime(
                ano_ev + 1,
                1,
                1
            )
        else:
            fim_ev = datetime(
                ano_ev,
                mes_ev + 1,
                1
            )

        total_ev = 0.0
        pago_ev = 0.0

        for contrato in contratos_todos:

            data_evento = converter_data(
                contrato.data_evento
            )

            if not data_evento:
                continue

            if inicio_ev <= data_evento < fim_ev:

                total_ev += float(
                    contrato.valor_total or 0
                )

                pago_ev += float(
                    contrato.valor_pago or 0
                )

        evolucao.append({
            "mes":
                inicio_ev.strftime("%Y-%m"),
            "label":
                inicio_ev.strftime("%b/%y"),
            "faturamento":
                total_ev,
            "recebido":
                pago_ev
        })


    return jsonify({

        "sucesso": True,

        "mes": mes,

        "resumo": {

            "faturamento":
                faturamento,

            "recebido":
                recebido,

            "a_receber":
                a_receber,

            "valor_estoque":
                valor_estoque,

            "qtd_contratos":
                qtd_contratos,

            "qtd_quitados":
                qtd_quitados,

            "qtd_pendentes":
                qtd_pendentes,

            "ticket_medio":
                ticket_medio,

            "percentual_recebido":
                percentual_recebido,

            "proximos_eventos":
                proximos_eventos,

            "qtd_itens_estoque":
                len(itens),

            "estoque_baixo":
                estoque_baixo,

            "qtd_saidas":
                qtd_saidas,

            "valor_saidas":
                valor_saidas,

            # No sistema atual não existe uma tabela
            # de despesas financeiras. Portanto este valor
            # representa o custo das saídas do estoque,
            # não "despesas gerais".
            "custo_consumo":
                valor_saidas,

            "maior_contrato":
                maior_contrato,

            "maior_pendente":
                maior_pendente
        },

        "formas_pagamento":
            formas_pagamento,

        "contratos":
            contratos_json,

        "estoque":
            estoque_json,

        "evolucao":
            evolucao
    })
# ==========================================================
# RELATÓRIO FINANCEIRO PDF
# ==========================================================

@app.route("/financeiro/relatorio-pdf")
def relatorio_financeiro_pdf():

    if "salao_id" not in session:
        return redirect("/")

    salao_id = session["salao_id"]

    salao = Salao.query.get_or_404(
        salao_id
    )

    # ======================================================
    # MÊS SELECIONADO
    # ======================================================

    mes = request.args.get("mes")

    if not mes:
        mes = datetime.now().strftime("%Y-%m")

    try:

        ano, numero_mes = mes.split("-")

        ano = int(ano)
        numero_mes = int(numero_mes)

        if numero_mes < 1 or numero_mes > 12:
            raise ValueError

        inicio_mes = datetime(
            ano,
            numero_mes,
            1
        )

        if numero_mes == 12:

            fim_mes = datetime(
                ano + 1,
                1,
                1
            )

        else:

            fim_mes = datetime(
                ano,
                numero_mes + 1,
                1
            )

    except Exception:

        return "Mês inválido.", 400


    # ======================================================
    # FUNÇÃO PARA DATA
    # ======================================================

    def converter_data(data):

        if not data:
            return None

        data = str(data).strip()

        formatos = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%Y/%m/%d"
        ]

        for formato in formatos:

            try:

                return datetime.strptime(
                    data,
                    formato
                )

            except ValueError:
                pass

        return None


    # ======================================================
    # FORMATAÇÃO DE MOEDA
    # ======================================================

    def moeda(valor):

        valor = float(valor or 0)

        return (
            f"R$ {valor:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )


    # ======================================================
    # NOME DO MÊS
    # ======================================================

    nomes_meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro"
    ]

    nome_mes = nomes_meses[
        numero_mes - 1
    ]


    # ======================================================
    # CONTRATOS DO SALÃO
    # ======================================================

    contratos = Contrato.query.filter_by(
        salao_id=salao_id
    ).order_by(
        Contrato.id.desc()
    ).all()


    contratos_periodo = []

    for contrato in contratos:

        data_evento = converter_data(
            contrato.data_evento
        )

        if not data_evento:
            continue

        if inicio_mes <= data_evento < fim_mes:

            contratos_periodo.append(
                contrato
            )


    # ======================================================
    # INDICADORES
    # ======================================================

    faturamento = 0
    recebido = 0
    a_receber = 0

    qtd_quitados = 0
    qtd_pendentes = 0

    maior_contrato = 0
    maior_pendente = 0

    for contrato in contratos_periodo:

        total = float(
            contrato.valor_total or 0
        )

        pago = float(
            contrato.valor_pago or 0
        )

        restante = contrato.valor_restante

        if restante is None:

            restante = max(
                0,
                total - pago
            )

        restante = float(
            restante
        )

        faturamento += total
        recebido += pago
        a_receber += max(
            0,
            restante
        )

        maior_contrato = max(
            maior_contrato,
            total
        )

        maior_pendente = max(
            maior_pendente,
            restante
        )

        if total > 0 and restante <= 0.01:

            qtd_quitados += 1

        else:

            qtd_pendentes += 1


    qtd_contratos = len(
        contratos_periodo
    )

    ticket_medio = (
        faturamento / qtd_contratos
        if qtd_contratos
        else 0
    )

    percentual_recebido = (
        (recebido / faturamento) * 100
        if faturamento > 0
        else 0
    )


    # ======================================================
    # FORMAS DE PAGAMENTO
    # ======================================================

    pagamentos = {}

    for contrato in contratos_periodo:

        forma = (
            contrato.forma_pagamento
            or "Não informado"
        )

        forma = forma.strip()

        valor = float(
            contrato.valor_pago or 0
        )

        pagamentos[forma] = (
            pagamentos.get(
                forma,
                0
            ) + valor
        )


    # ======================================================
    # ESTOQUE ATUAL
    # ======================================================

    itens = EstoqueItem.query.filter_by(
        salao_id=salao_id,
        ativo=1
    ).order_by(
        EstoqueItem.nome.asc()
    ).all()


    valor_estoque = 0
    estoque_baixo = 0

    for item in itens:

        quantidade = float(
            item.quantidade or 0
        )

        preco = float(
            item.preco or 0
        )

        valor_estoque += (
            quantidade * preco
        )

        if quantidade <= float(
            item.estoque_minimo or 0
        ):

            estoque_baixo += 1


    # ======================================================
    # MOVIMENTAÇÕES DO MÊS
    # ======================================================

    movimentacoes = (
        EstoqueMovimentacao.query
        .filter_by(
            salao_id=salao_id
        )
        .order_by(
            EstoqueMovimentacao.criado_em.asc()
        )
        .all()
    )


    saidas = []

    valor_saidas = 0

    for mov in movimentacoes:

        if mov.tipo != "saida":
            continue

        if not mov.criado_em:
            continue

        if not (
            inicio_mes
            <= mov.criado_em
            < fim_mes
        ):
            continue

        item = EstoqueItem.query.get(
            mov.item_id
        )

        quantidade = float(
            mov.quantidade or 0
        )

        preco = float(
            mov.preco_unitario or 0
        )

        total = (
            quantidade * preco
        )

        valor_saidas += total

        saidas.append({
            "item":
                item.nome
                if item
                else "-",

            "quantidade":
                quantidade,

            "unidade":
                item.unidade
                if item
                else "",

            "preco":
                preco,

            "total":
                total,

            "contrato":
                mov.contrato_id,

            "data":
                mov.criado_em.strftime(
                    "%d/%m/%Y"
                )
        })


    # ======================================================
    # PDF
    # ======================================================

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(

        buffer,

        pagesize=A4,

        rightMargin=14 * mm,
        leftMargin=14 * mm,

        topMargin=16 * mm,
        bottomMargin=16 * mm
    )


    styles = getSampleStyleSheet()


    titulo = ParagraphStyle(
        "TituloFinanceiro",

        parent=styles["Title"],

        fontName="Helvetica-Bold",

        fontSize=19,

        leading=23,

        alignment=TA_CENTER,

        textColor=colors.HexColor(
            "#111111"
        ),

        spaceAfter=5
    )


    subtitulo = ParagraphStyle(
        "SubtituloFinanceiro",

        parent=styles["Normal"],

        fontSize=9,

        alignment=TA_CENTER,

        textColor=colors.HexColor(
            "#666666"
        ),

        spaceAfter=16
    )


    secao = ParagraphStyle(
        "SecaoFinanceiro",

        parent=styles["Heading2"],

        fontName="Helvetica-Bold",

        fontSize=12,

        leading=15,

        textColor=colors.HexColor(
            "#111111"
        ),

        spaceBefore=12,

        spaceAfter=7
    )


    normal = ParagraphStyle(
        "NormalFinanceiro",

        parent=styles["Normal"],

        fontSize=8.5,

        leading=11
    )


    pequeno = ParagraphStyle(
        "PequenoFinanceiro",

        parent=styles["Normal"],

        fontSize=7.5,

        leading=9
    )


    destaque = ParagraphStyle(
        "DestaqueFinanceiro",

        parent=styles["Normal"],

        fontName="Helvetica-Bold",

        fontSize=10,

        leading=13
    )


    story = []


    # ======================================================
    # CABEÇALHO
    # ======================================================

    story.append(
        Paragraph(
            "RELATÓRIO FINANCEIRO",
            titulo
        )
    )

    story.append(
        Paragraph(
            f"<b>{salao.nome}</b><br/>"
            f"Período: {nome_mes} de {ano}",
            subtitulo
        )
    )


    # ======================================================
    # RESUMO EXECUTIVO
    # ======================================================

    story.append(
        Paragraph(
            "1. Resumo financeiro",
            secao
        )
    )


    resumo = [

        [
            Paragraph(
                "<b>Faturamento contratado</b>",
                pequeno
            ),

            Paragraph(
                "<b>Total recebido</b>",
                pequeno
            ),

            Paragraph(
                "<b>A receber</b>",
                pequeno
            )
        ],

        [
            Paragraph(
                moeda(faturamento),
                destaque
            ),

            Paragraph(
                moeda(recebido),
                destaque
            ),

            Paragraph(
                moeda(a_receber),
                destaque
            )
        ],

        [
            Paragraph(
                f"{qtd_contratos} contrato(s)",
                pequeno
            ),

            Paragraph(
                f"{percentual_recebido:.1f}% recebido",
                pequeno
            ),

            Paragraph(
                f"{qtd_pendentes} pendente(s)",
                pequeno
            )
        ]
    ]


    tabela_resumo = Table(
        resumo,

        colWidths=[
            58 * mm,
            58 * mm,
            58 * mm
        ]
    )


    tabela_resumo.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#111111")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "BACKGROUND",
                (0, 1),
                (-1, -1),
                colors.HexColor("#F7F7F7")
            ),

            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.7,
                colors.HexColor("#DDDDDD")
            ),

            (
                "INNERGRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor("#DDDDDD")
            ),

            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7
            )
        ])
    )


    story.append(
        tabela_resumo
    )


    # ======================================================
    # INDICADORES
    # ======================================================

    story.append(
        Paragraph(
            "2. Indicadores de desempenho",
            secao
        )
    )


    indicadores = [

        [
            "Contratos",
            str(qtd_contratos)
        ],

        [
            "Contratos quitados",
            str(qtd_quitados)
        ],

        [
            "Contratos pendentes",
            str(qtd_pendentes)
        ],

        [
            "Ticket médio",
            moeda(ticket_medio)
        ],

        [
            "Maior contrato",
            moeda(maior_contrato)
        ],

        [
            "Maior saldo pendente",
            moeda(maior_pendente)
        ]
    ]


    tabela_indicadores = Table(
        indicadores,

        colWidths=[
            80 * mm,
            94 * mm
        ]
    )


    tabela_indicadores.setStyle(
        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor("#DDDDDD")
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor("#F2F2F2")
            ),

            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),

            (
                "ALIGN",
                (1, 0),
                (1, -1),
                "RIGHT"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )


    story.append(
        tabela_indicadores
    )


    # ======================================================
    # FORMAS DE PAGAMENTO
    # ======================================================

    story.append(
        Paragraph(
            "3. Recebimentos por forma de pagamento",
            secao
        )
    )


    tabela_pagamentos = [
        [
            "Forma de pagamento",
            "Valor recebido",
            "Participação"
        ]
    ]


    for forma, valor in sorted(
        pagamentos.items(),
        key=lambda x: x[1],
        reverse=True
    ):

        percentual = (
            (valor / recebido) * 100
            if recebido > 0
            else 0
        )

        tabela_pagamentos.append([
            forma,
            moeda(valor),
            f"{percentual:.1f}%"
        ])


    if len(tabela_pagamentos) == 1:

        tabela_pagamentos.append([
            "Nenhum recebimento",
            moeda(0),
            "0%"
        ])


    tabela_formas = Table(
        tabela_pagamentos,

        colWidths=[
            80 * mm,
            55 * mm,
            39 * mm
        ],

        repeatRows=1
    )


    tabela_formas.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#111111")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor("#DDDDDD")
            ),

            (
                "ALIGN",
                (1, 1),
                (-1, -1),
                "RIGHT"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )


    story.append(
        tabela_formas
    )


    # ======================================================
    # CONTRATOS
    # ======================================================

    story.append(
        Paragraph(
            "4. Contratos do período",
            secao
        )
    )


    tabela_contratos = [[
        "Contrato",
        "Cliente",
        "Evento",
        "Data",
        "Total",
        "Pago",
        "A receber",
        "Situação"
    ]]


    for contrato in contratos_periodo:

        total = float(
            contrato.valor_total or 0
        )

        pago = float(
            contrato.valor_pago or 0
        )

        restante = contrato.valor_restante

        if restante is None:

            restante = max(
                0,
                total - pago
            )

        if total > 0 and restante <= 0.01:

            situacao = "QUITADO"

        elif pago > 0:

            situacao = "PARCIAL"

        else:

            situacao = "PENDENTE"


        tabela_contratos.append([

            f"#{contrato.id}",

            contrato.cliente or "-",

            contrato.aniversariante or "-",

            contrato.data_evento or "-",

            moeda(total),

            moeda(pago),

            moeda(restante),

            situacao
        ])


    if len(tabela_contratos) == 1:

        tabela_contratos.append([
            "-",
            "Nenhum contrato no período",
            "-",
            "-",
            moeda(0),
            moeda(0),
            moeda(0),
            "-"
        ])


    tabela_contratos_pdf = Table(
        tabela_contratos,

        colWidths=[
            15 * mm,
            36 * mm,
            31 * mm,
            22 * mm,
            25 * mm,
            25 * mm,
            25 * mm,
            20 * mm
        ],

        repeatRows=1
    )


    tabela_contratos_pdf.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#111111")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.35,
                colors.HexColor("#D5D5D5")
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                6.5
            ),

            (
                "ALIGN",
                (4, 1),
                (-2, -1),
                "RIGHT"
            ),

            (
                "ALIGN",
                (-1, 1),
                (-1, -1),
                "CENTER"
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F8F8F8")
                ]
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )


    story.append(
        tabela_contratos_pdf
    )


    # ======================================================
    # ESTOQUE
    # ======================================================

    story.append(
        Paragraph(
            "5. Posição atual do estoque",
            secao
        )
    )


    estoque_resumo = [[
        "Valor atual do estoque",
        moeda(valor_estoque)
    ], [
        "Itens ativos",
        str(len(itens))
    ], [
        "Itens no estoque mínimo/baixo",
        str(estoque_baixo)
    ], [
        "Saídas no mês",
        str(len(saidas))
    ], [
        "Custo das saídas",
        moeda(valor_saidas)
    ]]


    tabela_estoque_resumo = Table(
        estoque_resumo,

        colWidths=[
            80 * mm,
            94 * mm
        ]
    )


    tabela_estoque_resumo.setStyle(
        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor("#DDDDDD")
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor("#F2F2F2")
            ),

            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),

            (
                "ALIGN",
                (1, 0),
                (1, -1),
                "RIGHT"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )


    story.append(
        tabela_estoque_resumo
    )


    # ======================================================
    # DETALHAMENTO DAS SAÍDAS
    # ======================================================

    story.append(
        Paragraph(
            "6. Saídas de estoque no período",
            secao
        )
    )


    tabela_saidas = [[
        "Data",
        "Item",
        "Qtd.",
        "Valor unit.",
        "Total",
        "Contrato"
    ]]


    for saida in saidas:

        tabela_saidas.append([

            saida["data"],

            saida["item"],

            f'{saida["quantidade"]:g} '
            f'{saida["unidade"]}',

            moeda(
                saida["preco"]
            ),

            moeda(
                saida["total"]
            ),

            (
                f'#{saida["contrato"]}'
                if saida["contrato"]
                else "-"
            )
        ])


    if len(tabela_saidas) == 1:

        tabela_saidas.append([
            "-",
            "Nenhuma saída registrada no período",
            "-",
            moeda(0),
            moeda(0),
            "-"
        ])


    tabela_saidas_pdf = Table(
        tabela_saidas,

        colWidths=[
            24 * mm,
            57 * mm,
            27 * mm,
            29 * mm,
            29 * mm,
            25 * mm
        ],

        repeatRows=1
    )


    tabela_saidas_pdf.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#111111")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.35,
                colors.HexColor("#D5D5D5")
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "ALIGN",
                (2, 1),
                (-1, -1),
                "RIGHT"
            ),

            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F8F8F8")
                ]
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )


    story.append(
        tabela_saidas_pdf
    )


    # ======================================================
    # CONCLUSÃO EXECUTIVA
    # ======================================================

    story.append(
        Paragraph(
            "7. Síntese do período",
            secao
        )
    )


    if faturamento > 0:

        texto_sintese = (
            f"No período de {nome_mes} de {ano}, "
            f"o salão registrou "
            f"<b>{qtd_contratos}</b> contrato(s), "
            f"representando um faturamento contratado "
            f"de <b>{moeda(faturamento)}</b>. "
            f"Do total contratado, "
            f"<b>{moeda(recebido)}</b> foram registrados "
            f"como recebidos, correspondendo a "
            f"<b>{percentual_recebido:.1f}%</b> "
            f"do faturamento. "
            f"O saldo atualmente registrado como a receber "
            f"é de <b>{moeda(a_receber)}</b>."
        )

    else:

        texto_sintese = (
            f"Não foram identificados contratos com "
            f"data de evento dentro de {nome_mes} de {ano}."
        )


    story.append(
        Paragraph(
            texto_sintese,
            normal
        )
    )


    story.append(
        Spacer(
            1,
            15
        )
    )


    # ======================================================
    # RODAPÉ
    # ======================================================

    gerado_em = datetime.now().strftime(
        "%d/%m/%Y às %H:%M"
    )


    story.append(
        Paragraph(
            f"Relatório gerado em {gerado_em} "
            f"| SalonConnect",
            ParagraphStyle(
                "RodapeFinanceiro",

                parent=styles["Normal"],

                fontSize=7,

                alignment=TA_CENTER,

                textColor=colors.HexColor(
                    "#888888"
                )
            )
        )
    )


    # ======================================================
    # GERA PDF
    # ======================================================

    doc.build(
        story
    )


    buffer.seek(0)


    nome_salao = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        salao.nome or "Salao"
    )


    return send_file(

        buffer,

        mimetype="application/pdf",

        as_attachment=True,

        download_name=(
            f"Relatorio_Financeiro_"
            f"{nome_salao}_"
            f"{ano}_{numero_mes:02d}.pdf"
        )
    )

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)
