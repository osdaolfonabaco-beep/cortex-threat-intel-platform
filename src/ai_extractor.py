import anthropic
import json

# Definimos el prompt del sistema como una constante global
# (perfecto para que esté aquí, ya que es parte de la "herramienta")
SYSTEM_PROMPT = """
Eres un analista experto en inteligencia de amenazas de ciberseguridad.
Tu tarea es leer el texto proporcionado y extraer entidades de inteligencia de 
amenazas y sus relaciones.

Debes extraer las siguientes entidades (nodos):
- Actor: Grupos de amenaza, actores (ej. 'ShadowStalker', 'Lazarus Group').
- TTP: Tácticas, Técnicas y Procedimientos (ej. 'Phishing', 'CVE-2024-1234').
- Malware: Nombres de software malicioso (ej. 'EchoViper', 'WannaCry').
- Infrastructure: IPs, Dominios, URLs (ej. '198.51.100.25', 'control.shadow-ops.net').
- Tool: Herramientas usadas por los actores (ej. 'CobaltStrike', 'Mimikatz').

Debes formatear tu respuesta como un ÚNICO objeto JSON con dos claves:
1. "nodes": Una lista de objetos, donde cada objeto representa una entidad 
  única. Cada objeto debe tener:
  - "type": El tipo de entidad (ej. 'Actor', 'Malware', 'TTP', 'Infrastructure', 'Tool').
  - "name": El nombre o valor de la entidad (ej. 'ShadowStalker', 'CVE-2024-1234').
2. "relationships": Una lista de tuplas (listas de 3 elementos) que 
  describen la conexión entre entidades, en el formato 
  [ [entidad_origen, "RELACION", entidad_destino] ].
  - entidad_origen: El nombre (name) de la entidad de origen.
  - "RELACION": El tipo de acción, ej. "USES", "TARGETS", "EXPLOITS", "COMMUNICATES_WITH", "ALSO_KNOWN_AS", "DEPLOYS".
  - entidad_destino: El nombre (name) de la entidad de destino.

Reglas Importantes:
- Asegúrate de que los nombres de las entidades en "relationships" coincidan 
  EXACTAMENTE con los nombres en la lista "nodes".
- Solo responde con el objeto JSON. No incluyas ningún texto de saludo, 
  explicación o preámbulo.
"""

class AIExtractor:
    """
    Una clase profesional para encapsular la lógica de extracción de la IA.
    Nuestro pipeline la inicializará con la clave API.
    """
    
    def __init__(self, api_key):
        """
        Inicializa el cliente de Anthropic.
        """
        if not api_key:
            raise ValueError("API key de Anthropic no proporcionada.")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        print("Cliente de AIExtractor (Anthropic) inicializado.")

    def extract_entities(self, text_content):
        """
        Toma un bloque de texto crudo y devuelve un objeto 
        Python (diccionario) con las entidades extraídas.
        """
        print(f"Enviando {len(text_content)} caracteres a la IA para extracción...")
        
        if not text_content.strip():
            print("Advertencia: Se recibió texto vacío. Saltando extracción.")
            return None

        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2048,
                temperature=0.0,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": text_content
                    }
                ]
            )
            
            # Extraemos el texto de la respuesta
            json_response_text = message.content[0].text
            
            # Intentamos convertir el texto JSON en un diccionario de Python
            extracted_data = json.loads(json_response_text)
            print("¡Éxito! La IA devolvió un JSON válido.")
            return extracted_data

        except json.JSONDecodeError:
            print("--- ERROR DE EXTRACCIÓN (IA) ---")
            print("La IA devolvió una respuesta que NO es un JSON válido.")
            print(f"Respuesta cruda: {json_response_text}")
            return None
        except Exception as e:
            print(f"--- ERROR DE EXTRACCIÓN (API) ---")
            print(f"Ocurrió un error al conectar con la API: {e}")
            return None