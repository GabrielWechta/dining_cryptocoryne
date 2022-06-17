"""Client application - for every participant."""
import argparse

from . import Client


def __parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process input to Client.")

    parser.add_argument(
        "--always-vote",
        type=str,
        default=None,
        choices=["yes", "no"],
        help="Specify what this client (participant) " "should always vote.",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = __parse_args()
    always_vote = args.always_vote

    client = Client(always_vote=always_vote)
    client.run()
