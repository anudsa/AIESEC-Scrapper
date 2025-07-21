from lxml import html
import requests
import pandas as pd
import ObtenFechas 
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os # Importa el módulo os para manejar rutas de archivos

# Se crean los XPaths de los campos que se pueden conseguir de la página estática.
xpaths = {
    "Program": "/html/body/div[2]/main/div/div[1]/div[1]/div[1]/div[2]/div[2]/div[1]/div/div[2]/h3",
    "Backgrounds": "/html/body/div[2]/main/div/div[1]/div[1]/div[1]/div[2]/div[2]/div[3]/div/div[2]/h3",
    "Nombre_opp": "/html/body/div[2]/main/div/div[1]/div[1]/div[1]/div[2]/div[1]/div/div/div[1]/h3",
    "Empresa": "/html/body/div[2]/main/div/div[1]/div[1]/div[1]/div[2]/div[1]/div/div/div[2]/text()[1]",
    "Host_entity": "/html/body/div[2]/main/div/div[1]/div[1]/div[1]/div[2]/div[1]/div/div/div[2]/text()[2]",
    "Salario": "/html/body/div[2]/main/div/div[1]/div[1]/div[1]/div[2]/div[2]/div[4]/div/div[2]/h3/span",
    "Dias_de_proceso": "/html/body/div[2]/main/div/div[1]/div[1]/div[6]/div/div[2]/div[1]/span/b/text()[1]",
    "Idiomas": "/html/body/div[2]/main/div/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/div/div[2]/h3",
    "Horario": "/html/body/div[2]/main/div/div[1]/div[1]/div[4]/div/div[2]/div[2]"
}

def scrape_opportunity_lxml(url):
    """
    Función que obtiene los datos para un solo enlace.
    """
    data = {"Link": url}
    try:
        response = requests.get(url, timeout=10) # Tiene un timeout en caso de tardar en hacer la respuesta.
        response.raise_for_status() # Lanza errores encontrados
        tree = html.fromstring(response.content)
        
        for field, path in xpaths.items():
            nodes = tree.xpath(path)
            if not nodes:
                data[field] = "" # Cadena vacía si no se encuentra el nodo
            else:
                node = nodes[0]
                data[field] = node.text_content().strip() if hasattr(node, 'text_content') else str(node).strip()
        return data
    except requests.exceptions.RequestException as e:
        print(f"  [lxml] Error al obtener respuesta de enlace {url}: {e}")
        # Añade mensaje genérico en caso de no cargar la página
        return {field: (url if field == "Link" else "Error al cargar la página")
                for field in list(xpaths.keys()) + ["Link"]}

def parse_date_info(playwright_date_info_raw):
    """Analiza la cadena de texto cruda obtenida de `ObtenFechas.find_dates_in_html` y la convierte en un diccionario."""
    playwright_date_data = {
        "Start_Date": "N/A",
        "End_Date": "N/A",
        "Date_Range": "N/A", 
        "Interval_Months": "N/A", 
        "Apply_Before_Date": "N/A"
    }

    if isinstance(playwright_date_info_raw, str):
        start_date_match = re.search(r"Start Date:\s*(\d{1,2}\s*[A-Za-z]{3},\s*\d{4})", playwright_date_info_raw)
        if start_date_match:
            playwright_date_data["Start_Date"] = start_date_match.group(1).strip()
        
        end_date_match = re.search(r"End Date:\s*(\d{1,2}\s*[A-Za-z]{3},\s*\d{4})", playwright_date_info_raw)
        if end_date_match:
            playwright_date_data["End_Date"] = end_date_match.group(1).strip()
        
        apply_before_match = re.search(r"Apply Before Date:\s*(\d{1,2}\s*[A-Za-z]{3},\s*\d{4})", playwright_date_info_raw)
        if apply_before_match:
            playwright_date_data["Apply_Before_Date"] = apply_before_match.group(1).strip()

        try:
            if playwright_date_data["Start_Date"] != "N/A" and playwright_date_data["End_Date"] != "N/A":
                start_date_obj = datetime.strptime(playwright_date_data["Start_Date"], '%d %b, %Y')
                end_date_obj = datetime.strptime(playwright_date_data["End_Date"], '%d %b, %Y')
                
                delta = relativedelta(end_date_obj, start_date_obj)
                total_months = delta.years * 12 + delta.months
                playwright_date_data["Interval_Months"] = f"{total_months} meses" 
                playwright_date_data["Date_Range"] = f"{playwright_date_data['Start_Date']} - {playwright_date_data['End_Date']}"
        except ValueError:
            playwright_date_data["Date_Range"] = "Error de cálculo"
            playwright_date_data["Interval_Months"] = "Error de cálculo"
    
    return playwright_date_data

def process_single_url(url_to_scrape):
    """Procesa una única URL, extrae sus datos y devuelve un DataFrame."""
    print(f"\n--- Procesando URL única: {url_to_scrape} ---")
    
    lxml_data = scrape_opportunity_lxml(url_to_scrape)
    
    print(f"Obteniendo contenido de: {url_to_scrape}")
    html_content_from_playwright = ObtenFechas.get_aiesec_opportunity_content_with_playwright(url_to_scrape)

    playwright_date_info_raw = ObtenFechas.find_dates_in_html(html_content_from_playwright)
    playwright_date_data = parse_date_info(playwright_date_info_raw)
    
    merged_data = {**lxml_data, **playwright_date_data}
    return pd.DataFrame([merged_data])

