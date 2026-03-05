#!/usr/bin/env python3
"""Utility script: reset `impresso` flag to False for all ingressos_emitidos.

Run with the project virtualenv activated:

    $ python scripts/reset_impresso.py

It will iterate the collection and update in batches for efficiency.
"""

import os
from pymongo import UpdateMany
from app.config import database


def main():
    db = database.get_database()
    print("Resetting impresso on all ingressos_emitidos...")
    result = db.ingressos_emitidos.update_many(
        {}, {"$set": {"impresso": False}}
    )
    print(f"Matched {result.matched_count}, modified {result.modified_count}")

    print("Updating embedded ingressos inside participantes...")
    # use arrayFilters to reset flag for any element
    result2 = db.participantes.update_many(
        {"ingressos.impresso": {"$exists": True}},
        {"$set": {"ingressos.$[elem].impresso": False}},
        array_filters=[{"elem.impresso": {"$exists": True}}]
    )
    print(f"Participants matched {result2.matched_count}, modified {result2.modified_count}")
    print(f"Matched {result.matched_count}, modified {result.modified_count}")


if __name__ == "__main__":
    main()
