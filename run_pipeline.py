import os
import json
from dotenv import load_dotenv

# --- Importamos nuestras "herramientas" de 'src' ---
from src.graph_manager import GraphManager
from src.ai_extractor import AIExtractor 

# --- ¡FUNCIÓN ACTUALIZADA! ---
def ingest_graph_data(manager, data, source_link):
    """
    Toma los datos extraídos por la IA y los escribe en Neo4j
    CON ESTADO DE 'PENDING' (Staging).
    """
    
    nodes = data.get("nodes", [])
    relationships = data.get("relationships", [])
    
    if not nodes:
        print("La IA no extrajo nodos. Saltando ingesta en BD.")
        return

    print(f"\n--- Iniciando Ingesta en Staging (Pending) ---")
    
    # --- 1. Ingesta de Nodos ---
    nodes_created_count = 0
    for node in nodes:
        node_type = node.get("type")
        node_name = node.get("name")
        
        if not node_type or not node_name:
            print(f"Omitiendo nodo inválido: {node}")
            continue
            
        # --- ¡LÓGICA DE STAGING! ---
        # MERGE (encuentra o crea el nodo)
        # ON CREATE (si es nuevo) -> ponlo como 'pending'
        # ON MATCH (si ya existe) -> no hagas nada a su estado
        cypher = f"""
        MERGE (n:{node_type} {{name: $name}})
        ON CREATE SET n.status = 'pending', n.source = $source
        """
        manager.run_query(cypher, parameters={"name": node_name, "source": source_link})
        nodes_created_count += 1
    
    print(f"Nodos procesados: {nodes_created_count}")

    # --- 2. Ingesta de Relaciones ---
    rels_created_count = 0
    for rel in relationships:
        source_name, rel_type, dest_name = rel
        
        # --- ¡LÓGICA DE STAGING! ---
        cypher = f"""
        MATCH (a {{name: $source_name}})
        MATCH (b {{name: $dest_name}})
        MERGE (a)-[r:{rel_type}]->(b)
        ON CREATE SET r.status = 'pending', r.source = $source
        """
        manager.run_query(cypher, parameters={
            "source_name": source_name,
            "dest_name": dest_name,
            "source": source_link
        })
        rels_created_count += 1
    
    print(f"Relaciones procesadas: {rels_created_count}")
    print("--- Ingesta en Staging Completada ---")


def main():
    """
    Función principal para orquestar el pipeline de ETL completo.
    """
    print("Iniciando pipeline de Cortex (Modo Staging)...")
    
    load_dotenv()

    neo4j_uri = os.environ.get("NEO4J_URI")
    neo4j_user = os.environ.get("NEO4J_USER")
    neo4j_password = os.environ.get("NEO4J_PASSWORD")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not all([neo4j_uri, neo4j_user, neo4j_password, anthropic_api_key]):
        print("Error: Faltan variables de entorno. Revisa tu archivo .env")
        return

    print("Variables de entorno cargadas.")

    # --- 2. (E)XTRACT: Cargar Datos de Origen ---
    try:
        with open('items_extraidos.json', 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        if not articles:
            print("El archivo 'items_extraidos.json' está vacío. No hay nada que procesar.")
            return

        print(f"Se cargaron {len(articles)} artículos desde 'items_extraidos.json'.")

    except FileNotFoundError:
        print("Error: No se encontró 'items_extraidos.json'.")
        print("Por favor, ejecuta 'python src/ingestor.py' primero.")
        return
    except json.JSONDecodeError:
        print("Error: 'items_extraidos.json' está malformado.")
        return
        
    # --- 3. Inicializar Conexiones (Herramientas) ---
    print("Inicializando herramientas...")
    try:
        extractor = AIExtractor(api_key=anthropic_api_key)
        db_manager = GraphManager(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        db_manager.connect()
    
    except Exception as e:
        print(f"Error fatal al inicializar conexiones: {e}")
        return

    # --- 4. Bucle de Procesamiento (T)ransform y (L)oad ---
    print("\n========= INICIANDO PROCESAMIENTO DE ARTÍCULOS (STAGING) =========")
    total_articles = len(articles)
    
    for i, article in enumerate(articles, 1):
        print(f"\n--- Procesando Artículo {i}/{total_articles} ---")
        print(f"Título: {article.get('title')}")

        raw_text = article.get('raw_text')
        article_link = article.get('link') # ¡Obtenemos el enlace!
        
        if not raw_text:
            print("Artículo sin 'raw_text'. Saltando.")
            continue
        
        extracted_data = extractor.extract_entities(raw_text)
        
        if extracted_data:
            # --- ¡CAMBIO! ---
            # Pasamos el 'article_link' como la fuente
            ingest_graph_data(db_manager, extracted_data, article_link)
        else:
            print(f"No se extrajeron datos para el artículo '{article.get('title')}'.")
            
    print("\n========= PROCESAMIENTO DE ARTÍCULOS COMPLETADO =========")
    
    db_manager.close()
    print("Pipeline finalizado. Conexión a Neo4j cerrada.")


if __name__ == "__main__":
    main()