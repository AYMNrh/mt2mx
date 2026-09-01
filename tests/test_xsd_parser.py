from pathlib import Path

from mt2mx.xsd_parser import extract_xsd_inventory


FIXTURE = '''<?xml version="1.0"?>
<xs:schema xmlns="urn:test:demo.001.001.01"
 xmlns:xs="http://www.w3.org/2001/XMLSchema"
 targetNamespace="urn:test:demo.001.001.01" elementFormDefault="qualified">
 <xs:element name="Document" type="Document"/>
 <xs:complexType name="Document"><xs:sequence>
   <xs:element name="Root" type="RootType"/>
 </xs:sequence></xs:complexType>
 <xs:complexType name="RootType"><xs:sequence>
   <xs:element name="Amt" type="Amount"/>
   <xs:choice minOccurs="0">
     <xs:element name="Cd" type="Code"/>
     <xs:element name="Prtry" type="Text"/>
   </xs:choice>
 </xs:sequence></xs:complexType>
 <xs:complexType name="Amount"><xs:simpleContent><xs:extension base="xs:decimal">
   <xs:attribute name="Ccy" type="Code" use="required"/>
 </xs:extension></xs:simpleContent></xs:complexType>
 <xs:simpleType name="Code"><xs:restriction base="xs:string"/></xs:simpleType>
 <xs:simpleType name="Text"><xs:restriction base="xs:string"/></xs:simpleType>
</xs:schema>'''


def test_extracts_paths_choices_and_currency_attribute(tmp_path: Path):
    xsd = tmp_path / "demo.001.001.01.xsd"
    xsd.write_text(FIXTURE, encoding="utf-8")

    result = extract_xsd_inventory(xsd)
    by_path = {row["path"]: row for row in result["rows"]}

    assert result["message_id"] == "demo.001.001.01"
    assert result["root_tag"] == "Root"
    assert "Document/Root/Amt" in by_path
    assert by_path["Document/Root/Amt/@Ccy"]["is_attribute"] is True
    assert by_path["Document/Root/Amt/@Ccy"]["min_occurs"] == "1"
    assert by_path["Document/Root/Cd"]["choice_group"]
    assert by_path["Document/Root/Prtry"]["choice_group"] == by_path["Document/Root/Cd"]["choice_group"]
    assert by_path["Document/Root/Cd"]["min_occurs"] == "0"
