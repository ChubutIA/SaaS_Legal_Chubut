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
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# IMPORTACIONES AJUSTADAS
from services.ai_engine import initialize_ai
# CORRECCIÓN: Eliminamos "payment" (singular) que estaba rompiendo el servidor
from routers import auth, chat, upload, export, payments
from routers import liquidaciones
from routers import admin_scraper
from routers import plazos # <-- Agregá esto arriba
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
    description="Motor de jurisprudencia y legislatura para la Provincia de Chubut",
    version="2.0.0",
    lifespan=lifespan,
)

# ==========================================
# RATE LIMITING
# ==========================================
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from services.rate_limiter import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
app.include_router(auth.router,     prefix="/api/auth",     tags=["Autenticación"])
app.include_router(chat.router,     prefix="/api/chat",     tags=["Chat IA"])
app.include_router(upload.router,   prefix="/api/upload",   tags=["Archivos"])
app.include_router(export.router,   prefix="/api/export",   tags=["Exportar"])
# CORRECCIÓN: Dejamos únicamente el router correcto en plural
app.include_router(payments.router, prefix="/api/payments", tags=["Pagos"])
app.include_router(liquidaciones.router)
app.include_router(admin_scraper.router)
app.include_router(plazos.router)
# ==========================================
# SERVIR EL FRONTEND
# ==========================================
# Esto busca la carpeta 'frontend' que está un nivel arriba de 'backend'
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

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

# ==========================================
# EJECUCIÓN (RAILWAY FRIENDLY)
# ==========================================
if __name__ == "__main__":
    # Railway asigna el puerto mediante la variable de entorno 'PORT'
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
