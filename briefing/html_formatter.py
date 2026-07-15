from pathlib import Path

from jinja2 import Environment
from jinja2 import FileSystemLoader

from briefing.models import MorningBriefing


class HtmlFormatter:

    def save(
        self,
        briefing: MorningBriefing,
        filename: str = "reports/morning_briefing.html",
    ):

        Path("reports").mkdir(
            exist_ok=True
        )

        env = Environment(

            loader=FileSystemLoader(
                "briefing/templates"
            )

        )

        template = env.get_template(
            "briefing.html"
        )

        html = template.render(
            briefing=briefing
        )

        Path(filename).write_text(

            html,

            encoding="utf-8",

        )

        print()

        print(f"Saved: {filename}")

        print()