import os
import re
import urllib.request
from playwright.sync_api import sync_playwright

URL = "https://appointment.bmeia.gv.at/?Office=buenos-aires"
TOPIC = os.environ.get("NTFY_TOPIC", "").strip()


def avisar(mensaje):
    if not TOPIC:
        print("Falta NTFY_TOPIC; no se envió alerta.")
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}",
        data=mensaje.encode("utf-8"),
        headers={"Title": "Turno Austria Working Holiday"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=15).close()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    try:
        page = browser.new_page(locale="es-AR")
        page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        page.get_by_role("combobox").last.select_option(label="Working Holiday Programm")
        page.get_by_role("button", name="Continuar").click()
        page.get_by_role("button", name="Continuar").click()
        page.wait_for_timeout(1500)
        page.get_by_role("button", name="Continuar").click()
        page.wait_for_load_state("domcontentloaded")

        texto = page.locator("body").inner_text(timeout=15000)
        if "Citas disponibles para" not in texto or "Working Holiday Programm" not in texto:
            print("No se pudo verificar el calendario. Sin alerta.")
        elif "Actualmente no hay fechas disponibles" in texto:
            print("Sin turnos disponibles en la semana mostrada.")
        else:
            horarios = re.findall(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", texto)
            if horarios:
                print("Posible turno detectado. Revisar manualmente.")
                avisar("POSIBLE TURNO Working Holiday Austria. Revisá: " + URL)
            else:
                print("Resultado no concluyente. Sin alerta.")
        print("URL final:", page.url)
    except Exception as error:
        print("ERROR al revisar:", error)
        print("No se envió ninguna alerta.")
    finally:
        browser.close()
