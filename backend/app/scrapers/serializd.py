class SerializdScraper:
    def preflight(self, username: str) -> dict:
        return {"username": username, "is_private": False}
