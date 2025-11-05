import dash
import dash_bootstrap_components as dbc 
import dash_cytoscape as cyto
from dash import html, dcc, Input, Output, State, no_update
import os
from dotenv import load_dotenv
import anthropic
import re

# --- Importamos nuestro Gestor de Grafo ---
from src.graph_manager import GraphManager

# --- 1. Carga de Configuración ---
load_dotenv()
neo4j_uri = os.environ.get("NEO4J_URI")
neo4j_user = os.environ.get("NEO4J_USER")
neo4j_password = os.environ.get("NEO4J_PASSWORD")
anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

# --- 2. Funciones de Consulta a Neo4j ---

# --- ¡ACTUALIZADO! ---
def get_graph_elements(cypher_query="MATCH (n {status: 'approved'})-[r {status: 'approved'}]->(m {status: 'approved'}) RETURN n, r, m"):
    """
    Función Principal: Ejecuta una consulta para OBTENER EL GRAFO.
    La consulta por defecto ahora SOLO trae datos aprobados.
    """
    print(f"Executing query to get graph data: {cypher_query}")
    manager = None
    try:
        manager = GraphManager(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        manager.connect()
        print("Connection successful.")

        elements = []
        node_ids = set()
        results = manager.run_query(cypher_query)

        if not results:
            print("Query returned no results.")
            return []
        
        for record in results:
            for key, value in record.items():
                if value is None:
                    continue
                if hasattr(value, 'labels'): 
                    if value.element_id not in node_ids:
                        node_ids.add(value.element_id)
                        elements.append({
                            'data': {'id': value.element_id, 'label': value['name'], 'type': list(value.labels)[0]},
                            'classes': list(value.labels)[0]
                        })
                elif hasattr(value, 'type'):
                    elements.append({
                        'data': {'id': value.element_id, 'source': value.start_node.element_id, 'target': value.end_node.element_id, 'label': type(value).__name__}
                    })
        
        print(f"Data loaded: {len(node_ids)} nodes, {len(elements) - len(node_ids)} relationships.")
        return elements
    except Exception as e:
        print(f"Error loading data from Neo4j: {e}")
        return []
    finally:
        if manager:
            manager.close()
            print("Neo4j connection closed.")

# --- ¡ACTUALIZADO! ---
def get_node_connections(node_name):
    """
    Función de Ayuda: Obtiene las conexiones APROBADAS para un nodo específico.
    """
    print(f"Querying connections for node: {node_name}")
    manager = None
    try:
        manager = GraphManager(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        manager.connect()
        
        # --- ¡LÓGICA DE STAGING! ---
        # Solo trae conexiones donde la relación Y el nodo objetivo
        # también estén aprobados.
        query = """
        MATCH (n {name: $name, status: 'approved'})-[r {status: 'approved'}]-(m {status: 'approved'})
        RETURN type(r) AS rel_type, m.name AS target_name, labels(m)[0] AS target_type
        """
        results = manager.run_query(query, parameters={"name": node_name})
        
        connections = []
        if results:
            for record in results:
                connections.append({
                    "rel_type": record["rel_type"],
                    "target_name": record["target_name"],
                    "target_type": record["target_type"]
                })
        
        print(f"Found {len(connections)} connections.")
        return connections

    except Exception as e:
        print(f"Error querying node connections: {e}")
        return []
    finally:
        if manager:
            manager.close()
            print("Neo4j connection (for details) closed.")

# --- 3. Lógica del Traductor de IA ---

# --- ¡ACTUALIZADO! ---
# Le enseñamos a la IA sobre la propiedad 'status'
CYPHER_TRANSLATOR_PROMPT = """
Eres un experto traductor de lenguaje natural a Cypher de Neo4j.
Tu tarea es tomar una pregunta del usuario y convertirla en una consulta Cypher que devuelva un subgrafo (nodos y relaciones) de una base de datos de inteligencia de amenazas.

El esquema del grafo es:
Nodos:
- (:Actor {name: "...", status: "approved"})
- (:Malware {name: "...", status: "approved"})
- (:TTP {name: "...", status: "approved"})
- (:Tool {name: "...", status: "approved"})
- (:Infrastructure {name: "...", status: "approved"})

Relaciones:
- [:USES {status: "approved"}]
- [:TARGETS {status: "approved"}]
- ... (todas las relaciones también tienen 'status: "approved"')

Reglas:
1.  **Devuelve SOLO el código Cypher.** No incluyas "Aquí está la consulta:", "MATCH...", ` ```cypher ` o cualquier otro texto.
2.  Tu consulta SIEMPRE debe devolver nodos y relaciones (RETURN n, r, m).
3.  **¡IMPORTANTE!** Todas las entidades (nodos y relaciones) en tu consulta DEBEN ser filtradas para tener la propiedad `{status: 'approved'}`.

Ejemplos de Preguntas y Respuestas (Consultas Cypher):
- P: Muéstrame todo
  R: MATCH (n {status: 'approved'})-[r {status: 'approved'}]->(m {status: 'approved'}) RETURN n, r, m
- P: Qué herramientas usa ShadowStalker
  R: MATCH (a:Actor {name: 'ShadowStalker', status: 'approved'})-[r:USES {status: 'approved'}]->(t:Tool {status: 'approved'}) RETURN a, r, t
- P: Con qué se comunica EchoViper
  R: MATCH (m:Malware {name: 'EchoViper', status: 'approved'})-[r:COMMUNICATES_WITH {status: 'approved'}]->(i:Infrastructure {status: 'approved'}) RETURN m, r, i
- P: Qué sabes sobre CVE-2024-1234
  R: MATCH (n {name: 'CVE-2024-1234', status: 'approved'})-[r {status: 'approved'}]-(m {status: 'approved'}) RETURN n, r, m
"""

try:
    ia_client = anthropic.Anthropic(api_key=anthropic_api_key)
    print("Anthropic client for translation initialized.")
except Exception as e:
    print(f"Error initializing Anthropic client: {e}")
    ia_client = None

def get_cypher_from_ia(user_question):
    if not ia_client:
        print("Error: AI client is not initialized.")
        return None
    print(f"Sending question to AI: '{user_question}'")
    try:
        message = ia_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            temperature=0.0,
            system=CYPHER_TRANSLATOR_PROMPT,
            messages=[
                {"role": "user", "content": user_question}
            ]
        )
        cypher_query = message.content[0].text
        cypher_query = re.sub(r"^\s*```cypher\s*", "", cypher_query, flags=re.IGNORECASE)
        cypher_query = re.sub(r"\s*```\s*$", "", cypher_query)
        cypher_query = cypher_query.strip()
        print(f"AI returned Cypher query: {cypher_query}")
        return cypher_query
    except Exception as e:
        print(f"Error calling Anthropic API: {e}")
        return None

# --- 4. Inicializar la Aplicación Dash ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "Cortex - Threat Intelligence Platform"

# --- 5. Cargar los Datos Iniciales ---
# ¡Esto ahora cargará un grafo vacío, lo cual es correcto!
initial_elements = get_graph_elements() 

# --- 6. Definición del Layout (Traducido) ---
navbar = dbc.NavbarSimple(
    brand="CORTEX: Visual Threat Intelligence Platform",
    brand_style={"fontSize": "1.5rem", "fontWeight": "bold"},
    color="dark",
    dark=True,
    fluid=True,
)

chat_controls = dbc.InputGroup(
    [
        dbc.Input(id='chat-input', placeholder='Ask a question in natural language...'),
        dbc.Button('Query AI', id='chat-button', n_clicks=0, color="primary", className="ms-2")
    ],
    className="p-3",
)

graph_view = dcc.Loading(
    id="loading-graph",
    type="default",
    children=cyto.Cytoscape(
        id='cytoscape-graph',
        layout={'name': 'cose'},
        style={'width': '100%', 'height': '75vh'}, 
        elements=initial_elements,
        stylesheet=[
            {
                'selector': 'node',
                'style': {
                    'label': 'data(label)',
                    'font-size': '10px',
                    'color': '#FFFFFF', 
                    'text-outline-color': '#000000', 
                    'text-outline-width': '1px'
                }
            },
            {
                'selector': 'edge',
                'style': {
                    'label': 'data(label)',
                    'font-size': '8px',
                    'color': '#999999', 
                    'curve-style': 'bezier',
                    'target-arrow-shape': 'triangle',
                    'target-arrow-color': '#999999',
                    'line-color': '#999999' 
                }
            },
            {'selector': '.Actor', 'style': {'background-color': '#FF4136'}}, 
            {'selector': '.Malware', 'style': {'background-color': '#FF851B'}}, 
            {'selector': '.TTP', 'style': {'background-color': '#FFDC00', 'color': '#000'}}, 
            {'selector': '.Tool', 'style': {'background-color': '#0074D9'}}, 
            {'selector': '.Infrastructure', 'style': {'background-color': '#2ECC40'}} 
        ]
    )
)

details_panel = dbc.Card(
    [
        dbc.CardHeader(html.H4("Node Details", className="mb-0")),
        dbc.CardBody(
            id='node-details-panel',
            children=[
                html.P("Click a node on the graph to see its information here.", 
                       className="text-muted")
            ]
        )
    ],
    style={'height': '75vh', 'overflowY': 'auto'} 
)

app.layout = dbc.Container(
    [
        navbar,
        chat_controls,
        dbc.Row(
            [
                dbc.Col(graph_view, width=8), 
                dbc.Col(details_panel, width=4), 
            ],
            className="p-3"
        )
    ],
    fluid=True, 
    className="bg-dark text-light" 
)

# --- 7. Callback (Traductor de IA - Sin cambios) ---
@app.callback(
    Output('cytoscape-graph', 'elements'), 
    Input('chat-button', 'n_clicks'),      
    State('chat-input', 'value'),          
    prevent_initial_call=True 
)
def update_graph_on_chat(n_clicks, user_question):
    if not user_question:
        return no_update 
    cypher_query = get_cypher_from_ia(user_question)
    if not cypher_query:
        return no_update
    new_elements = get_graph_elements(cypher_query)
    return new_elements

# --- 8. Callback (Panel de Detalles - ¡ACTUALIZADO!) ---
@app.callback(
    Output('node-details-panel', 'children'), 
    Input('cytoscape-graph', 'tapNodeData')   
)
def display_node_details(node_data):
    if node_data is None:
        return [
            html.P("Click a node on the graph to see its information here.", 
                   className="text-muted")
        ]

    node_type = node_data.get('type', 'N/A')
    node_label = node_data.get('label', 'N/A')

    # ¡La lógica de conexiones ahora solo traerá conexiones 'approved'
    # gracias a la actualización de get_node_connections!
    connections = get_node_connections(node_label)
    
    connection_list_items = []
    if connections:
        for conn in connections:
            rel_type = conn.get('rel_type', 'N/A')
            target_name = conn.get('target_name', 'N/A')
            target_type = conn.get('target_type', 'N/A')
            
            badge_color = get_color_for_type(target_type)
            
            connection_list_items.append(
                dbc.ListGroupItem([
                    html.Span(f"{rel_type} ", style={"fontWeight": "bold", "color": "#FF851B"}),
                    html.Span(f" {target_name} "),
                    dbc.Badge(target_type, color=badge_color, className="ms-1")
                ], className="d-flex justify-content-between align-items-center")
            )
    else:
        connection_list_items.append(
            dbc.ListGroupItem("No approved connections found.")
        )

    details = [
        html.H4(node_label, className="mb-1"),
        dbc.Badge(node_type, color=get_color_for_type(node_type), className="ms-1"),
        html.Hr(style={"borderColor": "#555"}),
        
        html.H5("Approved Connections:", className="mt-3"),
        dbc.ListGroup(connection_list_items, flush=True), 
    ]
    
    return details

# Helper para asignar colores a las insignias (badges)
def get_color_for_type(node_type):
    colors = {
        "Actor": "danger", 
        "Malware": "warning", 
        "TTP": "info", 
        "Tool": "primary", 
        "Infrastructure": "success"
    }
    return colors.get(node_type, "secondary") 

# --- 9. Bloque para Ejecutar la Aplicación ---
if __name__ == '__main__':
    app.run(debug=True)