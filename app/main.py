from fastapi import FastAPI, Form, Depends, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fpdf import FPDF
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import bcrypt
from datetime import datetime, timedelta
from jose import jwt, JWTError
import os

# ====================== CONFIGURAÇÕES ======================
SECRET_KEY = "geradoc-chave-secreta-troque-depois-123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

app = FastAPI(title="GeraDoc")

PDF_FOLDER = "app/pdf"
os.makedirs(PDF_FOLDER, exist_ok=True)

SQLALCHEMY_DATABASE_URL = "sqlite:///./geradoc.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ====================== MODELO DE USUÁRIO ======================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    plano = Column(String, default="gratis")
    documentos_gerados = Column(Integer, default=0)
    criado_em = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)


# ====================== FUNÇÕES AUXILIARES ======================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verificar_senha(senha_plana, senha_hash):
    return bcrypt.checkpw(senha_plana.encode('utf-8'), senha_hash.encode('utf-8'))

def gerar_hash(senha):
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def criar_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            return None
        return get_user_by_email(db, email)
    except JWTError:
        return None


# ====================== ESTILO ======================
estilo = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
    body { background-color: #f0f2f5; color: #333; min-height: 100vh; }
    .container { max-width: 620px; margin: 40px auto; padding: 0 20px; }
    .card { background: white; border-radius: 12px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
    h1 { font-size: 26px; color: #1a1a1a; margin-bottom: 6px; text-align: center; }
    .subtitle { text-align: center; color: #666; margin-bottom: 28px; font-size: 14px; }
    .btn { display: block; width: 100%; background: #2563eb; color: white; border: none; padding: 14px; font-size: 16px; font-weight: 600; border-radius: 8px; cursor: pointer; text-decoration: none; text-align: center; margin-bottom: 12px; }
    .btn:hover { background: #1d4ed8; }
    .btn-secondary { background: #e5e7eb; color: #333; }
    .btn-secondary:hover { background: #d1d5db; }
    .btn-outline { background: white; color: #2563eb; border: 2px solid #2563eb; }
    .btn:disabled { background: #93c5fd; cursor: not-allowed; }
    label { display: block; margin-bottom: 5px; font-weight: 500; font-size: 14px; color: #374151; }
    input, textarea, select { width: 100%; padding: 11px 13px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 15px; margin-bottom: 16px; }
    input:focus, textarea:focus, select:focus { outline: none; border-color: #2563eb; }
    textarea { resize: vertical; min-height: 85px; }
    .logo { text-align: center; font-size: 30px; font-weight: 700; color: #2563eb; margin-bottom: 8px; }
    .footer { text-align: center; margin-top: 25px; color: #9ca3af; font-size: 13px; }
    .section-title { font-size: 13px; font-weight: 600; color: #6b7280; margin-bottom: 12px; margin-top: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
    .erro { background: #fef2f2; color: #b91c1c; padding: 12px; border-radius: 8px; margin-bottom: 16px; text-align: center; font-size: 14px; }
    .sucesso { background: #f0fdf4; color: #15803d; padding: 12px; border-radius: 8px; margin-bottom: 16px; text-align: center; font-size: 14px; }
    .links { text-align: center; margin-top: 16px; font-size: 14px; }
    .links a { color: #2563eb; text-decoration: none; }
    .user-info { text-align: center; margin-bottom: 20px; padding: 12px; background: #f0fdf4; border-radius: 8px; color: #15803d; font-size: 14px; }
    .ad-box { background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 40px 20px; text-align: center; margin: 25px 0; color: #64748b; }
    .ad-box strong { display: block; font-size: 18px; margin-bottom: 8px; color: #334155; }
    .countdown { font-size: 28px; font-weight: 700; color: #2563eb; margin: 15px 0; }
    .planos { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 30px; }
    @media (max-width: 600px) { .planos { grid-template-columns: 1fr; } }
    .plano { border: 2px solid #e5e7eb; border-radius: 12px; padding: 28px 22px; text-align: center; }
    .plano.destaque { border-color: #2563eb; background: #f8fafc; }
    .plano h2 { font-size: 20px; margin-bottom: 8px; }
    .preco { font-size: 32px; font-weight: 700; color: #2563eb; margin: 12px 0; }
    .preco span { font-size: 14px; font-weight: 400; color: #6b7280; }
    .beneficios { text-align: left; margin: 20px 0; font-size: 14px; color: #374151; }
    .beneficios li { margin-bottom: 8px; list-style: none; padding-left: 4px; }
    .beneficios li::before { content: "✓ "; color: #16a34a; font-weight: bold; }
</style>
"""


# ====================== CADASTRO ======================
@app.get("/cadastro", response_class=HTMLResponse)
async def pagina_cadastro():
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Cadastro - GeraDoc</title>{estilo}</head>
    <body>
        <div class="container"><div class="card">
            <div class="logo">GeraDoc</div>
            <h1>Criar Conta</h1>
            <p class="subtitle">Comece a gerar documentos profissionais</p>
            <form action="/cadastro" method="post">
                <label>Seu Nome</label>
                <input type="text" name="nome" placeholder="Ex: João Silva" required>
                <label>E-mail</label>
                <input type="email" name="email" placeholder="seu@email.com" required>
                <label>Senha</label>
                <input type="password" name="senha" placeholder="Mínimo 6 caracteres" required>
                <button type="submit" class="btn">Criar Conta</button>
            </form>
            <div class="links">Já tem conta? <a href="/login">Fazer Login</a></div>
        </div></div>
    </body></html>
    """)


@app.post("/cadastro")
async def cadastrar(nome: str = Form(...), email: str = Form(...), senha: str = Form(...), db: Session = Depends(get_db)):
    if get_user_by_email(db, email.lower().strip()):
        return HTMLResponse(f"""
        <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><title>Erro</title>{estilo}</head>
        <body><div class="container"><div class="card">
            <div class="erro">Este e-mail já está cadastrado.</div>
            <a href="/cadastro" class="btn">Tentar novamente</a>
            <a href="/login" class="btn btn-secondary">Fazer Login</a>
        </div></div></body></html>
        """)
    if len(senha) < 6:
        return HTMLResponse(f"""
        <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><title>Erro</title>{estilo}</head>
        <body><div class="container"><div class="card">
            <div class="erro">A senha deve ter no mínimo 6 caracteres.</div>
            <a href="/cadastro" class="btn">Tentar novamente</a>
        </div></div></body></html>
        """)
    novo_usuario = User(nome=nome, email=email.lower().strip(), senha_hash=gerar_hash(senha))
    db.add(novo_usuario)
    db.commit()
    return RedirectResponse(url="/login?cadastro=ok", status_code=303)


# ====================== LOGIN ======================
@app.get("/login", response_class=HTMLResponse)
async def pagina_login(cadastro: str = None):
    mensagem = '<div class="sucesso">Conta criada com sucesso! Faça login.</div>' if cadastro == "ok" else ""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Login - GeraDoc</title>{estilo}</head>
    <body>
        <div class="container"><div class="card">
            <div class="logo">GeraDoc</div>
            <h1>Entrar</h1>
            <p class="subtitle">Acesse sua conta</p>
            {mensagem}
            <form action="/login" method="post">
                <label>E-mail</label>
                <input type="email" name="email" placeholder="seu@email.com" required>
                <label>Senha</label>
                <input type="password" name="senha" placeholder="Sua senha" required>
                <button type="submit" class="btn">Entrar</button>
            </form>
            <div class="links">Não tem conta? <a href="/cadastro">Criar conta</a></div>
        </div></div>
    </body></html>
    """)


@app.post("/login")
async def fazer_login(email: str = Form(...), senha: str = Form(...), db: Session = Depends(get_db)):
    user = get_user_by_email(db, email.lower().strip())
    if not user or not verificar_senha(senha, user.senha_hash):
        return HTMLResponse(f"""
        <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><title>Erro</title>{estilo}</head>
        <body><div class="container"><div class="card">
            <div class="erro">E-mail ou senha incorretos.</div>
            <a href="/login" class="btn">Tentar novamente</a>
        </div></div></body></html>
        """)
    token = criar_token({"sub": user.email})
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.set_cookie(key="access_token", value=token, httponly=True, max_age=60*60*24*7, samesite="lax")
    return redirect


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response


# ====================== PÁGINA INICIAL ======================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        plano_texto = "Premium" if user.plano == "pago" else "Grátis"
        botoes_auth = f'''
            <div class="user-info">
                Olá, <strong>{user.nome}</strong>! &nbsp;|&nbsp; 
                Plano: <strong>{plano_texto}</strong>
                &nbsp;|&nbsp; <a href="/logout" style="color:#dc2626;">Sair</a>
            </div>
        '''
    else:
        botoes_auth = '''
            <a href="/login" class="btn btn-outline">Fazer Login</a>
            <a href="/cadastro" class="btn btn-secondary">Criar Conta</a>
        '''

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>GeraDoc</title>{estilo}</head>
    <body>
        <div class="container"><div class="card">
            <div class="logo">GeraDoc</div>
            <h1>Gerador de Documentos</h1>
            <p class="subtitle">Crie orçamentos, recibos e propostas profissionais em segundos</p>
            {botoes_auth}
            <a href="/orcamento" class="btn">Gerar Orçamento</a>
            <a href="/recibo" class="btn">Gerar Recibo</a>
            <a href="/proposta" class="btn">Gerar Proposta Comercial</a>
            <a href="/ordem" class="btn">Gerar Ordem de Serviço</a>
            <a href="/planos" class="btn btn-outline">Ver Planos</a>
        </div>
        <p class="footer">© 2026 GeraDoc</p>
        </div>
    </body></html>
    """)


# ====================== PÁGINA DE PLANOS ======================
@app.get("/planos", response_class=HTMLResponse)
async def pagina_planos(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    user_info = ""
    if user:
        plano_atual = "Premium" if user.plano == "pago" else "Grátis"
        user_info = f'''
            <div class="user-info">
                Olá, <strong>{user.nome}</strong>! &nbsp;|&nbsp; 
                Plano atual: <strong>{plano_atual}</strong>
                &nbsp;|&nbsp; <a href="/logout" style="color:#dc2626;">Sair</a>
            </div>
        '''

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Planos - GeraDoc</title>
        {estilo}
    </head>
    <body>
        <div class="container">
            <div class="card">
                <div class="logo">GeraDoc</div>
                <h1>Escolha seu plano</h1>
                <p class="subtitle">Use grátis com anúncios ou remova os anúncios com o Premium</p>

                {user_info}

                <div class="planos">
                    <div class="plano">
                        <h2>Grátis</h2>
                        <div class="preco">R$ 0 <span>/mês</span></div>
                        <ul class="beneficios">
                            <li>Todos os documentos</li>
                            <li>Geração ilimitada</li>
                            <li>Anúncio antes do download</li>
                            <li>Ideal para uso ocasional</li>
                        </ul>
                        <a href="/" class="btn btn-secondary">Continuar grátis</a>
                    </div>

                    <div class="plano destaque">
                        <h2>Premium</h2>
                        <div class="preco">R$ 23,99 <span>/mês</span></div>
                        <ul class="beneficios">
                            <li>Todos os documentos</li>
                            <li>Geração ilimitada</li>
                            <li><strong>Sem anúncios</strong></li>
                            <li>Download direto e rápido</li>
                            <li>Suporte prioritário</li>
                        </ul>
                        <a href="#" class="btn">Em breve</a>
                    </div>
                </div>

                <a href="/" class="btn btn-secondary" style="margin-top: 25px;">← Voltar</a>
            </div>
        </div>
    </body>
    </html>
    """)


# ====================== TELA DE ANÚNCIO ======================
@app.get("/liberar-download", response_class=HTMLResponse)
async def liberar_download(arquivo: str, request: Request, db: Session = Depends(get_db)):
    if ".." in arquivo or "/" in arquivo or "\\" in arquivo:
        return HTMLResponse("<h1>Arquivo inválido</h1>")

    user = get_current_user(request, db)

    # Se for Premium, baixa direto sem anúncio
    if user and user.plano == "pago":
        return RedirectResponse(url=f"/download/{arquivo}", status_code=303)

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Liberar Download - GeraDoc</title>
        {estilo}
    </head>
    <body>
        <div class="container">
            <div class="card">
                <div class="logo">GeraDoc</div>
                <h1>Seu documento está pronto!</h1>
                <p class="subtitle">Assista ao anúncio para liberar o download</p>

                <div class="ad-box">
                    <strong>Espaço de Anúncio</strong>
                    <p>Aqui entrará o anúncio real no futuro<br>(Google AdSense ou similar)</p>
                    <div class="countdown" id="contador">5</div>
                    <p id="texto">Aguarde para liberar o download...</p>
                </div>

                <a href="/download/{arquivo}" class="btn" id="btn-download" style="display:none;">
                    Baixar PDF
                </a>

                <a href="/planos" class="btn btn-outline">Quero Premium (sem anúncio)</a>
                <a href="/" class="btn btn-secondary">Voltar ao início</a>
            </div>
        </div>

        <script>
            let segundos = 5;
            const contador = document.getElementById('contador');
            const texto = document.getElementById('texto');
            const botao = document.getElementById('btn-download');

            const timer = setInterval(() => {{
                segundos--;
                contador.innerText = segundos;
                if (segundos <= 0) {{
                    clearInterval(timer);
                    contador.style.display = 'none';
                    texto.innerText = 'Anúncio concluído! Você já pode baixar.';
                    botao.style.display = 'block';
                }}
            }}, 1000);
        </script>
    </body>
    </html>
    """)


@app.get("/download/{nome_arquivo}")
async def download_arquivo(nome_arquivo: str):
    caminho = os.path.join(PDF_FOLDER, nome_arquivo)
    if not os.path.exists(caminho):
        return HTMLResponse("<h1>Arquivo não encontrado</h1>")
    return FileResponse(caminho, media_type="application/pdf", filename=nome_arquivo)


# ====================== FORMULÁRIOS ======================
@app.get("/orcamento", response_class=HTMLResponse)
async def formulario_orcamento():
    return HTMLResponse(f"""
    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Orçamento - GeraDoc</title>{estilo}</head>
    <body><div class="container"><div class="card">
        <div class="logo">GeraDoc</div><h1>Novo Orçamento</h1><p class="subtitle">Preencha os dados abaixo</p>
        <form action="/gerar-orcamento" method="post">
            <div class="section-title">Dados da sua empresa</div>
            <label>Nome da Empresa / Prestador</label><input type="text" name="empresa" placeholder="Ex: Marcenaria Silva" required>
            <div class="section-title">Dados do cliente</div>
            <label>Nome do Cliente</label><input type="text" name="nome_cliente" placeholder="Ex: João Silva" required>
            <label>Telefone</label><input type="text" name="telefone" placeholder="Ex: (11) 99999-9999" required>
            <div class="section-title">Detalhes do orçamento</div>
            <label>Descrição dos Serviços</label><textarea name="descricao" placeholder="Descreva os serviços..." required></textarea>
            <label>Valor Total (R$)</label><input type="number" step="0.01" name="valor" placeholder="Ex: 3500.00" required>
            <label>Validade</label><input type="text" name="validade" placeholder="Ex: 10 dias" required>
            <button type="submit" class="btn">Gerar PDF</button>
        </form>
        <a href="/" class="btn btn-secondary">← Voltar</a>
    </div></div></body></html>
    """)


@app.get("/recibo", response_class=HTMLResponse)
async def formulario_recibo():
    return HTMLResponse(f"""
    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Recibo - GeraDoc</title>{estilo}</head>
    <body><div class="container"><div class="card">
        <div class="logo">GeraDoc</div><h1>Novo Recibo</h1><p class="subtitle">Preencha os dados abaixo</p>
        <form action="/gerar-recibo" method="post">
            <div class="section-title">Dados da sua empresa</div>
            <label>Nome da Empresa / Prestador</label><input type="text" name="empresa" placeholder="Ex: Marcenaria Silva" required>
            <div class="section-title">Dados do pagamento</div>
            <label>Recebido de (Nome)</label><input type="text" name="nome" placeholder="Ex: João Silva" required>
            <label>Valor (R$)</label><input type="number" step="0.01" name="valor" placeholder="Ex: 1500.00" required>
            <label>Referente a</label><textarea name="referente" placeholder="Ex: Pagamento de serviços" required></textarea>
            <label>Forma de Pagamento</label>
            <select name="forma_pagamento" required>
                <option value="Dinheiro">Dinheiro</option><option value="PIX">PIX</option>
                <option value="Cartão de Crédito">Cartão de Crédito</option><option value="Cartão de Débito">Cartão de Débito</option>
                <option value="Transferência">Transferência</option><option value="Boleto">Boleto</option>
            </select>
            <button type="submit" class="btn">Gerar PDF</button>
        </form>
        <a href="/" class="btn btn-secondary">← Voltar</a>
    </div></div></body></html>
    """)


@app.get("/proposta", response_class=HTMLResponse)
async def formulario_proposta():
    return HTMLResponse(f"""
    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Proposta Comercial - GeraDoc</title>{estilo}</head>
    <body><div class="container"><div class="card">
        <div class="logo">GeraDoc</div><h1>Nova Proposta Comercial</h1><p class="subtitle">Preencha os dados abaixo</p>
        <form action="/gerar-proposta" method="post">
            <div class="section-title">Dados da sua empresa</div>
            <label>Nome da Empresa / Prestador</label><input type="text" name="empresa" placeholder="Ex: Marcenaria Silva" required>
            <div class="section-title">Dados do cliente</div>
            <label>Nome do Cliente</label><input type="text" name="nome_cliente" placeholder="Ex: Empresa XYZ Ltda" required>
            <label>Telefone / E-mail</label><input type="text" name="contato" placeholder="Ex: (11) 99999-9999" required>
            <div class="section-title">Detalhes da proposta</div>
            <label>Descrição da Proposta</label><textarea name="descricao" placeholder="Descreva os serviços ou produtos..." required></textarea>
            <label>Valor Total (R$)</label><input type="number" step="0.01" name="valor" placeholder="Ex: 8500.00" required>
            <label>Condições de Pagamento</label><input type="text" name="pagamento" placeholder="Ex: 50% na assinatura + 50% na entrega" required>
            <label>Prazo de Entrega / Execução</label><input type="text" name="prazo" placeholder="Ex: 15 dias úteis" required>
            <label>Validade da Proposta</label><input type="text" name="validade" placeholder="Ex: 7 dias" required>
            <button type="submit" class="btn">Gerar PDF</button>
        </form>
        <a href="/" class="btn btn-secondary">← Voltar</a>
    </div></div></body></html>
    """)


@app.get("/ordem", response_class=HTMLResponse)
async def formulario_ordem():
    return HTMLResponse(f"""
    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Ordem de Serviço - GeraDoc</title>{estilo}</head>
    <body><div class="container"><div class="card">
        <div class="logo">GeraDoc</div><h1>Nova Ordem de Serviço</h1><p class="subtitle">Preencha os dados abaixo</p>
        <form action="/gerar-ordem" method="post">
            <div class="section-title">Dados da sua empresa</div>
            <label>Nome da Empresa / Prestador</label><input type="text" name="empresa" placeholder="Ex: Marcenaria Silva" required>
            <div class="section-title">Dados do cliente</div>
            <label>Nome do Cliente</label><input type="text" name="nome_cliente" placeholder="Ex: João Silva" required>
            <label>Telefone</label><input type="text" name="telefone" placeholder="Ex: (11) 99999-9999" required>
            <label>Endereço do Serviço</label><input type="text" name="endereco" placeholder="Ex: Rua das Flores, 123" required>
            <div class="section-title">Detalhes do serviço</div>
            <label>Descrição do Serviço</label><textarea name="descricao" placeholder="Descreva o que será feito..." required></textarea>
            <label>Data de Início</label><input type="text" name="data_inicio" placeholder="Ex: 05/10/2026" required>
            <label>Prazo de Conclusão</label><input type="text" name="prazo" placeholder="Ex: 10 dias úteis" required>
            <label>Valor (R$)</label><input type="number" step="0.01" name="valor" placeholder="Ex: 2800.00" required>
            <button type="submit" class="btn">Gerar PDF</button>
        </form>
        <a href="/" class="btn btn-secondary">← Voltar</a>
    </div></div></body></html>
    """)


# ====================== GERADORES DE PDF ======================
@app.post("/gerar-orcamento")
async def gerar_orcamento(
    empresa: str = Form(...),
    nome_cliente: str = Form(...),
    telefone: str = Form(...),
    descricao: str = Form(...),
    valor: float = Form(...),
    validade: str = Form(...)
):
    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    data = datetime.now().strftime("%d/%m/%Y")
    numero = datetime.now().strftime("%Y%m%d%H%M")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 10, empresa.upper(), ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "ORÇAMENTO", ln=True, align="C")
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.8)
    pdf.line(25, pdf.get_y(), 185, pdf.get_y())
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(95, 7, f"Nº {numero}", ln=False)
    pdf.cell(0, 7, f"Data: {data}", ln=True, align="R")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, "CLIENTE", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, nome_cliente, ln=True)
    pdf.cell(0, 7, f"Telefone: {telefone}", ln=True)
    pdf.ln(7)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "DESCRIÇÃO DOS SERVIÇOS", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, descricao)
    pdf.ln(8)
    pdf.set_fill_color(240, 245, 255)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 11, f"  Valor Total: {valor_formatado}", ln=True, fill=True)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Validade deste orçamento: {validade}", ln=True)
    pdf.ln(25)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "Documento gerado pelo GeraDoc", ln=True, align="C")

    nome_arquivo = f"orcamento_{numero}.pdf"
    caminho_pdf = os.path.join(PDF_FOLDER, nome_arquivo)
    pdf.output(caminho_pdf)
    return RedirectResponse(url=f"/liberar-download?arquivo={nome_arquivo}", status_code=303)


@app.post("/gerar-recibo")
async def gerar_recibo(
    empresa: str = Form(...),
    nome: str = Form(...),
    valor: float = Form(...),
    referente: str = Form(...),
    forma_pagamento: str = Form(...)
):
    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    data = datetime.now().strftime("%d/%m/%Y")
    numero = datetime.now().strftime("%Y%m%d%H%M")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 10, empresa.upper(), ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "RECIBO", ln=True, align="C")
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.8)
    pdf.line(25, pdf.get_y(), 185, pdf.get_y())
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 8, f"Recebi de {nome} a quantia de {valor_formatado}, referente a {referente}.")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Forma de pagamento: {forma_pagamento}", ln=True)
    pdf.cell(0, 8, f"Data: {data}", ln=True)
    pdf.cell(0, 8, f"Número do recibo: {numero}", ln=True)
    pdf.ln(28)
    pdf.set_draw_color(120, 120, 120)
    pdf.line(55, pdf.get_y(), 155, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, "Assinatura", ln=True, align="C")
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "Documento gerado pelo GeraDoc", ln=True, align="C")

    nome_arquivo = f"recibo_{numero}.pdf"
    caminho_pdf = os.path.join(PDF_FOLDER, nome_arquivo)
    pdf.output(caminho_pdf)
    return RedirectResponse(url=f"/liberar-download?arquivo={nome_arquivo}", status_code=303)


@app.post("/gerar-proposta")
async def gerar_proposta(
    empresa: str = Form(...),
    nome_cliente: str = Form(...),
    contato: str = Form(...),
    descricao: str = Form(...),
    valor: float = Form(...),
    pagamento: str = Form(...),
    prazo: str = Form(...),
    validade: str = Form(...)
):
    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    data = datetime.now().strftime("%d/%m/%Y")
    numero = datetime.now().strftime("%Y%m%d%H%M")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 10, empresa.upper(), ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 11, "PROPOSTA COMERCIAL", ln=True, align="C")
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.8)
    pdf.line(25, pdf.get_y(), 185, pdf.get_y())
    pdf.ln(9)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(95, 7, f"Proposta Nº {numero}", ln=False)
    pdf.cell(0, 7, f"Data: {data}", ln=True, align="R")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, "CLIENTE", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, nome_cliente, ln=True)
    pdf.cell(0, 7, f"Contato: {contato}", ln=True)
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "DESCRIÇÃO DA PROPOSTA", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, descricao)
    pdf.ln(6)
    pdf.set_fill_color(240, 245, 255)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 11, f"  Valor Total: {valor_formatado}", ln=True, fill=True)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "CONDIÇÕES", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Pagamento: {pagamento}", ln=True)
    pdf.cell(0, 7, f"Prazo: {prazo}", ln=True)
    pdf.cell(0, 7, f"Validade: {validade}", ln=True)
    pdf.ln(16)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "ACEITE DA PROPOSTA", ln=True)
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, "_______________________________", ln=False)
    pdf.cell(0, 6, "_______________________________", ln=True)
    pdf.cell(95, 5, "Assinatura do Cliente", ln=False)
    pdf.cell(0, 5, "Assinatura do Prestador", ln=True)
    pdf.ln(18)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "Documento gerado pelo GeraDoc", ln=True, align="C")

    nome_arquivo = f"proposta_{numero}.pdf"
    caminho_pdf = os.path.join(PDF_FOLDER, nome_arquivo)
    pdf.output(caminho_pdf)
    return RedirectResponse(url=f"/liberar-download?arquivo={nome_arquivo}", status_code=303)


@app.post("/gerar-ordem")
async def gerar_ordem(
    empresa: str = Form(...),
    nome_cliente: str = Form(...),
    telefone: str = Form(...),
    endereco: str = Form(...),
    descricao: str = Form(...),
    data_inicio: str = Form(...),
    prazo: str = Form(...),
    valor: float = Form(...)
):
    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    data = datetime.now().strftime("%d/%m/%Y")
    numero = datetime.now().strftime("%Y%m%d%H%M")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 10, empresa.upper(), ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 11, "ORDEM DE SERVIÇO", ln=True, align="C")
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.8)
    pdf.line(25, pdf.get_y(), 185, pdf.get_y())
    pdf.ln(9)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(95, 7, f"OS Nº {numero}", ln=False)
    pdf.cell(0, 7, f"Data: {data}", ln=True, align="R")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, "CLIENTE", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, nome_cliente, ln=True)
    pdf.cell(0, 7, f"Telefone: {telefone}", ln=True)
    pdf.cell(0, 7, f"Endereço: {endereco}", ln=True)
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "DESCRIÇÃO DO SERVIÇO", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, descricao)
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "PRAZOS", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Data de início: {data_inicio}", ln=True)
    pdf.cell(0, 7, f"Prazo de conclusão: {prazo}", ln=True)
    pdf.ln(6)
    pdf.set_fill_color(240, 245, 255)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 11, f"  Valor: {valor_formatado}", ln=True, fill=True)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(16)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "AUTORIZAÇÃO", ln=True)
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, "_______________________________", ln=False)
    pdf.cell(0, 6, "_______________________________", ln=True)
    pdf.cell(95, 5, "Assinatura do Cliente", ln=False)
    pdf.cell(0, 5, "Assinatura do Prestador", ln=True)
    pdf.ln(18)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "Documento gerado pelo GeraDoc", ln=True, align="C")

    nome_arquivo = f"ordem_servico_{numero}.pdf"
    caminho_pdf = os.path.join(PDF_FOLDER, nome_arquivo)
    pdf.output(caminho_pdf)
    return RedirectResponse(url=f"/liberar-download?arquivo={nome_arquivo}", status_code=303)