from dataclasses import dataclass
from enum import Enum
from typing import Optional
import re

from diags_parser.logging_configs import get_logger
import logging
from logging import Logger

@dataclass
class LineTuple:
    """
    line: str
    ln: int
    """

    line: str
    ln: int


class LogicalLineIterator:
    def __init__(self, lines: list[LineTuple], log_name: str = ""):
        self.lines = lines
        self.i: int = 0
        self.start_index: int = 0
        self.curr_line: LineTuple = lines[0]
        self._pending_parts: list[LineTuple] = []
        if not log_name:
            self.logger: Logger = get_logger("LineIter", level=logging.INFO)
        else:
            self.logger: Logger = get_logger(log_name, level=logging.INFO)

    def __iter__(self):
        return self

    def reset(self, ln: int = 0):
        self.i = ln
        self.start_index = ln
        self._pending_parts = []

    def get_start_ln(self) -> int:
        idx = self.start_index
        return self.lines[idx].ln

    def get_curr_idx(self) -> int:
        return self.i

    def _scan_with_comment_and_split(
        self,
        line: str,
        split_char: str | None = None,
    ) -> list[str]:
        """
        Scan a line, respecting Fortran-style '!' comments and quotes.
        - Stops scanning when an unquoted '!' is hit.
        - Tracks strings delimited by ' or ".
        - Optionally splits on a given split_char when outside strings.
        """
        in_string = None  # None, "'", or '"'
        parts: list[str] = []
        current: list[str] = []

        i = 0
        while i < len(line):
            c = line[i]
            if c in ('"', "'"):
                if in_string is None:
                    in_string = c
                elif in_string == c:
                    # handle escaped/doubled quote inside string
                    if i + 1 < len(line) and line[i + 1] == c:
                        current.append(c)  # add one quote, skip next
                        i += 1
                    else:
                        in_string = None  # close string
                current.append(c)
            elif c == "!" and in_string is None:
                # comment starts here: stop processing
                break
            elif split_char is not None and c == split_char and in_string is None:
                part = "".join(current).strip()
                if part:
                    parts.append(part)
                current = []
            else:
                current.append(c)
            i += 1

        tail = "".join(current).strip()
        if tail:
            parts.append(tail)

        return parts

    def strip_comment(self) -> str:
        """
        Return the line with comments stripped,
        without any splitting (equivalent to split_char=None, first part).
        """
        line = self.lines[self.i].line
        parts = self._scan_with_comment_and_split(line, split_char=None)
        return parts[0] if parts else ""

    def __next__(self):

        if self._pending_parts:
            self.curr_line = self._pending_parts.pop(0)
            return self.curr_line
        if self.i >= len(self.lines):
            raise StopIteration
        self.start_index = self.i

        cur_ln = self.lines[self.i].ln
        full_line = self.strip_comment()
        full_line = full_line.rstrip("\n").strip()
        num_continuations: int = 1
        while full_line.rstrip().endswith("&"):
            num_continuations += 1
            full_line = full_line.rstrip()[:-1].strip()
            self.i += 1
            if self.i >= len(self.lines):
                self.logger.error("Error-- line incomplete!")
                raise StopIteration
            new_line = self.strip_comment().strip()
            # test if line is just a comment or otherwise empty
            if not new_line:
                full_line += " &"  # re append & so loop goes to next line
            else:
                new_line = regex_preand.sub(" ", new_line)
                full_line += " " + new_line.rstrip("\n")

        # result = (full_line.lower(), self.i)
        self.i += 1

        # semicolon splitting, preserving original ln
        parts = self._scan_with_comment_and_split(full_line,split_char=';')
        # filter out completely empty pieces
        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            # empty after stripping; just yield empty logical line
            self.curr_line = LineTuple(line="", ln=cur_ln)
            return self.curr_line

        # first part is returned now; remaining queued for subsequent __next__ calls
        first_part = parts[0].lower()
        self._pending_parts = [LineTuple(line=p.lower(), ln=cur_ln) for p in parts[1:]]
        self.curr_line = LineTuple(line=first_part, ln=cur_ln)
        return self.curr_line

    def next_n(self, n):
        """Get next n full logical lines."""
        results = []
        for _ in range(n):
            try:
                results.append(next(self))
            except StopIteration:
                break
        return results

    def insert_after(self, stmt: str):
        """
        Inserts after current line and increments subsequent lns
        """
        cur_ln = self.i
        self.lines.insert(cur_ln + 1, LineTuple(line=stmt, ln=cur_ln + 1))
        self.i += 1
        for i in range(cur_ln + 2, len(self.lines)):
            self.lines[i].ln += 1

        return

    def get_curr_line(self):
        if self.i >= len(self.lines):
            return None
        return self.lines[self.i].line

    def has_next(self):
        return self.i < len(self.lines)

    def comment_cont_block(self, index: Optional[int] = None):
        old_index = index if index else self.start_index
        for ln in range(old_index, self.i):
            self.lines[ln].commented = True

    def consume_until(
        self,
        end_pattern: re.Pattern,
        start_pattern: Optional[re.Pattern],
    ) -> tuple[list[LineTuple], int]:

        results: list[LineTuple] = [self.curr_line]
        ln: int = -1
        nesting = 0
        while self.has_next():
            curr_line = next(self)
            full_line = curr_line.line
            start_ln = self.get_start_ln()
            results.append(LineTuple(line=full_line, ln=start_ln))
            if start_pattern and start_pattern.match(full_line):
                nesting += 1
            if end_pattern.match(full_line):
                if nesting == 0:
                    break
                else:
                    nesting -= 1

        return results, ln

    def get_orig_ln(self):
        start_index = self.get_start_ln()
        return self.lines[start_index].ln

    def replace_in_line(
        self,
        lns: list[int],
        pattern: re.Pattern,
        repl_str: str,
        logger: Optional[Logger] = None,
    ):
        if not logger:
            logger = self.logger
        for ln in lns:
            self.i = ln
            full_line = next(self)
            delta_ln = self.i - ln
            m_ = pattern.search(full_line.line)
            if m_:
                for i in range(0, delta_ln + 1):
                    curr_line = self.lines[ln + i].line
                    self.lines[ln + i].line = pattern.sub(repl_str, curr_line)
            else:
                self.logger.error(
                    f"(replace_in_line) FAILED to match {pattern} in \n {full_line}"
                )

        return

    def get_lines(self, regex: re.Pattern) -> list[LineTuple]:
        self.reset()
        res = [lpair for lpair in self if regex.search(lpair.line)]
        self.reset()
        return res


class Precedence(Enum):
    _ = 0
    LOWEST = 1
    EQUALS = 2
    LESSGREATER = 3
    SUM = 4
    PRODUCT = 5
    PREFIX = 6
    BOUNDS = 7
    CALL = 8

