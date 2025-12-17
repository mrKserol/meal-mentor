import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get("/sample/")
def sample(offer_ids: str) -> dict:
    """Return the last offer in the list"""
    # Parse offer IDs
    offers_ids = [int(offer) for offer in offer_ids.split(",")]

    # Pick the last offer ID
    offer_id = offers_ids[-1]

    # Prepare response
    response = {
        "offer_id": offer_id,
    }

    return response


def main() -> None:
    """Run application"""
    uvicorn.run("main:app", host="localhost")


if __name__ == "__main__":
    main()
