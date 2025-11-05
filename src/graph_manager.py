from neo4j import GraphDatabase

# --- Configuración de la Conexión ---
# Estas son las credenciales para tu base de datos local.
# Asegúrate de que coincidan con tu Neo4j Desktop.

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Password123." # ¡Asegúrate de que esta sea tu contraseña real!


# ------------------------------------


class GraphManager:
    def __init__(self, uri, user, password):
        """
        Inicializa el manejador. Guarda las credenciales.
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        print("Manejador de Grafo inicializado.")

    def connect(self):
        """
        Establece la conexión con la base de datos Neo4j.
        """
        try:
            # Crea el "driver" (el conector principal)
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verifica que la conexión es exitosa
            self.driver.verify_connectivity()
            print(f"Conexión exitosa a: {self.uri}")
        except Exception as e:
            print(f"Error al conectar con Neo4j: {e}")

    def run_query(self, query, parameters=None):
        """
        Ejecuta una consulta Cypher en la base de datos, opcionalmente con parámetros,
        y DEVUELVE los resultados.
        """
        if not self.driver:
            print("Error: El driver no está conectado. Llama a connect() primero.")
            return None # Devolver None si no hay conexión

        try:
            # Obtenemos una sesión de la base de datos
            with self.driver.session() as session:
                
                # Preparamos el mensaje de log (para depuración)
                log_message = f"Ejecutando consulta: {query}"
                if parameters:
                    log_message += f" con parámetros: {parameters}"
                # (Quitamos el print de aquí para no duplicar el log)
                # print(log_message)

                # Ejecutamos la consulta con sus parámetros
                result = session.run(query, parameters)
                
                # ¡Cambio sutil pero importante!
                # Para MERGE/CREATE, result.data() está vacío.
                # Para MATCH/RETURN, contiene los datos.
                # Así que convertimos el iterador a una lista
                # para "consumirlo" y que la transacción se complete.
                records = [record for record in result]
                
                # (Quitamos el log de éxito para reducir el ruido)
                # print("Consulta ejecutada con éxito.") 
                
                # Devolvemos la lista de resultados (Records)
                return records

        except Exception as e:
            print(f"Error al ejecutar la consulta: {e}")
            return None # Devolver None si la consulta falla

    def close(self):
        """
        Cierra la conexión si está abierta.
        """
        if self.driver:
            self.driver.close()
            print("Conexión cerrada.")

# --- Bloque de Prueba ---
# Este código solo se ejecutará cuando corramos 'python src/graph_manager.py'
if __name__ == "__main__":
    print("Iniciando prueba de conexión y consulta (con parámetros)...")
    
    # Asegúrate de que estas credenciales coincidan con las de arriba
    # y sean correctas para tu base de datos.
    test_uri = "neo4j://127.0.0.1:7687"
    test_user = "neo4j"
    test_password = "Password123." # Cambia esto por tu contraseña real
    
    db = GraphManager(test_uri, test_user, test_password)
    db.connect()

    # Prueba de creación con parámetros
    test_query = "CREATE (n:TestNode {name: $name_param, status: 'test'})"
    test_params = {"name_param": "¡Hola Grafo!"}
    db.run_query(test_query, test_params)

    # Prueba de limpieza con parámetros
    cleanup_query = "MATCH (n:TestNode {name: $name_param}) DELETE n"
    cleanup_params = {"name_param": "¡Hola Grafo!"}
    db.run_query(cleanup_query, cleanup_params)

    db.close()
    
    print("Prueba de conexión y consulta finalizada.")