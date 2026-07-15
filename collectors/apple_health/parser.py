from xml.etree.ElementTree import iterparse


class AppleHealthParser:

    def __init__(self, xml_path: str):
        self.xml_path = xml_path

    def records(self):

        context = iterparse(self.xml_path, events=("end",))

        for _, element in context:

            if element.tag != "Record":
                continue

            yield {
                "type": element.attrib.get("type"),
                "source_name": element.attrib.get("sourceName"),
                "unit": element.attrib.get("unit"),
                "start_date": element.attrib.get("startDate"),
                "end_date": element.attrib.get("endDate"),
                "value": element.attrib.get("value"),
            }

            element.clear()