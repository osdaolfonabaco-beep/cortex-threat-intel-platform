# src/setup_database.py

# Importamos nuestra clase GraphManager desde el archivo graph_manager.py
# También importamos nuestras credenciales (¡buena práctica!)
from graph_manager import GraphManager, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def define_schema(graph_db):
    """
    Define el esquema principal y las restricciones de unicidad para Cortex.
    """
    print("Iniciando la definición del esquema...")
    
    # Estas son las entidades clave de nuestro proyecto
    schema_queries = [
        # Un actor (ej. "Lazarus Group") debe tener un nombre único.
        "CREATE CONSTRAINT actors_unique_name IF NOT EXISTS FOR (a:Actor) REQUIRE a.name IS UNIQUE",
        
        # Un malware (ej. "WannaCry") debe tener un nombre único.
        "CREATE CONSTRAINT malware_unique_name IF NOT EXISTS FOR (m:Malware) REQUIRE m.name IS UNIQUE",
        
        # Una dirección IP debe ser única.
        "CREATE CONSTRAINT ip_unique_address IF NOT EXISTS FOR (i:IP) REQUIRE i.address IS UNIQUE",
        
        # Un dominio debe ser único.
        "CREATE CONSTRAINT domain_unique_name IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE",

        # Un TTP (ej. "T1059.001") debe tener un ID único.
        "CREATE CONSTRAINT ttp_unique_id IF NOT EXISTS FOR (t:TTP) REQUIRE t.id IS UNIQUE",
        
        # Un reporte de inteligencia (ej. la URL) debe ser único.
        "CREATE CONSTRAINT report_unique_url IF NOT EXISTS FOR (r:Report) REQUIRE r.url IS UNIQUE"
    ]
    
    # Ejecutamos cada consulta de esquema una por una
    for query in schema_queries:
        graph_db.run_query(query)
        
    print("--- Esquema 'Cortex' definido con éxito. ---")
    print("Restricciones creadas para: Actor, Malware, IP, Domain, TTP, Report.")

# --- Bloque Principal ---
# Esto se ejecuta cuando corremos 'python src/setup_database.py'

if __name__ == "__main__":
    try:
        # Nos conectamos usando las credenciales importadas
        db = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        db.connect()
        
        # Ejecutamos la función principal de este script
        define_schema(db)
        
    except Exception as e:
        print(f"Error durante la configuración de la base de datos: {e}")
    finally:
        # Nos aseguramos de cerrar la conexión pase lo que pase
        if 'db' in locals() and db.driver:
            db.close()
            print("Configuración finalizada. Conexión cerrada.")