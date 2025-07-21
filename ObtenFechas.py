import asyncio
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from datetime import datetime

def get_aiesec_opportunity_content_with_playwright(url):
    """
    Usa Playwright para cargar la página, esperar a que el contenido dinámico cargue,
    y luego devuelve el contenido HTML.
    """
    try:
        with sync_playwright() as p:
            # Se puede elegir 'chromium', 'firefox', o 'webkit'
            browser = p.chromium.launch(headless=True) 
            page = browser.new_page()
            
            # Navega a la URL
            page.goto(url, wait_until='networkidle') # Espera hasta que la red esté inactiva (contenido cargado)
            
            # Se usa el selector del div tomado del html
            try:
                page.wait_for_selector('div.font-bold.text-\\[16px\\]', timeout=15000) # Espera 15 segundos
            except Exception as e:
                print(f"Advertencia: El selector de fecha no apareció a tiempo: {e}. Intentando continuar...")
            
            html_content = page.content() # Obtiene el HTML renderizado
            browser.close()
            return html_content
    except Exception as e:
        print(f"Error con Playwright: {e}")
        return None

def find_dates_in_html(html_content):
    """
    Busca las fechas dentro del contenido HTML (obtenido dinámicamente)
    y usa expresiones regulares para extraerlas.
    """
    if not html_content:
        return "No se pudo obtener el contenido HTML para buscar las fechas."

    soup = BeautifulSoup(html_content, 'html.parser')

    results = []

    # Intenta encontrar el div con la clase exacta donde está el rango de fechas
    date_range_div = soup.find('div', class_='font-bold text-[16px]')
    if date_range_div:
        full_text_block = date_range_div.get_text(strip=True)
        # Patrón para "DD Mon, YYYY - DD Mon, YYYY"
        date_range_pattern = re.compile(r'(\d{1,2}\s*[A-Za-z]{3},\s*\d{4})\s*-\s*(\d{1,2}\s*[A-Za-z]{3},\s*\d{4})')
        main_date_match = date_range_pattern.search(full_text_block)
        if main_date_match:
            results.append(f"Start Date: {main_date_match.group(1).strip()}")
            results.append(f"End Date: {main_date_match.group(2).strip()}")
    else:
        print("Advertencia: No se encontró el bloque que contiene la fecha")

    # Busca la fecha de "Apply before" en todo el texto de la página,
    full_page_text = soup.get_text(separator=' ', strip=True)
    apply_before_pattern = re.compile(r'Apply before\s*(\d{1,2}\s*[A-Za-z]{3},\s*\d{4})')
    apply_before_match = apply_before_pattern.search(full_page_text)
    if apply_before_match:
        results.append(f"Apply Before Date: {apply_before_match.group(1).strip()}")
    else:
        print("Advertencia: No se encontró la fecha 'Apply before'.")

    if results:
        return "\n".join(results)
    else:
        # Si no se encuentra nada con los selectores y regex específicos, se hace una búsqueda más general en todo el texto.
        print("Falló la extracción específica, intentando búsqueda general de fechas...")
        
        # Patrón más general para cualquier fecha en formato "DD Mon, YYYY"
        general_date_pattern = re.compile(r'\d{1,2}\s*[A-Za-z]{3},\s*\d{4}')
        
        found_general_dates = general_date_pattern.findall(full_page_text)
        if found_general_dates:
            return "Fechas generales encontradas (podrían no ser las exactas): " + ", ".join(found_general_dates)
        else:
            return "No se encontraron fechas en el contenido HTML."

if __name__ == "__main__":
    # Ejemplo de uso (no se ejecuta al importarse como módulo)
    url = "https://aiesec.org/opportunity/global-talent/1326094"
    
    print(f"Obteniendo contenido de: {url} usando Playwright...\n")

    html_content = get_aiesec_opportunity_content_with_playwright(url)

    if html_content:
        print("--- Contenido HTML renderizado (primeras 2000 caracteres) ---")
        # Playwright obtiene el HTML completo renderizado, puede ser muy largo.
        print(html_content[:2000])
        print("\n--- Fin del contenido HTML ---")

        print("\n--- Intentando encontrar las fechas en el HTML renderizado ---")
        date_info = find_dates_in_html(html_content)
        print(date_info)
    else:
        print("No se pudo obtener el contenido de la página usando Playwright.")