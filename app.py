import streamlit as st
import re
import base64
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code39
from reportlab.lib.units import mm
from io import BytesIO

# --- SEITEN-KONFIGURATION ---
# "layout='wide'" macht die App breiter, damit das PDF besser reinpasst
st.set_page_config(page_title="Barcode Lieferschein Tool", page_icon="📦", layout="wide")

def extract_numbers(text):
    auftrag_match = re.search(r"Auftrags-Nr[\s\S]*?(\d{6,})", text)
    ls_match = re.search(r"Lieferschein[\s\S]*?(PA-\d+)", text)
    return (auftrag_match.group(1) if auftrag_match else None, 
            ls_match.group(1) if ls_match else None)

def create_barcode_overlay(auftrag, lieferschein):
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(210*mm, 297*mm))
    
    # --- NEUE POSITIONIERUNG ---
    x_pos = 145 * mm 
    # y_start weiter nach oben geschoben (von 270 auf 282)
    y_start = 282 * mm

    def draw_bc(text, y, label):
        if text:
            bc = code39.Standard39(text.upper(), barWidth=0.4*mm, barHeight=13*mm, checksum=0)
            # Schriftart minimal verkleinert, damit es kompakter wirkt
            can.setFont("Helvetica-Bold", 10) 
            can.drawString(x_pos, y + 14*mm, f"{label} {text.upper()}")
            bc.drawOn(can, x_pos, y)

    # Abstand zwischen den Barcodes verringert (von 30mm auf 21mm)
    draw_bc(auftrag, y_start, "Auftrag:")
    draw_bc(lieferschein, y_start - 21*mm, "Lieferschein:")
    
    can.save()
    packet.seek(0)
    return packet

# --- WEB-OBERFLÄCHE ---
st.title("📦 Barcode Lieferschein Tool")
st.markdown("Dieses Tool liest automatisch Auftrags- und Lieferscheinnummern aus hochgeladenen Dokumenten aus und platziert die entsprechenden Barcodes platzsparend oben rechts.")

# Neues, neutrales Wording
uploaded_file = st.file_uploader("PDF Lieferschein hochladen", type="pdf")

if uploaded_file is not None:
    try:
        reader = PdfReader(uploaded_file)
        page_text = reader.pages[0].extract_text()
        
        nr_auftrag, nr_ls = extract_numbers(page_text)
        
        if nr_auftrag or nr_ls:
            st.success(f"✅ Nummern erfolgreich erkannt! Auftrag: **{nr_auftrag}** | Lieferschein: **{nr_ls}**")
            
            writer = PdfWriter()
            overlay_pdf = PdfReader(create_barcode_overlay(nr_auftrag, nr_ls))
            
            for i, page in enumerate(reader.pages):
                if i == 0:
                    page.merge_page(overlay_pdf.pages[0])
                writer.add_page(page)
            
            output_pdf = BytesIO()
            writer.write(output_pdf)
            output_pdf.seek(0)
            
            st.markdown("---")
            
            # Button zum klassischen Herunterladen bleibt als Backup
            st.download_button(
                label="⬇️ Fertiges Dokument mit Barcodes herunterladen",
                data=output_pdf,
                file_name=f"BARCODED_{uploaded_file.name}",
                mime="application/pdf"
            )
            
            st.markdown("### Vorschau des fertigen Dokuments:")
            # --- NEU: PDF direkt im Browser anzeigen ---
            base64_pdf = base64.b64encode(output_pdf.getvalue()).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            
        else:
            st.warning("⚠️ Es konnten keine Auftrags- oder Lieferscheinnummern im PDF gefunden werden.")
            
    except Exception as e:
        st.error(f"❌ Ein Fehler ist aufgetreten: {e}")
