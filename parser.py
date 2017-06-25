#!/usr/bin/env python3

import re
from colored import fg, bg, attr, style
import os
from collections import defaultdict


IRC_BOLD = "\x02"
IRC_COLOR = "\x03"
IRC_ITALIC = "\x16"
IRC_UNDERLINE = "\x1f"

# See https://pypi.python.org/pypi/colored
WHITE = "white"
DARK_GREY = "grey_23"
BLUE = "blue"
GREEN = "green"
ORANGE = "light_red"
RED = "red"
PURPLE = "plum_4"
OFF_YELLOW = "gold_1"
YELLOW = "yellow"
LIGHT_GREEN = "light_green"
AQUAMARINE = "cyan"
CYAN = "light_cyan"
LIGHT_BLUE = "light_blue"
LIGHT_PURPLE = "light_magenta"
LIGHT_GREY = "dark_gray"
V_LIGHT_GREY = "grey_82"

ircolors = [WHITE, DARK_GREY, BLUE, GREEN, ORANGE, RED, PURPLE, OFF_YELLOW, YELLOW,
            LIGHT_GREEN, AQUAMARINE, CYAN, LIGHT_BLUE, LIGHT_PURPLE, LIGHT_GREY, V_LIGHT_GREY]

TRANSFORM_RE = re.compile(r'(?P<start>[0-9]+)(\-(?P<end>[0-9]+))?(?P<tag>[a-z]+)')


def print_palette():
    """
    Prints out color palette for debugging colors
    """
    for i in range(0, len(ircolors)):
        print("{reset}{num}: {code} {num} {num} {num} {num} {num} "
              .format(reset=style.RESET, num=i, code=bg(ircolors[i])))


def load_file(path):
    with open(path, "rb") as f:
        all_lines = []
        while True:
            line = f.readline()
            if not line:
                break
            try:
                all_lines.append(line.decode("UTF-8").rstrip("\n"))
            except UnicodeDecodeError:
                print("Dropped line: {}".format(line))
        return all_lines


def write_ascii(chatlines, output_dir):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    items = os.listdir(output_dir)
    max_item = 0
    for item in items:
        num = int(item)
        if num > max_item:
            max_item = num
    max_item += 1
    dest_file = os.path.join(output_dir, str(max_item))
    with open(dest_file, "wb") as f:
        for line in chatlines:
            f.write(line.message.encode("UTF-8"))
            f.write("\n".encode("UTF-8"))
    return dest_file


