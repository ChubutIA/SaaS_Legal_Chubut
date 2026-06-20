# ==========================================
# PARCHE PARA CHROMADB EN LINUX (RAILWAY)
# ==========================================
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass
from dotenv import load_dotenv
load_dotenv()
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# IMPORTACIONES AJUSTADAS PARA EJECUCIÓN LOCAL
from .services.ai_engine import initialize_ai
from .routers import auth, chat, upload, export, payment

# ==========================================
# LIFESPAN: INICIALIZACIÓN DEL CEREBRO IA
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Inicializando Chubut.IA...")
    await initialize_ai()
    print("✅ Motor jurídico cargado y listo.")
    yield
    print("🛑 Servidor detenido.")

# ==========================================
# INSTANCIA FASTAPI
# ==========================================
app = FastAPI(
    title="Chubut.IA API",
    description="Motor de jurisprudencia para la Provincia de Chubut",
    version="2.0.0",
    lifespan=lifespan,
)

# ==========================================
# CORS
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# ROUTERS
# ==========================================
app.include_router(auth.router,     prefix="/api/auth",    tags=["Autenticación"])
app.include_router(chat.router,     prefix="/api/chat",    tags=["Chat IA"])
app.include_router(upload.router,   prefix="/api/upload",  tags=["Archivos"])
app.include_router(export.router,   prefix="/api/export",  tags=["Exportar"])
app.include_router(payment.router,  prefix="/api/payment", tags=["Pagos"])

# ==========================================
# SERVIR EL FRONTEND
# ==========================================
# Ajustamos la ruta para que desde 'backend' suba un nivel a la raíz y luego baje a 'frontend'
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{full_path:path}", include_in_schema=False)
async def catch_all(full_path: str):
    file_path = os.path.join(FRONTEND_DIR, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
