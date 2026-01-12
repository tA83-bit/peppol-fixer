import streamlit as st
import io
import zipfile
import re

def fix_xml_minimal_changes(xml_text):
    changed = False
    log_messages = []
    
    # 1. Zoek het BTW-nummer in de AccountingCustomerParty
    customer_match = re.search(r'<cac:AccountingCustomerParty>.*?</cac:AccountingCustomerParty>', xml_text, re.DOTALL)
    if not customer_match:
        return xml_text, False, ["FOUT: Geen AccountingCustomerParty gevonden"]
    
    customer_section = customer_match.group(0)
    
    # Zoek het 9925 BTW nummer
    vat_match = re.search(r'<cbc:EndpointID[^>]*schemeID="9925"[^>]*>(.*?)</cbc:EndpointID>', customer_section)
    
    if vat_match:
        original_vat = vat_match.group(1).strip()
        # Maak de 0208 versie (zonder BE, zonder punten)
        clean_vat = original_vat.replace('BE', '').replace('.', '').strip()
        
        # STAP A: Voeg PartyTaxScheme toe
        if '<cac:PartyTaxScheme>' not in customer_section:
            tax_scheme_xml = f'''<cac:PartyTaxScheme>
        <cbc:CompanyID>{original_vat}</cbc:CompanyID>
        <cac:TaxScheme>
          <cbc:ID>VAT</cbc:ID>
        </cac:TaxScheme>
      </cac:PartyTaxScheme>\n      '''
            if '<cac:PartyLegalEntity>' in customer_section:
                new_customer_section = customer_section.replace('<cac:PartyLegalEntity>', tax_scheme_xml + '<cac:PartyLegalEntity>')
                xml_text = xml_text.replace(customer_section, new_customer_section)
                customer_section = new_customer_section
                changed = True
                log_messages.append(f"Toegevoegd: PartyTaxScheme voor {original_vat}")

        # STAP B: Vervang 9925 door 0208
        old_endpoint = vat_match.group(0)
        new_endpoint = re.sub(r'schemeID="9925"', 'schemeID="0208"', old_endpoint)
        new_endpoint = new_endpoint.replace(original_vat, clean_vat)
        
        if old_endpoint != new_endpoint:
            new_customer_section = customer_section.replace(old_endpoint, new_endpoint)
            xml_text = xml_text.replace(customer_section, new_customer_section)
            changed = True
            log_messages.append(f"Aangepast: EndpointID 9925 -> 0208 ({clean_vat})")

    return xml_text, changed, log_messages

# --- Streamlit Interface ---
st.set_page_config(page_title="Peppol Minimal Fixer", page_icon="🇧🇪")
st.title("🇧🇪 Peppol XML Fixer")
st.info("Deze versie past alleen de noodzakelijke regels aan en houdt een logboek bij.")

uploaded_files = st.file_uploader("Upload XML bestanden", type="xml", accept_multiple_files=True)

if uploaded_files:
    zip_buffer = io.BytesIO()
    success_count = 0
    processing_logs = [] # Lijst om alle logs in te verzamelen
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for uploaded_file in uploaded_files:
            raw_content = uploaded_file.read().decode('utf-8')
            
            fixed_content, was_changed, logs = fix_xml_minimal_changes(raw_content)
            
            zip_file.writestr(uploaded_file.name, fixed_content.encode('utf-8'))
            
            if was_changed:
                success_count += 1
                processing_logs.append({"file": uploaded_file.name, "status": "Gecorrigeerd", "details": logs})
            else:
                processing_logs.append({"file": uploaded_file.name, "status": "Geen wijziging", "details": ["Bestand voldeed al aan de regels."]})

    # Toon overzicht van de logs
    st.subheader("Verwerkingsverslag")
    for entry in processing_logs:
        icon = "✅" if entry["status"] == "Gecorrigeerd" else "ℹ️"
        with st.expander(f"{icon} {entry['file']} - {entry['status']}"):
            for detail in entry["details"]:
                st.write(f"- {detail}")

    if success_count > 0:
        zip_buffer.seek(0)
        st.divider()
        st.download_button(
            label=f"📥 Download {success_count} aangepaste bestanden (ZIP)",
            data=zip_buffer,
            file_name="peppol_verwerkt.zip",
            mime="application/zip"
        )
      