class ChatLine(object):
    """docstring for ChatLine"""

    line_format_re = re.compile(r'^(?P<timestamp>\[[0-9\:]+\]) ((<(?P<nick>[^>]+)>) (?P<message>.+)|(?P<other>.+))')
    formatting_re = re.compile(r'([\x02\x03\x16\x1f])')

    def __init__(self, line):
        self._parts = []

        # Was the line a privmsg or something else?
        self.is_chat = False
        # Was there formatting in the line?
        self.has_format = False
        # Sender nick (if chat)
        self.nick = None
        # Message only
        self.message = None

        self.original = line

    def parse(self):
        line = self._original
        matches = ChatLine.line_format_re.match(line)

        if not matches:
            # Assume it's just a message ready to be formatted
            self.message = line
            self.parse_message_args(line)
        else:
            line_parts = matches.groupdict()

            if line_parts["message"]:
                line = line_parts["message"]
                self.is_chat = True
                self.nick = line_parts["nick"]
                self.message = line_parts["message"]
                self.parse_message_args(self.message)

    def parse_message_args(self, message):
        # Split the line on formatting sequences
        matches = ChatLine.formatting_re.split(message)
        # Anything before a format char isn't formatted
        self._parts.append(matches.pop(0))

        # Read each pair of parts.
        # Each pair is a formatting sequence and the following text
        part_index = 0
        while part_index < len(matches):
            seperator = matches[part_index]
            part = matches[part_index + 1]
            part_index += 2

            if seperator == IRC_COLOR:
                self.has_format = True
                # Try to parse foreground, background colors
                # Can look like:
                # 9,9DATA
                # 10,10DATA or 9,10DATA or 10,9DATA
                # ,10DATA
                # Neither number will look like
                # 09, 00, 01, etc
                colors = [None, None]

                # Check if there is a number
                if part and ChatLine.is_numeric(part[0]):
                    color_digits = part[0]
                    part = part[1:]
                    # Is there another number?
                    if part and ChatLine.is_numeric(part[0]):
                        color_digits_temp = color_digits + part[0]
                        # Are we breaking the "no 09 formatting" rule?
                        if int(color_digits_temp) <= 15:
                            color_digits = color_digits_temp
                            part = part[1:]
                    # We found a valid 1 or 2 digit color!
                    colors[0] = int(color_digits)
                # Is there a comma followed by a number?
                if len(part) >= 2 and part[0] == "," and ChatLine.is_numeric(part[1]):
                    color_digits = part[1]
                    part = part[2:]
                    # Is there a 2nd digit?
                    if part and ChatLine.is_numeric(part[0]):
                        color_digits_temp = color_digits + part[0]
                        # Are we breaking the "no 09 formatting" rule?
                        if int(color_digits_temp) <= 15:
                            color_digits = color_digits_temp
                            part = part[1:]
                    # We found a valid 1 or 2 digit color!
                    colors[1] = int(color_digits)
                # Alter the foreground
                if colors[0] is not None:
                    self._parts.append(fg(ircolors[colors[0]]))
                # Alter the background
                if colors[1] is not None:
                    self._parts.append(bg(ircolors[colors[1]]),)
                # If no valid formatting was found, reset all styles
                if colors[0] is None and colors[1] is None:
                    self._parts.append(style.RESET)

                # if colors[0] is not None:
                #     print(colors[0], end='')
                # if colors[1] is not None:
                #     print(",", end='')
                #     print(colors[1], end='')
            # elif seperator == IRC_BOLD:
            #     self.has_format = True
            #     self._parts.append(attr("bold"))
            # elif seperator == IRC_ITALIC:
            #     pass
            #     # ???
            # elif seperator == IRC_UNDERLINE:
            #     self.has_format = True
            #     self._parts.append(attr("underlined"))

            self._parts.append(part)

    @property
    def formatted(self):
        return ''.join(self._parts)

    def __str__(self):
        return self.formatted

    @property
    def original(self):
        return self._original

    @original.setter
    def original(self, original):
        self._original = original
        self.parse()

    @classmethod
    def is_numeric(self, char):
        i = ord(char)
        return i >= 48 and i <= 57


