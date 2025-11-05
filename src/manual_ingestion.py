# src/manual_ingestion.py

# Importamos las herramientas que necesitamos
from graph_manager import GraphManager, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def ingest_report_1(graph_db):
    """
    Ingesta manual de nuestro primer reporte de inteligencia ficticio.
    Reporte: "ShadowStalker group uses new 'EchoViper' malware"
    """
    print("Iniciando ingesta del Reporte 1...")

    # --- 1. Definir las Entidades (los Nodos) ---
    
    # El Actor
    actor_name = "ShadowStalker"
    actor_query = "MERGE (a:Actor {name: $name})"
    graph_db.run_query(actor_query, {"name": actor_name})

    # El Malware
    malware_name = "EchoViper"
    malware_query = "MERGE (m:Malware {name: $name})"
    graph_db.run_query(malware_query, {"name": malware_name})

    # La Infraestructura (IP)
    ip_address = "198.51.100.23"
    ip_query = "MERGE (i:IP {address: $address})"
    graph_db.run_query(ip_query, {"address": ip_address})

    # --- 2. Definir las Relaciones (las Aristas) ---
    
    print("Creando relaciones...")
    
    # Relación: Actor -> USA -> Malware
    query_actor_uses_malware = """
    MATCH (a:Actor {name: $actor_name})
    MATCH (m:Malware {name: $malware_name})
    MERGE (a)-[r:USES]->(m)
    """
    graph_db.run_query(query_actor_uses_malware, {
        "actor_name": actor_name,
        "malware_name": malware_name
    })

    # Relación: Malware -> TIENE_INFRA -> IP
    query_malware_has_infra = """
    MATCH (m:Malware {name: $malware_name})
    MATCH (i:IP {address: $ip_address})
    MERGE (m)-[r:HAS_INFRASTRUCTURE]->(i)
    """
    graph_db.run_query(query_malware_has_infra, {
        "malware_name": malware_name,
        "ip_address": ip_address
    })

    print("--- Reporte 1 Ingestado Exitosamente ---")
    print(f"Nodos creados/actualizados: {actor_name}, {malware_name}, {ip_address}")

#
# <--- Asegúrate de que haya un espacio aquí
#

def ingest_report_2(graph_db):
    """
    Ingesta manual del Reporte 2.
    Reporte: "ShadowStalker group uses new 'ViperLink' RAT"
    """
    print("\nIniciando ingesta del Reporte 2...")

    # --- 1. Definir Entidades ---
    
    # Este actor YA EXISTE. MERGE lo encontrará y lo reutilizará.
    actor_name = "ShadowStalker"
    actor_query = "MERGE (a:Actor {name: $name})"
    graph_db.run_query(actor_query, {"name": actor_name})

    # Este malware es NUEVO. MERGE lo creará.
    malware_name = "ViperLink"
    malware_query = "MERGE (m:Malware {name: $name})"
    graph_db.run_query(malware_query, {"name": malware_name})

    # Este dominio es NUEVO. MERGE lo creará.
    domain_name = "control.viperlink-c2.com"
    domain_query = "MERGE (d:Domain {name: $name})"
    graph_db.run_query(domain_query, {"name": domain_name})

    # --- 2. Definir Relaciones ---
    print("Creando nuevas relaciones...")
    
    # Relación: Actor -> USA -> Malware
    query_actor_uses_malware = """
    MATCH (a:Actor {name: $actor_name})
    MATCH (m:Malware {name: $malware_name})
    MERGE (a)-[r:USES]->(m)
    """
    graph_db.run_query(query_actor_uses_malware, {
        "actor_name": actor_name,
        "malware_name": malware_name
    })

    # Relación: Malware -> TIENE_INFRA -> Dominio
    query_malware_has_infra = """
    MATCH (m:Malware {name: $malware_name})
    MATCH (d:Domain {name: $domain_name})
    MERGE (m)-[r:HAS_INFRASTRUCTURE]->(d)
    """
    graph_db.run_query(query_malware_has_infra, {
        "malware_name": malware_name,
        "domain_name": domain_name
    })

    print("--- Reporte 2 Ingestado Exitosamente ---")
    print(f"Nodos reutilizados: {actor_name}")
    print(f"Nodos nuevos creados: {malware_name}, {domain_name}")

#
# <--- Asegúrate de que haya un espacio aquí
#

# --- Bloque Principal ---
# ¡ESTE BLOQUE DEBE ESTAR AL NIVEL 0 DE INDENTACIÓN!
if __name__ == "__main__":
    try:
        db = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        db.connect()
        
        # --- Ejecutamos ambas ingestas ---
        # Si los datos ya existen del script anterior, MERGE los reutilizará.
        
        ingest_report_1(db)
        ingest_report_2(db)
        
    except Exception as e:
        print(f"Error durante la ingesta manual: {e}")
    finally:
        if 'db' in locals() and db.driver:
            db.close()
            print("\nIngesta manual (1 y 2) finalizada. Conexión cerrada.")