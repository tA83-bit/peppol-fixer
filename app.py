import streamlit as st
import io
import zipfile
import re

def fix_xml_minimal_changes(xml_text):
    changed = False
    log_messages = []
    
    # 1. Zoek de Customer sectie
    customer_match = re.search(r'<cac:AccountingCustomerParty>.*?</cac:AccountingCustomerParty>', xml_text, re.DOTALL)
    if not customer_match:
        return xml_text, False, ["FOUT: Tag <cac:AccountingCustomerParty> niet gevonden."]
    
    customer_section = customer_match.group(0)
    
    # 2. Zoek het 9925 BTW nummer
    vat_match = re.search(r'<cbc:EndpointID[^>]*schemeID="9925"[^>]*>(.*?)</cbc:EndpointID>', customer_section)
    
    if vat_match:
        original_vat = vat_match.group(1).strip()
        # Maak de 0208 versie (zonder BE, zonder punten)
        clean_vat = original_vat.replace('BE', '').replace('.', '').replace(' ', '').strip()
        
        # STAP A: Voeg PartyTaxScheme toe als deze ontbreekt
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
                log_messages.append(f"✅ PartyTaxScheme toegevoegd voor {original_vat}")

        # STAP B: Vervang 9925 door 0208
