import os
from datetime import datetime

import streamlit as st
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Banco Digital",
    page_icon="🏦",
    layout="wide"
)

load_dotenv()

CAMINHO_CREDENCIAL = os.getenv("FIREBASE_CREDENTIALS_PATH")


@st.cache_resource
def conectar_firebase(caminho_credencial):
    if not firebase_admin._apps:
        cred = credentials.Certificate(caminho_credencial)
        firebase_admin.initialize_app(cred)

    return firestore.client()


# Verifica se encontrou o caminho da credencial
if not CAMINHO_CREDENCIAL:
    st.error(
        "Erro: a variável FIREBASE_CREDENTIALS_PATH "
        "não foi encontrada no arquivo .env."
    )
    st.stop()


# Tenta conectar ao Firebase
try:
    db = conectar_firebase(CAMINHO_CREDENCIAL)
except Exception as e:
    st.error(f"Erro ao conectar ao Firebase: {e}")
    st.stop()


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def formatar_reais(valor):
    """Transforma número em formato brasileiro de dinheiro."""
    valor = float(valor or 0)
    texto = f"R$ {valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return texto


def agora():
    """Retorna data e hora atual para o histórico."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def obter_clientes():
    """Busca todos os clientes."""
    return [
        {"id": doc.id, **doc.to_dict()}
        for doc in db.collection("clientes").stream()
    ]


def obter_contas():
    """Busca todas as contas."""
    return [
        {"id": doc.id, **doc.to_dict()}
        for doc in db.collection("contas").stream()
    ]


def obter_dividas():
    """Busca todas as dívidas."""
    return [
        {"id": doc.id, **doc.to_dict()}
        for doc in db.collection("dividas").stream()
    ]


def nome_cliente(cliente_id, clientes):
    """Retorna o nome do cliente através do ID."""
    for cliente in clientes:
        if cliente["id"] == cliente_id:
            return cliente.get("nome", "Cliente não encontrado")
    return "Cliente não encontrado"


def gerar_numero_conta():
    """Gera um número simples para a conta."""
    contas = obter_contas()
    maior = 0

    for conta in contas:
        try:
            numero = int(conta.get("numero", 0))
            if numero > maior:
                maior = numero
        except (ValueError, TypeError):
            pass

    return str(maior + 1).zfill(4)


# ============================================================
# CABEÇALHO
# ============================================================

st.title("🏦 Banco Digital")
st.caption("Sistema acadêmico utilizando Python, Streamlit e Firebase Firestore")
st.success("✅ Firebase conectado com sucesso!")


# ============================================================
# DADOS PARA O SISTEMA
# ============================================================

clientes = obter_clientes()
contas = obter_contas()
dividas = obter_dividas()


# ============================================================
# PAINEL RESUMIDO
# ============================================================

saldo_total = sum(float(conta.get("saldo", 0)) for conta in contas)

divida_total = sum(
    max(
        float(divida.get("valor_total", 0))
        - float(divida.get("valor_pago", 0)),
        0
    )
    for divida in dividas
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("👤 Clientes", len(clientes))

with col2:
    st.metric("💳 Contas", len(contas))

with col3:
    st.metric("💰 Dinheiro nas contas", formatar_reais(saldo_total))

with col4:
    st.metric("💸 Dívidas em aberto", formatar_reais(divida_total))


st.divider()


# ============================================================
# ABAS
# ============================================================

aba_clientes, aba_contas, aba_operacoes, aba_dividas, aba_historico = st.tabs(
    [
        "👤 Clientes",
        "💳 Contas",
        "💰 Operações",
        "💸 Dívidas",
        "📜 Histórico",
    ]
)


# ============================================================
# ABA CLIENTES
# ============================================================

with aba_clientes:
    st.subheader("Cadastrar cliente")

    with st.form("form_cliente", clear_on_submit=True):

        nome = st.text_input("Nome completo")

        cpf = st.text_input(
            "CPF",
            placeholder="000.000.000-00"
        )

        idade = st.number_input(
            "Idade",
            min_value=0,
            max_value=120,
            step=1
        )

        cadastrar_cliente = st.form_submit_button(
            "➕ Cadastrar cliente"
        )

        if cadastrar_cliente:

            if not nome.strip():
                st.warning("Informe o nome do cliente.")

            elif not cpf.strip():
                st.warning("Informe o CPF.")

            else:

                db.collection("clientes").add(
                    {
                        "nome": nome.strip(),
                        "cpf": cpf.strip(),
                        "idade": int(idade),
                        "criado_em": agora(),
                    }
                )

                st.success(
                    f"Cliente '{nome.strip()}' cadastrado com sucesso!"
                )

                st.rerun()


    st.divider()

    st.subheader("Clientes cadastrados")

    clientes_atualizados = obter_clientes()

    if not clientes_atualizados:
        st.info("Nenhum cliente cadastrado ainda.")

    else:

        for cliente in clientes_atualizados:

            col1, col2, col3 = st.columns([4, 2, 1])

            with col1:
                st.write(f"**{cliente.get('nome', '—')}**")

            with col2:
                st.write(
                    f"CPF: {cliente.get('cpf', '—')}"
                )

            with col3:
                st.write(
                    f"{cliente.get('idade', '—')} anos"
                )


# ============================================================
# ABA CONTAS
# ============================================================

with aba_contas:
    st.subheader("Criar conta")

    if not clientes:
        st.warning(
            "Cadastre pelo menos um cliente antes de criar uma conta."
        )

    else:

        opcoes_clientes = {
            f"{cliente.get('nome', 'Sem nome')} | CPF: {cliente.get('cpf', '—')}":
            cliente["id"]
            for cliente in clientes
        }

        with st.form("form_conta", clear_on_submit=True):

            cliente_escolhido = st.selectbox(
                "Cliente",
                list(opcoes_clientes.keys())
            )

            tipo_conta = st.selectbox(
                "Tipo de conta",
                [
                    "Conta corrente",
                    "Conta poupança"
                ]
            )

            saldo_inicial = st.number_input(
                "Saldo inicial (R$)",
                min_value=0.0,
                step=10.0,
                format="%.2f"
            )

            criar_conta = st.form_submit_button(
                "💳 Criar conta"
            )

            if criar_conta:

                cliente_id = opcoes_clientes[cliente_escolhido]

                numero = gerar_numero_conta()

                db.collection("contas").add(
                    {
                        "numero": numero,
                        "cliente_id": cliente_id,
                        "tipo": tipo_conta,
                        "saldo": float(saldo_inicial),
                        "criado_em": agora(),
                    }
                )

                # Registra o saldo inicial no histórico
                if saldo_inicial > 0:

                    db.collection("transacoes").add(
                        {
                            "conta_id": numero,
                            "tipo": "Depósito inicial",
                            "valor": float(saldo_inicial),
                            "data": agora(),
                            "descricao": "Saldo inicial da conta",
                        }
                    )

                st.success(
                    f"Conta {numero} criada com sucesso!"
                )

                st.rerun()


    st.divider()

    st.subheader("Contas cadastradas")

    contas_atualizadas = obter_contas()
    clientes_atualizados = obter_clientes()

    if not contas_atualizadas:
        st.info("Nenhuma conta cadastrada ainda.")

    else:

        for conta in contas_atualizadas:

            cliente = nome_cliente(
                conta.get("cliente_id"),
                clientes_atualizados
            )

            col1, col2, col3, col4 = st.columns([1.5, 2.5, 2, 2])

            with col1:
                st.write(
                    f"**Conta {conta.get('numero', '—')}**"
                )

            with col2:
                st.write(cliente)

            with col3:
                st.write(conta.get("tipo", "—"))

            with col4:
                st.write(
                    f"**{formatar_reais(conta.get('saldo', 0))}**"
                )


# ============================================================
# ABA OPERAÇÕES
# ============================================================

with aba_operacoes:

    st.subheader("Depósito ou saque")

    contas_atualizadas = obter_contas()
    clientes_atualizados = obter_clientes()

    if not contas_atualizadas:

        st.info(
            "Crie uma conta antes de realizar operações."
        )

    else:

        opcoes_contas = {}

        for conta in contas_atualizadas:

            cliente = nome_cliente(
                conta.get("cliente_id"),
                clientes_atualizados
            )

            descricao = (
                f"Conta {conta.get('numero')} - "
                f"{cliente} - "
                f"Saldo: {formatar_reais(conta.get('saldo', 0))}"
            )

            opcoes_contas[descricao] = conta["id"]


        with st.form("form_operacao"):

            conta_escolhida = st.selectbox(
                "Conta",
                list(opcoes_contas.keys())
            )

            tipo_operacao = st.selectbox(
                "Operação",
                [
                    "Depósito",
                    "Saque"
                ]
            )

            valor_operacao = st.number_input(
                "Valor (R$)",
                min_value=0.01,
                step=10.0,
                format="%.2f"
            )

            descricao_operacao = st.text_input(
                "Descrição",
                placeholder="Ex.: salário, compra, saque..."
            )

            realizar_operacao = st.form_submit_button(
                "✅ Realizar operação"
            )

            if realizar_operacao:

                conta_id = opcoes_contas[conta_escolhida]

                referencia_conta = db.collection(
                    "contas"
                ).document(conta_id)

                documento_conta = referencia_conta.get()

                if not documento_conta.exists:

                    st.error("A conta não foi encontrada.")

                else:

                    dados_conta = documento_conta.to_dict()

                    saldo_atual = float(
                        dados_conta.get("saldo", 0)
                    )

                    valor = float(valor_operacao)


                    # ----------------------------------------
                    # DEPÓSITO
                    # ----------------------------------------

                    if tipo_operacao == "Depósito":

                        novo_saldo = saldo_atual + valor

                        referencia_conta.update(
                            {
                                "saldo": novo_saldo
                            }
                        )

                        db.collection("transacoes").add(
                            {
                                "conta_id": dados_conta.get("numero"),
                                "tipo": "Depósito",
                                "valor": valor,
                                "data": agora(),
                                "descricao": (
                                    descricao_operacao.strip()
                                    or "Depósito"
                                ),
                            }
                        )

                        st.success(
                            "Depósito realizado com sucesso! "
                            f"Novo saldo: {formatar_reais(novo_saldo)}"
                        )

                        st.rerun()


                    # ----------------------------------------
                    # SAQUE
                    # ----------------------------------------

                    else:

                        if valor > saldo_atual:

                            st.error(
                                "Saldo insuficiente para realizar o saque."
                            )

                        else:

                            novo_saldo = saldo_atual - valor

                            referencia_conta.update(
                                {
                                    "saldo": novo_saldo
                                }
                            )

                            db.collection("transacoes").add(
                                {
                                    "conta_id": dados_conta.get("numero"),
                                    "tipo": "Saque",
                                    "valor": valor,
                                    "data": agora(),
                                    "descricao": (
                                        descricao_operacao.strip()
                                        or "Saque"
                                    ),
                                }
                            )

                            st.success(
                                "Saque realizado com sucesso! "
                                f"Novo saldo: {formatar_reais(novo_saldo)}"
                            )

                            st.rerun()


# ============================================================
# ABA DÍVIDAS
# ============================================================

with aba_dividas:

    st.subheader("Cadastrar dívida")

    clientes_atualizados = obter_clientes()

    if not clientes_atualizados:

        st.warning(
            "Cadastre um cliente antes de cadastrar uma dívida."
        )

    else:

        opcoes_clientes = {
            cliente.get("nome", "Sem nome"): cliente["id"]
            for cliente in clientes_atualizados
        }

        with st.form("form_divida", clear_on_submit=True):

            cliente_divida = st.selectbox(
                "Cliente",
                list(opcoes_clientes.keys()),
                key="cliente_divida"
            )

            descricao_divida = st.text_input(
                "Descrição da dívida",
                placeholder="Ex.: empréstimo, compra..."
            )

            valor_divida = st.number_input(
                "Valor total da dívida (R$)",
                min_value=0.01,
                step=10.0,
                format="%.2f"
            )

            cadastrar_divida = st.form_submit_button(
                "💸 Cadastrar dívida"
            )

            if cadastrar_divida:

                if not descricao_divida.strip():

                    st.warning(
                        "Informe a descrição da dívida."
                    )

                else:

                    db.collection("dividas").add(
                        {
                            "cliente_id": opcoes_clientes[cliente_divida],
                            "descricao": descricao_divida.strip(),
                            "valor_total": float(valor_divida),
                            "valor_pago": 0.0,
                            "criada_em": agora(),
                        }
                    )

                    st.success(
                        "Dívida cadastrada com sucesso!"
                    )

                    st.rerun()


    st.divider()

    # ========================================================
    # PAGAMENTO DE DÍVIDA
    # ========================================================

    st.subheader("Pagar dívida")

    dividas_atualizadas = obter_dividas()
    contas_atualizadas = obter_contas()
    clientes_atualizados = obter_clientes()

    dividas_abertas = []

    for divida in dividas_atualizadas:

        total = float(
            divida.get("valor_total", 0)
        )

        pago = float(
            divida.get("valor_pago", 0)
        )

        restante = max(total - pago, 0)

        if restante > 0:

            cliente = nome_cliente(
                divida.get("cliente_id"),
                clientes_atualizados
            )

            dividas_abertas.append(
                (
                    f"{cliente} - "
                    f"{divida.get('descricao', 'Dívida')} - "
                    f"Restante: {formatar_reais(restante)}",
                    divida,
                    restante
                )
            )


    if not dividas_abertas:

        st.info("Nenhuma dívida em aberto.")

    elif not contas_atualizadas:

        st.warning(
            "É necessário ter uma conta para pagar uma dívida."
        )

    else:

        opcoes_dividas = {
            item[0]: item[1]["id"]
            for item in dividas_abertas
        }

        opcoes_contas_pagamento = {}

        for conta in contas_atualizadas:

            cliente = nome_cliente(
                conta.get("cliente_id"),
                clientes_atualizados
            )

            texto = (
                f"Conta {conta.get('numero')} - "
                f"{cliente} - "
                f"Saldo: {formatar_reais(conta.get('saldo', 0))}"
            )

            opcoes_contas_pagamento[texto] = conta["id"]


        with st.form("form_pagamento_divida"):

            divida_escolhida = st.selectbox(
                "Dívida",
                list(opcoes_dividas.keys())
            )

            conta_pagamento = st.selectbox(
                "Conta usada para pagar",
                list(opcoes_contas_pagamento.keys())
            )

            valor_pagamento = st.number_input(
                "Valor do pagamento (R$)",
                min_value=0.01,
                step=10.0,
                format="%.2f"
            )

            pagar_divida = st.form_submit_button(
                "💵 Pagar dívida"
            )

            if pagar_divida:

                divida_id = opcoes_dividas[divida_escolhida]
                conta_id = opcoes_contas_pagamento[conta_pagamento]

                referencia_divida = db.collection(
                    "dividas"
                ).document(divida_id)

                referencia_conta = db.collection(
                    "contas"
                ).document(conta_id)

                documento_divida = referencia_divida.get()
                documento_conta = referencia_conta.get()

                if not documento_divida.exists:

                    st.error("Dívida não encontrada.")

                elif not documento_conta.exists:

                    st.error("Conta não encontrada.")

                else:

                    dados_divida = documento_divida.to_dict()
                    dados_conta = documento_conta.to_dict()

                    total_divida = float(
                        dados_divida.get("valor_total", 0)
                    )

                    pago_atual = float(
                        dados_divida.get("valor_pago", 0)
                    )

                    restante = total_divida - pago_atual

                    saldo_conta = float(
                        dados_conta.get("saldo", 0)
                    )

                    valor = float(valor_pagamento)

                    if valor > restante:

                        st.error(
                            "O pagamento não pode ser maior que "
                            "o valor restante da dívida."
                        )

                    elif valor > saldo_conta:

                        st.error(
                            "Saldo insuficiente nessa conta."
                        )

                    else:

                        novo_pago = pago_atual + valor
                        novo_saldo = saldo_conta - valor

                        referencia_divida.update(
                            {
                                "valor_pago": novo_pago
                            }
                        )

                        referencia_conta.update(
                            {
                                "saldo": novo_saldo
                            }
                        )

                        db.collection("transacoes").add(
                            {
                                "conta_id": dados_conta.get("numero"),
                                "tipo": "Pagamento de dívida",
                                "valor": valor,
                                "data": agora(),
                                "descricao": dados_divida.get(
                                    "descricao",
                                    "Pagamento de dívida"
                                ),
                            }
                        )

                        st.success(
                            "Pagamento realizado com sucesso!"
                        )

                        st.rerun()


    st.divider()

    st.subheader("Dívidas cadastradas")

    dividas_atualizadas = obter_dividas()
    clientes_atualizados = obter_clientes()

    if not dividas_atualizadas:

        st.info("Nenhuma dívida cadastrada.")

    else:

        for divida in dividas_atualizadas:

            cliente = nome_cliente(
                divida.get("cliente_id"),
                clientes_atualizados
            )

            total = float(
                divida.get("valor_total", 0)
            )

            pago = float(
                divida.get("valor_pago", 0)
            )

            restante = max(total - pago, 0)

            col1, col2, col3, col4 = st.columns(
                [2, 3, 2, 2]
            )

            with col1:
                st.write(f"**{cliente}**")

            with col2:
                st.write(
                    divida.get("descricao", "—")
                )

            with col3:
                st.write(
                    f"Pago: {formatar_reais(pago)}"
                )

            with col4:
                if restante == 0:
                    st.success("✅ Quitada")
                else:
                    st.warning(
                        f"Falta: {formatar_reais(restante)}"
                    )


# ============================================================
# ABA HISTÓRICO
# ============================================================

with aba_historico:

    st.subheader("Histórico de operações")

    contas_atualizadas = obter_contas()

    opcoes_filtro = {
        "Todas as contas": None
    }

    for conta in contas_atualizadas:

        opcoes_filtro[
            f"Conta {conta.get('numero', '—')}"
        ] = conta.get("numero")


    filtro = st.selectbox(
        "Filtrar por conta",
        list(opcoes_filtro.keys())
    )

    filtro_conta = opcoes_filtro[filtro]

    transacoes = [
        {"id": doc.id, **doc.to_dict()}
        for doc in db.collection("transacoes").stream()
    ]

    if filtro_conta is not None:

        transacoes = [
            transacao
            for transacao in transacoes
            if transacao.get("conta_id") == filtro_conta
        ]


    transacoes.sort(
        key=lambda x: x.get("data", ""),
        reverse=True
    )


    if not transacoes:

        st.info("Nenhuma transação encontrada.")

    else:

        for transacao in transacoes:

            tipo = transacao.get("tipo", "—")
            valor = float(transacao.get("valor", 0))
            data = transacao.get("data", "—")
            descricao = transacao.get("descricao", "—")
            conta = transacao.get("conta_id", "—")

            col1, col2, col3, col4 = st.columns(
                [2, 2, 3, 2]
            )

            with col1:
                st.write(f"**{tipo}**")

            with col2:
                st.write(formatar_reais(valor))

            with col3:
                st.write(descricao)

            with col4:
                st.write(f"Conta {conta}")
                st.caption(data)