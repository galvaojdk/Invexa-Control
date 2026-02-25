from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.system import SystemGuide
from app.api.dependencies import get_db, login_required

router = APIRouter(tags=["System Guide"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/api/guide/status")
async def get_guide_status(user: User = Depends(login_required), db: Session = Depends(get_db)):
    guide = db.query(SystemGuide).order_by(SystemGuide.id.desc()).first()
    if not guide:
        return JSONResponse({"version": 0, "has_update": False})
    
    # Check if user needs an update
    has_update = (guide.version > (user.guide_version_viewed or 0))
    return JSONResponse({"version": guide.version, "has_update": has_update})

@router.get("/api/guide/content")
async def get_guide_content(db: Session = Depends(get_db)):
    guide = db.query(SystemGuide).order_by(SystemGuide.id.desc()).first()
    if not guide:
        return {"content": "Nenhum guia disponível no momento.", "version": 0}
    
    return {"content": guide.content, "version": guide.version}

@router.post("/api/guide/mark_read")
async def mark_guide_read(user: User = Depends(login_required), db: Session = Depends(get_db)):
    guide = db.query(SystemGuide).order_by(SystemGuide.id.desc()).first()
    if guide and user:
        user.guide_version_viewed = guide.version
        db.commit()
    return {"status": "ok"}

DEFAULT_GUIDE_CONTENT = """<!-- 1. Cadastros Básicos -->
<div class="space-y-2">
    <h4 class="font-bold text-main flex items-center gap-2">
        <span class="bg-indigo-500/10 text-indigo-500 px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider">Passo 1</span>
        Cadastros Gerais
    </h4>
    <p class="leading-relaxed text-[12px]">
        Em <strong>Cadastros</strong> você registra seus Produtos e os Terceirizados (Facções). 
        Existem produtos <strong>Simples</strong> (matéria-prima/insumos) e <strong>Compostos</strong> (Produto final que possui Ficha Técnica).
    </p>
</div>

<!-- 2. Entradas e Saídas -->
<div class="space-y-2">
    <h4 class="font-bold text-main flex items-center gap-2">
        <span class="bg-sky-500/10 text-sky-500 px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider">Passo 2</span>
        Movimentações (Estoque)
    </h4>
    <p class="leading-relaxed text-[12px]">
        Na tela de <strong>Movimentações</strong> você adiciona produtos novos ao saldo (Entrada) ou retira itens (Saída). 
        Sempre que você despachar uma <strong>Saída em Lote</strong> vinculada ao nome de um <strong>Terceirizado</strong>, o sistema "penhora" esses itens e joga eles lá no balcão de Pendências em Remessas.
    </p>
</div>

<!-- 3. Ordens de Produção -->
<div class="space-y-2">
    <h4 class="font-bold text-main flex items-center gap-2">
        <span class="bg-emerald-500/10 text-emerald-500 px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider">Passo 3</span>
        Gerando uma OP
    </h4>
    <p class="leading-relaxed text-[12px]">
        Decidiu fabricar um produto final composto? Crie uma <strong>Ordem de Produção (OP)</strong> definindo a Meta. Ela começa como Rascunho. 
        Ao fazer uma Saída (Passo 2) de materiais para a Facção e apontar o ID dessa OP no final da saída, ela entra "Em Andamento" e vincula os insumos a ela de forma inteligente.
    </p>
</div>

<!-- 4. Recebimento e Remessas -->
<div class="space-y-2">
    <h4 class="font-bold text-main flex items-center gap-2">
        <span class="bg-blue-500/10 text-blue-500 px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider">Passo 4</span>
        Recebimento Mágico
    </h4>
    <p class="leading-relaxed text-[12px]">
        A facção entregou o lote? Vá em <strong>Remessas > Registrar Produção</strong>. 
        O sistema irá:
    </p>
    <ul class="list-disc pl-4 text-[11px] leading-relaxed space-y-1">
        <li>Dar "Entrada" imediata da calça/produto pronto no seu estoque.</li>
        <li>Baixar automaticamente os botões e tecidos da <strong>Ficha Técnica</strong> na carteira de pendências daquela Facção.</li>
        <li>Preencher a "Barra de Progresso" da OP caso tenha selecionado. Tudo em um botão!</li>
    </ul>
</div>

<!-- 5. Inteligência -->
<div class="space-y-2">
    <h4 class="font-bold text-main flex items-center gap-2">
        <span class="bg-violet-500/10 text-violet-500 px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider">Extra</span>
        Inteligência
    </h4>
    <p class="leading-relaxed text-[12px]">
        Explore o menu <strong>Relatórios</strong> para cruzar e investigar o desperdício das facções usando as informações das remessas ou para gerar planilhas para a contabilidade!
    </p>
</div>"""

@router.get("/admin/guide")
async def admin_edit_guide(request: Request, user: User = Depends(login_required), db: Session = Depends(get_db)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso Restrito")
    guide = db.query(SystemGuide).order_by(SystemGuide.id.desc()).first()
    if not guide: # Create placeholder if missing
        guide = SystemGuide(content=DEFAULT_GUIDE_CONTENT, version=1)
        db.add(guide)
        db.commit()
        db.refresh(guide)
    elif guide.content == "<p>Guia Vazio</p>":
        guide.content = DEFAULT_GUIDE_CONTENT
        db.commit()
        db.refresh(guide)
        
    return templates.TemplateResponse("admin_guide.html", {"request": request, "user": user, "guide": guide})

@router.post("/admin/guide")
async def admin_save_guide(content: str = Form(...), user: User = Depends(login_required), db: Session = Depends(get_db)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso Restrito")
        
    guide = db.query(SystemGuide).order_by(SystemGuide.id.desc()).first()
    if not guide:
        guide = SystemGuide()
        db.add(guide)
        
    guide.content = content
    guide.version += 1 # Upgrade format
    db.commit()
    
    return RedirectResponse(url="/admin/guide", status_code=303)
