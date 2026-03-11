import streamlit as st
import re
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code39
from reportlab.lib.units import mm
from io import BytesIO

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Barcode Lieferschein Tool", page_icon="📦")

def extract_numbers(text):
    # Die extrem robuste Suche, die alle Umbrüche im Blueprint-Layout meistert
    auftrag_match = re.search(r"Auftrags-Nr[\s\S]*?(\d{6,})", text)
    ls_match = re.search(r"Lieferschein[\s\S]*?(PA-\d+)", text)
    return (auftrag_match.group(1) if auftrag_match else None, 
            ls_match.group(1) if ls_match else None)

def create_barcode_overlay(auftrag, lieferschein):
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(210*mm, 297*mm))
    
    # Position: Oben rechts
    x_pos = 145 * mm 
    y_start = 270 * mm

    def draw_bc(text, y, label):
        if text:
            # 30% vergrößerter Standard39 Barcode
            bc = code39.Standard39(text.upper(), barWidth=0.4*mm, barHeight=13*mm, checksum=0)
            can.setFont("Helvetica-Bold", 12)
            can.drawString(x_pos, y + 15*mm, f"{label} {text.upper()}")
            bc.drawOn(can, x_pos, y)

    draw_bc(auftrag, y_start, "Auftrag:")
    draw_bc(lieferschein, y_start - 30*mm, "Lieferschein:")
    
    can.save()
    packet.seek(0)
    return packet

# --- WEB-OBERFLÄCHE ---
st.title("📦 Barcode Lieferschein Tool")
st.markdown("Ziehen Sie das Original-PDF einfach hier in das Feld. Das Tool liest die Nummern aus und generiert sofort das fertige Dokument.")

# Das Drag & Drop Feld
uploaded_file = st.file_uploader("DATEV-PDF hochladen", type="pdf")

if uploaded_file is not None:
    try:
        # PDF direkt aus dem Browser-Speicher (ohne Festplatte) lesen
        reader = PdfReader(uploaded_file)
        page_text = reader.pages[0].extract_text()
        
        nr_auftrag, nr_ls = extract_numbers(page_text)
        
        if nr_auftrag or nr_ls:
            st.success(f"✅ Nummern erfolgreich erkannt! Auftrag: **{nr_auftrag}** | Lieferschein: **{nr_ls}**")
            
            writer = PdfWriter()
            overlay_pdf = PdfReader(create_barcode_overlay(nr_auftrag, nr_ls))
            
            # Stempelt den Barcode auf die erste Seite
            for i, page in enumerate(reader.pages):
                if i == 0:
                    page.merge_page(overlay_pdf.pages[0])
                writer.add_page(page)
            
            # Fertiges PDF für den Download vorbereiten
            output_pdf = BytesIO()
            writer.write(output_pdf)
            output_pdf.seek(0)
            
            st.markdown("---")
            # Der große Download-Button
            st.download_button(
                label="⬇️ Fertiges PDF herunterladen",
                data=output_pdf,
                file_name=f"BARCODED_{uploaded_file.name}",
                mime="application/pdf"
            )
        else:
            st.warning("⚠️ Es konnten keine Auftrags- oder Lieferscheinnummern im PDF gefunden werden.")
            
    except Exception as e:
        st.error(f"❌ Ein Fehler ist aufgetreten: {e}")