def process_multiple_urls(urls_to_scrape):
    """Procesa múltiples URLs, extrae sus datos y devuelve un DataFrame."""
    records = []
    for url in urls_to_scrape:
        print(f"\n--- Procesando: {url} ---")
        
        lxml_data = scrape_opportunity_lxml(url)
        
        print(f"Obteniendo contenido de: {url}...")
        html_content_from_playwright = ObtenFechas.get_aiesec_opportunity_content_with_playwright(url)

        playwright_date_info_raw = ObtenFechas.find_dates_in_html(html_content_from_playwright)
        playwright_date_data = parse_date_info(playwright_date_info_raw)
        
        records.append({**lxml_data, **playwright_date_data})
    return pd.DataFrame(records)

if __name__ == "__main__":
    df = pd.DataFrame() # Inicializa un dataframe vacío
    output_filename = "" # Inicializa el nombre del archivo
    full_output_path = "" # Variable para almacenar la ruta completa

    while True:
        print("\n")
        print("1. Extraer datos de una única URL")
        print("2. Extraer datos de varias URLs")
        print("3. Salir")
        
        choice = input("Por favor, introduce tu elección (1, 2 o 3): ").strip()

        if choice == '1':
            url_input = input("Introduce la URL de la oportunidad: ").strip()
            if url_input and url_input.startswith("http"):
                # Extrae el ID de la oportunidad de la URL para el nombre de archivo.
                opportunity_id_match = re.search(r'/(\d+)$', url_input)
                opportunity_id = opportunity_id_match.group(1) if opportunity_id_match else "unknown_id"
                
                df = process_single_url(url_input)
                # Crea el nombre del archivo dinámicamente
                output_filename = f'oportunidad_{opportunity_id}.csv' 
            else:
                print("URL no válida. Por favor, asegúrate de que empieza con 'http' o 'https' y que no está vacía.")
            break 
        
        elif choice == '2':
            print("\n--- ¡Importante! Formato de entrada para URLs múltiples ---")
            print("Puedes pegar varias URLs separadas por espacios, comas, saltos de línea,")
            print("o incluso pegarlas una después de otra sin separación (el programa las detectará).")
            print("Asegúrate de que cada URL empiece con 'http' o 'https'.")
            urls_input_raw = input("Introduce las URLs: \n").strip()
            
            # Regex para separar urls pegados juntos
            url_pattern = re.compile(r'(https?://aiesec\.org/opportunity/(?:global-talent|global-teacher)/\d+)')
            urls_list = [u.strip() for u in url_pattern.findall(urls_input_raw) if u.strip()]

            if urls_list:
                print(f"Se detectaron {len(urls_list)} URLs. Iniciando extracción...")
                df = process_multiple_urls(urls_list)
                output_filename = 'oportunidades_multiples.csv'
            else:
                print("No se detectaron URLs válidas. Por favor, intenta de nuevo y asegúrate de que las URLs empiecen con 'http' o 'https'.")
            break

        elif choice == '3':
            print("Saliendo del programa.")
            break
        else:
            print("Elección no válida. Por favor, introduce 1, 2 o 3.")
    
    # Procesamiento de formato final
    if not df.empty:
        # Se renombran columnas en español
        df = df.rename(columns={
            "Host_entity": "país_anfitrión", 
            "Start_Date": "Fecha_inicio",
            "End_Date": "Fecha_final",
            "Date_Range": "Fechas_rango",
            "Interval_Months": "Duración", 
            "Apply_Before_Date": "Fecha_aplicacion_final"
        })

        # Se añade la columna con el mensaje dinámicamente
        df['mensaje'] = df.apply(lambda row: f"""Hola
Te invitamos a aplicar a la siguiente oportunidad:

🌎 Lugar: {row['país_anfitrión']}
🏢 Empresa: {row['Empresa']}
📌 Nombre de la oportunidad: {row['Nombre_opp']}
💡 Área: {row['Program']}
💵 Sueldo: {row['Salario']}
💬 Idiomas: {row['Idiomas']}
📅 Fechas de la pasantía {row['Fechas_rango']}

Para conocer todos los requisitos y postulación entra a: {row['Link']}
Recuerda avisar a cualquier administradora del grupo si aplicas a alguna de nuestras oportunidades para dar seguimiento a tu proceso de selección""", axis=1)

        # Se confirma el orden de las columnas en el dataframe
        column_order = [
            "Link", "Nombre_opp", "Empresa", "país_anfitrión", "Program", "Backgrounds",
            "Salario", "Dias_de_proceso", "Idiomas", "Horario",
            "Fecha_inicio", "Fecha_final", "Fechas_rango", "Duración", "Fecha_aplicacion_final",
            "mensaje" 
        ]

        # Ordenamiento final de verificación
        final_column_order = [col for col in column_order if col in df.columns]
        for col in df.columns: 
            if col not in final_column_order:
                final_column_order.append(col)
        df = df[final_column_order]

        # Obtiene la ruta completa del directorio actual del script
        current_directory = os.path.dirname(os.path.abspath(__file__))
        # Combina el directorio actual con el nombre del archivo de salida
        full_output_path = os.path.join(current_directory, output_filename)

        df.to_csv(full_output_path, index=False, encoding='utf-8-sig') 
        print(f"\n¡Extracción completada! Datos guardados la ruta: '{full_output_path}'")
    elif choice != '3': 
        print("\nNo se pudo extraer ningún dato.")