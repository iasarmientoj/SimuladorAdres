import requests

def consultar_runt_publico(placa_buscada):
    """
    Consulta la API de Datos Abiertos de Colombia.
    Retorna True si la placa existe (Vehículo Activo), False si no.
    """
    # Endpoint oficial de datos.gov.co
    url_base = "https://www.datos.gov.co/resource/g7i9-xkxz.json"
    
    # FILTRO: Le pedimos a la API que solo traiga la fila donde la columna 'placa' coincida
    # Convertimos a mayúsculas por si acaso
    params = {'placa': placa_buscada.upper()} 
    
    try:
        # Hacemos el "Request" (la llamada telefónica a la API)
        respuesta = requests.get(url_base, params=params, timeout=5)
        
        # Convertimos la respuesta a JSON (lista de diccionarios)
        datos = respuesta.json()
        
        # Lógica: Si la lista tiene al menos 1 elemento, el vehículo está activo
        if len(datos) > 0:
            vehiculo = datos[0] # Tomamos el primer resultado
            return {
                'existe': True,
                'datos': vehiculo # Devolvemos marca, modelo, etc. por si quieres mostrarlos
            }
        else:
            return {'existe': False, 'datos': None}
            
    except Exception as e:
        print(f"Error conectando a la API: {e}")
        return {'existe': False, 'datos': None} # En caso de error, asumimos que no se pudo verificar