def parse_logfile(logfile, output_dir):
    # print_palette()

    all_lines = load_file(logfile)

    # Maping of sender nick to lines sent/meta
    # meta is a mapping of
    #     lastseen->lineno(int),    line number the chatter was last seen
    #     lines->list,              string lines of chat
    #     ref -> string             if part of a group, act on this instead

    class Ascii:
        def __init__(self, lastseen, lines, ref):
            self.lastseen = lastseen
            self.lines = []
            self.ref = ref

        def __str__(self):
            return "Ascii(lastseen={}, len(lines)={}, ref={})".format(self.lastseen, len(self.lines), self.ref)

    watched_asciis = {}

    def resolve(input_nic):
        n = watched_asciis[input_nic]
        if n.ref:
            return resolve(n.ref)
        return input_nic

    def clean_refs(input_nic):
        for nickslot_name, nickslot in [i for i in watched_asciis.items()]:
            if nickslot.ref == input_nic:
                del watched_asciis[nickslot_name]

    for lineno in range(0, len(all_lines)):
        line = ChatLine(all_lines[lineno])
        # print(line.nick, line, style.RESET)

        # Do EOF completes
        for nickslot_name, nickslot in [i for i in watched_asciis.items()]:
            if not nickslot.ref and lineno - nickslot.lastseen > 16:
                print("EOF-Completed {}".format(nickslot_name))
                for i in nickslot.lines:
                    print(i.nick, i, style.RESET)
                write_ascii(nickslot.lines, output_dir)
                del watched_asciis[nickslot_name]
                clean_refs(nickslot_name)

        if line.has_format:  # TODO or smells like ascii art
            nickslot_name = line.nick
            nickslot = watched_asciis.get(nickslot_name, None)
            if nickslot:
                nickslot.lastseen = lineno
                if nickslot.ref:
                    nickslot_name = nickslot.ref
                    nickslot = watched_asciis.get(nickslot_name)

                nickslot.lastseen = lineno
                nickslot.lines.append(line)
                continue

            # If:
            # - any of the last 3 lines was formatted
            # - I speak again with formatting in the next X lines,
            # We assume multi-user ascii

            last_3_lines = [ChatLine(i) for i in all_lines[max(lineno - 3, 0):lineno - 1]]
            next_X_lines = [ChatLine(i) for i in all_lines[lineno + 1:lineno + 16]]
            format_in_last = any([i.has_format for i in last_3_lines])
            i_speak_again = any([i.nick == nickslot_name for i in next_X_lines])

            if format_in_last and i_speak_again:
                # Ref onto existing ascii
                last_line = [i for i in last_3_lines if i.has_format][-1]
                target = resolve(last_line.nick)
                watched_asciis[nickslot_name] = Ascii(lineno, [], target)
                watched_asciis[target].lines.append(line)
            else:
                # Start a new ascii
                watched_asciis[nickslot_name] = Ascii(0, [], "")
                watched_asciis[nickslot_name].lines.append(line)
                watched_asciis[nickslot_name].lastseen = lineno

    for nickslot_name, nickslot in watched_asciis.items():
        print("EOL-Completed {}".format(nickslot_name))
        for line in nickslot.lines:
            print(line.nick, line, style.RESET)
        write_ascii(nickslot.lines, output_dir)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="IRC log ascii art exporter toolkit")
    subparser_action = parser.add_subparsers(dest='action', help='action to take')

    parser_parse = subparser_action.add_parser('parse', help='Extract asciis from logs')
    parser_parse.add_argument('-o', '--output-dir', help="Output directory", default="./asciis")
    parser_parse.add_argument('files', nargs="+", help="Input log files")

    parser_insp = subparser_action.add_parser('inspect', help='View files with fomratting')
    parser_insp.add_argument("-l", "--lines", action="store_true", help="Show line numbers")
    parser_insp.add_argument('file', nargs=1, help="Input file")

    parser_split = subparser_action.add_parser('split', help='Split asciis into multiple')
    parser_split.add_argument('file', nargs=1, help="Input file")
    parser_split.add_argument("-p", "--preview", action="store_true", help="Don't write anything")
    parser_split.add_argument('-o', '--output-dir', help="Output directory", default="./asciis")
    parser_split.add_argument("-t", "--sections", nargs="+", help="sections to modify", required=True)
    # TODO write docs for --sections
    # Format is:
    # 0a     associate line 0 with group a
    # 10-20a associate lines 10-20, inclusive, with group a

    args = parser.parse_args()

    if args.action == "parse":
        for item in args.files:
            parse_logfile(item, args.output_dir)

    elif args.action == "inspect":
        lineno = 0
        for line in load_file(args.file[0]):
            if args.lines:
                print("{}\t".format(lineno), end='')
            print(ChatLine(line).formatted + style.RESET)
            lineno += 1

    elif args.action == "split":
        lines = [[None, line] for line in load_file(args.file[0])]
        for t in args.sections:
            spec = TRANSFORM_RE.match(t).groupdict()

            start = int(spec["start"])
            end = int(spec["end"]) if spec["end"] else start

            for i in range(start, end + 1):
                lines[i][0] = spec["tag"]

        grouped = defaultdict(list)
        for tag, line in lines:
            grouped[tag].append(line)

        if None in grouped.keys():
            raise Exception("Not all lines grouped")

        for tag, lines in grouped.items():
            print("Tag {}:".format(tag))
            for line in lines:
                print(ChatLine(line).formatted + style.RESET)
            if not args.preview:
                new_file = write_ascii([ChatLine(i) for i in lines], args.output_dir)
                print("Wrote {}".format(new_file))
            print("\n\n")

        if not args.preview:
            os.unlink(args.file[0])


if __name__ == '__main__':
    main()
