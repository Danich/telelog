import argparse
import logging

from chatparser import ChatParser


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('data_dump', help='Path to file with json dump')
    parser.add_argument('-i', dest='interpolation', help='Interpolate by X days', type=int, default=1, required=False)
    parser.add_argument('-o', dest='output', help='Graph output file', type=str, required=False)
    parser.add_argument('-u', dest='users', help='Show graphs for users', required=False, nargs='*')
    return parser


def main(arguments):
    logging.basicConfig(level=logging.INFO)

    chat_parser = ChatParser(arguments.interpolation, arguments.users, arguments.output)
    chat_parser.load_data(arguments.data_dump)
    chat_parser.run()


if __name__ == '__main__':
    argument_parser = make_parser()
    args = argument_parser.parse_args()
    main(args)
