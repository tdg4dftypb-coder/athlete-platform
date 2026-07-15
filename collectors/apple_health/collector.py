from collectors.apple_health.parser import AppleHealthParser


class AppleHealthCollector:

    def __init__(self, export_path):

        self.parser = AppleHealthParser(export_path)

    def load(self):

        root = self.parser.load()

        print(f"Apple Health loaded.")

        print(f"Root tag: {root.tag}")

        print(f"Children: {len(root)}")