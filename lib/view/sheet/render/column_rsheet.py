# Copyright 2013-2018 Aerospike, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from lib.view import terminal

from ..const import FieldAlignment
from .base_rsheet import BaseRField, BaseRSheet, BaseRTupleField


class ColumnRSheet(BaseRSheet):
    # ==========================================================================
    # Required overrides.

    def do_create_tuple_field(self, field, groups):
        return RTupleFieldColumn(self, field, groups)

    def do_create_field(self, field, groups, parent_key=None):
        return RFieldColumn(self, field, groups, parent_key=parent_key)

    def do_render(self):
        rfields = self.visible_rfields
        n_records = self.n_records

        try:
            n_title_lines = max(rfield.n_title_lines for rfield in rfields)
        except ValueError:
            # Sheet is empty.
            return ''

        render = []

        # Render field titles.
        title_width = sum(rfield.width for rfield in rfields) + (
            len(rfields) - 1) * len(self.decl.separator)

        self._do_render_title(render, title_width)
        self._do_render_description(render, title_width, title_width - 10)

        for line_num in range(n_title_lines):
            render.append(self.decl.formatted_separator.join(
                rfield.get_title_line(line_num) for rfield in rfields))

        # Render fields.
        n_groups = 0 if not rfields else rfields[0].n_groups
        has_aggregates = any(rfield.has_aggregate() for rfield in rfields)

        for group_ix in range(n_groups):
            n_entries = rfields[0].n_entries_in_group(group_ix)

            for entry_ix in range(n_entries):
                row = [rfield.entry_cell(group_ix, entry_ix)
                       for rfield in rfields]
                render.append(self.decl.formatted_separator.join(row))

            if has_aggregates:
                row = [rfield.aggregate_cell(group_ix) for rfield in rfields]
                render.append(self.decl.formatted_separator.join(row))

        self._do_render_n_records(render, n_records)

        return "\n".join(render) + "\n"

    # ==========================================================================
    # Other methods.

    def _do_render_title(self, render, width):
        filler = self.decl.title_fill

        t = self.title.center(width, filler)

        if len(t) > 0:
            if not t.startswith(filler):
                t = filler + t
            if not t.endswith(filler):
                t += filler

        t = terminal.bold() + t + terminal.unbold()

        render.append(t)

    def _do_render_description(self, render, line_width, desc_width):
        if self.description is None or self.description == '':
            return []

        tdesc = self.description[:].split(' ')
        lines = []
        words = []

        while tdesc != []:
            words.append(tdesc.pop(0))
            line = ' '.join(words)

            if len(line) >= desc_width:
                if len(words) > 1:
                    tdesc.insert(0, words.pop())
                    line = ' '.join(words)

                words = []
                lines.append(line)
        else:
            if words:
                line = ' '.join(words)
                lines.append(line)

        description = [terminal.dim() + l.center(line_width) + terminal.reset()
                       for l in lines]
        description = '\n'.join(description)

        render.append(description)

    def _do_render_n_records(self, render, n_records):
        render.append(
            terminal.dim() + 'Number of rows: {}'.format(n_records) +
            terminal.undim())


