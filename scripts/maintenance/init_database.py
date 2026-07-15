from core.database import Database


def main():

    db = Database()

    db.initialize()

    db.close()


if __name__ == "__main__":
    main()