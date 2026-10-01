import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Carrega as configurações do arquivo .env
load_dotenv()

# 2. Pega a URL do banco
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ Erro: Arquivo .env não encontrado ou DATABASE_URL vazia.")
else:
    print("Tentando conectar ao banco de dados...")
    try:
        # 3. Prepara a conexão
        engine = create_engine(DATABASE_URL)
        
        # 4. Abre a conexão e tenta fazer uma consulta simples
        with engine.connect() as conexao:
            resultado = conexao.execute(text("SELECT version();"))
            versao = resultado.fetchone()[0]
            
            print("\n✅ Conexão bem-sucedida!")
            print(f"O seu banco na nuvem está rodando:\n{versao}")
            
    except Exception as e:
        print("\n❌ Falha na conexão. Verifique sua URL e internet.")
        print(f"Detalhe do erro: {e}")