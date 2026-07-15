from pathlib import Path
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import SubElement

from workout.models import Workout


class ZwoExporter:

    def export(
        self,
        workout: Workout,
        directory: Path,
    ) -> Path:

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file = directory / f"{workout.name}.zwo"

        root = Element("workout_file")

        SubElement(root, "author").text = "Athlete Platform"

        SubElement(root, "name").text = workout.name

        SubElement(root, "description").text = workout.description

        SubElement(root, "sportType").text = "bike"

        workout_xml = SubElement(root, "workout")

        for block in workout.blocks:

            if block.name.lower() == "warmup":

                SubElement(

                    workout_xml,

                    "Warmup",

                    Duration=str(block.duration),

                    PowerLow=f"{block.power_from:.2f}",

                    PowerHigh=f"{block.power_to:.2f}",

                )

                continue

            if block.name.lower() == "cooldown":

                SubElement(

                    workout_xml,

                    "Cooldown",

                    Duration=str(block.duration),

                    PowerLow=f"{block.power_from:.2f}",

                    PowerHigh=f"{block.power_to:.2f}",

                )

                continue

            for _ in range(block.repeat):

                SubElement(

                    workout_xml,

                    "SteadyState",

                    Duration=str(block.duration),

                    Power=f"{(block.power_from + block.power_to) / 2:.2f}",

                )

        ElementTree(root).write(

            file,

            encoding="utf-8",

            xml_declaration=True,

        )

        return file