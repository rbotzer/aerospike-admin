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

import traceback
from collections import defaultdict

from ..const import SheetStyle
from .column_rsheet import ColumnRSheet
from .row_rsheet import RowRSheet
from .json_rsheet import JSONRSheet


render_class = {
    SheetStyle.columns: ColumnRSheet,
    SheetStyle.rows: RowRSheet,
    SheetStyle.json: JSONRSheet
}

use_json = False


def set_style_json():
    global use_json
    use_json = True


def render(sheet, title, data_source, style=None, common=None,
           description=None, selectors=None, dyn_aggr=None, dyn_diff=False):
    """
    Arguments:
    sheet       -- The decl.sheet to render.
    title       -- Title for this render.
    data_source -- Dictionary of data_sources to project fields from.

    Keyword Arguments:
    style       -- 'SheetStyle.columns': Output fields as columns.
                   'SheetStyle.rows'   : Output fields as rows.
                   'SheetStyle.json'   : Output sheet as JSON.
    common      -- A dict of common information passed to each entry.
    description -- A description of the sheet.
    selectors   -- List of regular expressions to select which fields from
                   dynamic fields.
    dyn_aggr    -- Aggregate for dynamic fields only have numeric values.
    dyn_diff    -- Only show dynamic fields that aren't uniform.
    """
    # NOTE - Other than the title's suffix, it doesn't change.
    #        Title without suffix could move to decl and suffix be passed in
    #        here. Likewise, if the title moves to decl, the description should
    #        also move.
    tcommon = defaultdict(lambda: None)

    if common is not None:
        tcommon.update(common)

    assert set(sheet.from_sources) - set(data_source.keys()) == set()

    if use_json:
        style = SheetStyle.json
    elif style is None:
        style = sheet.default_style

    try:
        return render_class[style](
            sheet, title, data_source, tcommon, description=description,
            selectors=selectors, dyn_aggr=dyn_aggr, dyn_diff=dyn_diff).render()
    except Exception as e:
        # FIXME - Temporary debugging - should be removed before release.
        print e
        print "title:", title, "field_style:", style, "description:", \
            description
        traceback.print_exc()
        raise e
