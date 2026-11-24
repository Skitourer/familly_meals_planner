"""Lancement du serveur : ``uv run repas`` (production : voir le Dockerfile)."""

import argparse

import uvicorn


def main() -> None:
    analyseur = argparse.ArgumentParser(description="Serveur Menu Famille")
    analyseur.add_argument("--hote", default="127.0.0.1")
    analyseur.add_argument("--port", type=int, default=8000)
    options = analyseur.parse_args()
    uvicorn.run(
        "repas.application:creer_application",
        factory=True,
        host=options.hote,
        port=options.port,
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
