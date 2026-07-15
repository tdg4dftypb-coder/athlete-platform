from collectors.apple_health.importer import AppleHealthImporter


def main():

    importer = AppleHealthImporter(
        "data/raw/export.xml"
    )

    importer.run()


if __name__ == "__main__":
    main()