class RTupleFieldColumn(BaseRTupleField):
    # ==========================================================================
    # Optional overrides.

    def do_prepare(self):
        """prepare is called after all fields have been initialized."""
        self._do_prepare_find_width()

        for subfield in self.visible:
            subfield.ready()

        self._do_prepare_count_title_lines()

    # ==========================================================================
    # Other methods.

    def _do_prepare_find_width(self):
        sub_fields_width = sum(sub.width for sub in self.visible)
        separators_width = len(self.rsheet.decl.separator) * (
            len(self.visible) - 1)
        min_width = max(map(len, self.decl.title.split(' ')))

        self.width = max((
            # Visible subfield width with separators.
            sub_fields_width + separators_width,
            # Min group title width.
            min_width))

        self._do_prepare_title()

        line_len = max(map(len, self.title_lines))

        # At least 2 empty characters are needed to display a '-' on either side
        # of title.
        if self.width == line_len:
            self.width += 2
            self._do_prepare_title()
        elif self.width - 1 == line_len:
            self.width += 1
            self._do_prepare_title()

        if self.width - separators_width > sub_fields_width:
            # Split the extra space across all visible subfield.
            diff = (self.width - separators_width) - sub_fields_width
            share = diff // len(self.visible)
            extra = diff % len(self.visible)

            for subfield in self.visible:
                addto = share

                if extra > 0:
                    addto += 1
                    extra -= 1

                subfield.width += addto

    def _do_prepare_title(self):
        # NOTE - Same as RFieldColumn.
        if len(self.decl.title) <= self.width:
            self.title_lines = [self.decl.title]
            self.n_title_lines = 1
            return

        words = self.decl.title.split(' ')
        lines = []
        line = [words[0]]
        cur_len = len(line[0])

        for word in words[1:]:
            if len(word) + cur_len < self.width:
                line.append(word)
                cur_len += len(word) + 1  # add one for a space
            else:
                lines.append(' '.join(line))
                cur_len = len(word)
                line = [word]

        if line:
            lines.append(' '.join(line))

        self.title_lines = lines

    def _do_prepare_count_title_lines(self):
        self.n_title_lines = max(
            sub.n_title_lines for sub in self.visible) + len(self.title_lines)

    def get_title_line(self, line_num):
        try:
            line = self.title_lines[line_num]
        except IndexError:
            sub_line = line_num - len(self.title_lines)
            line = self.rsheet.decl.formatted_separator.join(
                sub.get_title_line(sub_line) for sub in self.visible)

            return line

        line = line.center(self.width, self.rsheet.decl.subtitle_fill)
        return terminal.bold() + line + terminal.unbold()

    def entry_cell(self, group_ix, entry_ix):
        return self.rsheet.decl.formatted_separator.join(
            sub.entry_cell(group_ix, entry_ix) for sub in self.visible)

    def aggregate_cell(self, group_ix):
        return self.rsheet.decl.formatted_separator.join(
            sub.aggregate_cell(group_ix) for sub in self.visible)


class RFieldColumn(BaseRField):
    # ==========================================================================
    # Optional overrides.

    def do_prepare(self):
        """prepare is called after all fields have been initialized."""
        self._do_prepare_find_width()

        if self.parent_key is None:
            self.ready()
        # else - Parent will call ready when it is ready.

    # ==========================================================================
    # Other methods.

    def _do_prepare_find_width(self):
        self.width = max((
            # maximum entry width.
            max(max(map(len, group_converted))
                for group_converted in self.groups_converted),
            # maximum aggregate width.
            max(map(len, self.aggregates_converted)),
            self.decl.min_title_width))

    def ready(self):
        """ready is called after prepare or after a parent has prepared all
        sub-fields"""
        self._ready_title()

    def _ready_title(self):
        if len(self.decl.title) <= self.width:
            self.title_lines = [self.decl.title]
            self.n_title_lines = 1
            return

        words = self.decl.title_words
        lines = []
        line = [words[0]]
        cur_len = len(line[0])

        for word in words[1:]:
            if len(word) + cur_len < self.width:
                line.append(word)
                cur_len += len(word) + 1  # add one for a space
            else:
                lines.append(' '.join(line))
                cur_len = len(word)
                line = [word]

        if line:
            lines.append(' '.join(line))

        self.title_lines = lines
        self.n_title_lines = len(lines)

    def get_title_line(self, line_num):
        try:
            line = self.title_lines[line_num]
            width = self.width

            if self.is_ordered_by:
                orig_width = len(line)
                line = terminal.underline() + line + terminal.ununderline()
                extra_width = len(line) - orig_width
                width += extra_width
        except IndexError:
            line = self.rsheet.decl.subtitle_empty_line
            width = self.width

        return terminal.bold() + line.rjust(width) + terminal.unbold()

    def entry_cell(self, group_ix, entry_ix):
        cell = self._entry_cell_align(
            self.groups_converted[group_ix][entry_ix])
        format_name, formatter = self.entry_format(
            group_ix, entry_ix)

        if formatter is not None:
            cell = formatter(cell)

        return cell

    def _entry_cell_align(self, converted):
        if self.decl.align is FieldAlignment.right:
            return converted.rjust(self.width)
        elif self.decl.align is FieldAlignment.left:
            return converted.ljust(self.width)
        elif self.decl.align is FieldAlignment.center:
            return converted.center(self.width)
        else:
            raise

    def aggregate_cell(self, group_ix):
        cell = self._entry_cell_align(self.aggregates_converted[group_ix])

        if self.aggregates[group_ix] is not None:
            cell = terminal.fg_blue() + cell + terminal.fg_not_blue()

            if self.is_grouped_by:
                cell = terminal.bold() + cell + terminal.unbold()

        return cell
