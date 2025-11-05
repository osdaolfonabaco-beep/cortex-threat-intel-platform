import dash
import dash_bootstrap_components as dbc 
from dash import html, dcc, Input, Output, State, no_update
import os
from dotenv import load_dotenv

# Importamos nuestro Gestor de Grafo
from src.graph_manager import GraphManager

# --- 1. Carga de Configuración ---
load_dotenv()
neo4j_uri = os.environ.get("NEO4J_URI")
neo4j_user = os.environ.get("NEO4J_USER")
neo4j_password = os.environ.get("NEO4J_PASSWORD")

# --- 2. Funciones de Ayuda para la Revisión ---

# --- Funciones de Nodos ---
def get_next_pending_node():
    """Busca el SIGUIENTE nodo pendiente."""
    manager = None
    try:
        manager = GraphManager(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        manager.connect()
        query = """
        MATCH (n)
        WHERE n.status = 'pending'
        RETURN n.name AS name, labels(n)[0] AS type, n.source AS source, elementId(n) AS id
        LIMIT 1
        """
        result = manager.run_query(query)
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting next pending node: {e}")
        return None
    finally:
        if manager: manager.close()

def process_node(node_id, action):
    """Aprueba o rechaza un NODO."""
    manager = None
    try:
        manager = GraphManager(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        manager.connect()
        if action == 'approve':
            query = "MATCH (n) WHERE elementId(n) = $id SET n.status = 'approved'"
            manager.run_query(query, parameters={"id": node_id})
        elif action == 'reject':
            query = "MATCH (n) WHERE elementId(n) = $id DETACH DELETE n"
            manager.run_query(query, parameters={"id": node_id})
    except Exception as e:
        print(f"Error processing node: {e}")
    finally:
        if manager: manager.close()

# --- ¡NUEVAS Funciones de Relaciones! ---
def get_next_pending_relationship():
    """Busca la SIGUIENTE relación pendiente."""
    manager = None
    try:
        manager = GraphManager(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        manager.connect()
        # Traemos la relación Y los nodos que conecta
        query = """
        MATCH (a)-[r {status: 'pending'}]->(b)
        RETURN 
            elementId(r) AS id, 
            type(r) AS rel_type, 
            r.source AS source,
            a.name AS source_name, 
            labels(a)[0] AS source_type,
            b.name AS target_name,
            labels(b)[0] AS target_type
        LIMIT 1
        """
        result = manager.run_query(query)
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting next pending rel: {e}")
        return None
    finally:
        if manager: manager.close()

def process_relationship(rel_id, action):
    """Aprueba o rechaza una RELACIÓN."""
    manager = None
    try:
        manager = GraphManager(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        manager.connect()
        if action == 'approve':
            query = "MATCH ()-[r]-() WHERE elementId(r) = $id SET r.status = 'approved'"
            manager.run_query(query, parameters={"id": rel_id})
        elif action == 'reject':
            query = "MATCH ()-[r]-() WHERE elementId(r) = $id DELETE r"
            manager.run_query(query, parameters={"id": rel_id})
    except Exception as e:
        print(f"Error processing relationship: {e}")
    finally:
        if manager: manager.close()


# --- 3. Inicializar la Aplicación Dash ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "Cortex - Review Panel"

# --- 4. Layout del Panel de Revisión (¡ACTUALIZADO CON TABS!) ---
app.layout = dbc.Container([
    # Stores para guardar el ID del ítem actual en cada pestaña
    dcc.Store(id='current-node-store'),
    dcc.Store(id='current-rel-store'),
    
    dbc.NavbarSimple(
        brand="CORTEX: AI Review Panel",
        brand_style={"fontSize": "1.5rem", "fontWeight": "bold"},
        color="danger", 
        dark=True,
        fluid=True,
    ),
    
    # --- ¡NUEVAS TABS! ---
    dbc.Tabs(
        [
            dbc.Tab(label="Review Nodes", tab_id="tab-nodes"),
            dbc.Tab(label="Review Relationships", tab_id="tab-rels"),
        ],
        id="review-tabs",
        active_tab="tab-nodes", # Empezar en la pestaña de Nodos
        className="mt-3"
    ),
    
    dbc.Row(
        dbc.Col(
            dbc.Card(
                [
                    # El CardHeader y CardBody se llenarán dinámicamente
                    dbc.CardHeader(id='review-card-header'),
                    dbc.CardBody(id='review-card-body'), 
                    
                    # Los botones están fijos en el footer
                    dbc.CardFooter(
                        dbc.Row([
                            dbc.Col(dbc.Button("Approve", id='approve-button', color="success", n_clicks=0), width=6),
                            dbc.Col(dbc.Button("Reject", id='reject-button', color="danger", n_clicks=0), width=6),
                        ])
                    )
                ], 
                className="mt-2" # Reducido el margen superior
            ),
            width={"size": 8, "offset": 2} 
        )
    )
], fluid=True, className="bg-dark text-light vh-100")


# --- 5. Callback (¡ACTUALIZADO!) ---
# Un callback para manejar AMBAS pestañas
@app.callback(
    Output('review-card-header', 'children'),
    Output('review-card-body', 'children'),
    Output('current-node-store', 'data'),
    Output('current-rel-store', 'data'),
    Input('review-tabs', 'active_tab'), # Se activa al cambiar de pestaña
    Input('approve-button', 'n_clicks'), # Se activa al aprobar
    Input('reject-button', 'n_clicks'),  # Se activa al rechazar
    State('current-node-store', 'data'),
    State('current-rel-store', 'data')
)
def update_review_card(active_tab, approve_clicks, reject_clicks, node_data, rel_data):
    
    # 1. Determinar qué causó la activación
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'review-tabs'

    # 2. Si fue un botón, procesar la acción BASADO EN LA PESTAÑA ACTIVA
    if triggered_id == 'approve-button':
        if active_tab == 'tab-nodes' and node_data and node_data.get('id'):
            process_node(node_data['id'], 'approve')
        elif active_tab == 'tab-rels' and rel_data and rel_data.get('id'):
            process_relationship(rel_data['id'], 'approve')
            
    elif triggered_id == 'reject-button':
        if active_tab == 'tab-nodes' and node_data and node_data.get('id'):
            process_node(node_data['id'], 'reject')
        elif active_tab == 'tab-rels' and rel_data and rel_data.get('id'):
            process_relationship(rel_data['id'], 'reject')

    # 3. Cargar el siguiente ítem BASADO EN LA PESTAÑA ACTIVA
    
    # --- Lógica para Pestaña de Nodos ---
    if active_tab == 'tab-nodes':
        pending_node = get_next_pending_node()
        if pending_node:
            header = html.H4("Pending AI Finding (Node)")
            body = [
                html.H5(pending_node['name'], className="card-title"),
                dbc.Badge(pending_node['type'], color=get_color_for_type(pending_node['type']), className="ms-1"),
                html.Hr(style={"borderColor": "#555"}),
                html.Strong("Source Article:"),
                html.A(pending_node['source'], href=pending_node['source'], target="_blank", style={"display": "block", "wordWrap": "break-word"}),
            ]
            return header, body, {'id': pending_node['id']}, no_update
        else:
            header = html.H4("Pending AI Finding (Node)")
            body = [html.H5("All Clear!", className="card-title"), html.P("No pending nodes found to review."), dbc.Spinner(color="success")]
            return header, body, {'id': None}, no_update

    # --- Lógica para Pestaña de Relaciones ---
    elif active_tab == 'tab-rels':
        pending_rel = get_next_pending_relationship()
        if pending_rel:
            header = html.H4("Pending AI Finding (Relationship)")
            
            # Formatear la relación de forma visual
            rel_display = html.Div([
                dbc.Badge(pending_rel['source_type'], color=get_color_for_type(pending_rel['source_type']), className="ms-1"),
                html.Span(f" {pending_rel['source_name']} "),
                html.Strong(f"-[{pending_rel['rel_type']}]-> ", style={"color": "#FF851B"}),
                dbc.Badge(pending_rel['target_type'], color=get_color_for_type(pending_rel['target_type']), className="ms-1"),
                html.Span(f" {pending_rel['target_name']}"),
            ], style={"fontSize": "1.1rem"})

            body = [
                rel_display,
                html.Hr(style={"borderColor": "#555"}),
                html.Strong("Source Article:"),
                html.A(pending_rel['source'], href=pending_rel['source'], target="_blank", style={"display": "block", "wordWrap": "break-word"}),
            ]
            return header, body, no_update, {'id': pending_rel['id']}
        else:
            header = html.H4("Pending AI Finding (Relationship)")
            body = [html.H5("All Clear!", className="card-title"), html.P("No pending relationships found to review."), dbc.Spinner(color="success")]
            return header, body, no_update, {'id': None}

    return no_update # Por si acaso

# Helper de color
def get_color_for_type(node_type):
    colors = {
        "Actor": "danger", "Malware": "warning", "TTP": "info", 
        "Tool": "primary", "Infrastructure": "success"
    }
    return colors.get(node_type, "secondary") 

# --- 6. Bloque de Ejecución ---
if __name__ == '__main__':
    app.run(debug=True, port=8051)