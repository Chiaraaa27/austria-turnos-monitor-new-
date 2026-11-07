import os
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
        headers={"Title": "Posible turno Austria Working Holiday"},
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
            # No asumimos que la ausencia del mensaje rojo significa que haya turnos.
            # Inspeccionamos controles habilitados dentro de la página del calendario.
            controles = page.locator(
                'input[type="radio"]:enabled, '
                'input[type="checkbox"]:enabled, '
                'select:enabled, '
                'button:enabled, '
                'a[href]'
            )
            candidatos = []
            for i in range(min(controles.count(), 100)):
                control = controles.nth(i)
                etiqueta = (control.get_attribute("aria-label") or "") + " " + (
                    control.get_attribute("value") or ""
                ) + " " + (control.inner_text(timeout=2000) or "")
                etiqueta = etiqueta.strip()
                if any(x in etiqueta.lower() for x in ("reservar", "seleccionar cita", "elegir hora")):
                    candidatos.append(etiqueta)
            if candidatos:
                print("Posible opción de reserva detectada:", candidatos[:3])
                avisar("POSIBLE TURNO Working Holiday Austria. Verificá el sitio oficial: " + URL)
            else:
                print("Calendario diferente al habitual, pero sin opción de reserva confirmada. Sin alerta.")

        print("URL final:", page.url)
    except Exception as error:
        print("ERROR al revisar:", error)
        print("No se envió ninguna alerta.")
    finally:
        browser.close()
