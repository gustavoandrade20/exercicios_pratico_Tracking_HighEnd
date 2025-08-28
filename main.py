from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
from sqlalchemy import create_engine, Column, Integer, String, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- Configuração do Banco de Dados ---
DATABASE_URL = "sqlite:///./avaliacoes.db"  # Pode trocar para MySQL/PostgreSQL
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Avaliacao(Base):
    __tablename__ = "avaliacoes"
    id = Column(Integer, primary_key=True, index=True)
    pais = Column(String, index=True)
    tipo_avaliacao = Column(String)  # "curti" ou "nao_curti"

Base.metadata.create_all(bind=engine)

# --- Configuração da API ---
app = FastAPI()

# --- Models para requisição ---
class AvaliarPais(BaseModel):
    pais: str
    avaliacao: str  # "curti" ou "nao_curti"

# --- Funções auxiliares ---
def padronizar_pais(dados):
    return {
        "nome": dados.get("name", {}).get("common", ""),
        "populacao": dados.get("population", 0),
        "continente": dados.get("region", "")
    }

# --- Endpoints ---
@app.get("/paises/top10")
def top10():
    try:
        resposta = requests.get("https://restcountries.com/v3.1/all")
        paises = resposta.json()
        # Ordenar por população decrescente
        paises_ordenados = sorted(paises, key=lambda x: x.get("population", 0), reverse=True)
        top10 = paises_ordenados[:10]
        # Padronizar campos
        return [padronizar_pais(p) for p in top10]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/paises/buscar")
def buscar(nome: str):
    try:
        resposta = requests.get(f"https://restcountries.com/v3.1/name/{nome}")
        paises = resposta.json()
        if isinstance(paises, dict) and paises.get("status") == 404:
            raise HTTPException(status_code=404, detail="País não encontrado")
        padronizado = padronizar_pais(paises[0])
        # Adicionar contagem de avaliações
        db = SessionLocal()
        total_curti = db.query(func.count(Avaliacao.id)).filter(Avaliacao.pais==padronizado["nome"], Avaliacao.tipo_avaliacao=="curti").scalar()
        total_nao_curti = db.query(func.count(Avaliacao.id)).filter(Avaliacao.pais==padronizado["nome"], Avaliacao.tipo_avaliacao=="nao_curti").scalar()
        db.close()
        padronizado["avaliacoes"] = {"curti": total_curti, "nao_curti": total_nao_curti}
        return padronizado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/paises/avaliar")
def avaliar(avaliacao: AvaliarPais):
    if avaliacao.avaliacao not in ["curti", "nao_curti"]:
        raise HTTPException(status_code=400, detail="Avaliação deve ser 'curti' ou 'nao_curti'")
    try:
        db = SessionLocal()
        nova_avaliacao = Avaliacao(pais=avaliacao.pais, tipo_avaliacao=avaliacao.avaliacao)
        db.add(nova_avaliacao)
        db.commit()
        # Contar total de votos do país
        total_curti = db.query(func.count(Avaliacao.id)).filter(Avaliacao.pais==avaliacao.pais, Avaliacao.tipo_avaliacao=="curti").scalar()
        total_nao_curti = db.query(func.count(Avaliacao.id)).filter(Avaliacao.pais==avaliacao.pais, Avaliacao.tipo_avaliacao=="nao_curti").scalar()
        db.close()
        return {
            "pais": avaliacao.pais,
            "status": "sucesso",
            "avaliacoes_totais": {"curti": total_curti, "nao_curti": total_nao_curti}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
