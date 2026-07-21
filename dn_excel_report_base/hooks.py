from odoo import api


TYPE_FIELD_MAP = {
    # Font
    "font_name": "font_name",
    "font_size": "font_size",
    "font_color": "font_color",
    "bold": "bold",
    "italic": "italic",
    "underline": "underline",
    "font_strikeout": "font_strikeout",
    "font_script": "font_script",

    # Alignment
    "align": "align",
    "valign": "valign",
    "text_wrap": "text_wrap",
    "rotation": "rotation",
    "indent": "indent",

    # Border
    "border": "border",
    "border_color": "border_color",
    "top": "top",
    "top_color": "top_color",
    "bottom": "bottom",
    "bottom_color": "bottom_color",
    "left": "left",
    "left_color": "left_color",
    "right": "right",
    "right_color": "right_color",

    # Fill
    "pattern": "pattern",
    "bg_color": "bg_color",
    "fg_color": "fg_color",

    # Number
    "num_format": "num_format",

    # Protection
    "locked": "locked",
    "hidden": "hidden",
}


def _create_if_not_exists(Model, type_name, name, value):
    field_name = TYPE_FIELD_MAP[type_name]
    field = Model._fields[field_name]

    if field.type == "selection":
        value = str(value)

    domain = [
        ("type", "=", type_name),
        (field_name, "=", value),
    ]

    if Model.search(domain, limit=1):
        return

    vals = {
        "name": name,
        "type": type_name,
        field_name: value,
    }

    Model.create(vals)


def post_init_hook(env):
    Format = env["excel.report.format"]

    #
    # Font Family
    #

    fonts = [
        "Arial",
        "Calibri",
        "Times New Roman",
        "Tahoma",
        "Verdana",
        "Segoe UI",
        "Cambria",
        "Georgia",
        "Courier New",
        "Consolas",
    ]

    for font in fonts:
        _create_if_not_exists(
            Format,
            "font_name",
            font,
            font,
        )

    #
    # Font Size
    #

    for i in range(10, 31):
        _create_if_not_exists(
            Format,
            "font_size",
            str(i),
            i,
        )

    #
    # Font Color
    #

    colors = [
        "#000000",
        "#FFFFFF",
        "#FF0000",
        "#00FF00",
        "#0000FF",
        "#FFFF00",
        "#808080",
        "#FFA500",
    ]

    for color in colors:
        _create_if_not_exists(
            Format,
            "font_color",
            color,
            color,
        )

    #
    # Boolean
    #

    bool_fields = [
        "bold",
        "italic",
        "text_wrap",
        "font_strikeout",
        "locked",
        "hidden",
    ]

    for field in bool_fields:
        _create_if_not_exists(
            Format,
            field,
            "True",
            True,
        )

        _create_if_not_exists(
            Format,
            field,
            "False",
            False,
        )

    #
    # Underline
    #

    underline = {
        "None": 0,
        "Single": 1,
        "Double": 2,
        "Accounting Single": 33,
        "Accounting Double": 34,
    }

    for name, value in underline.items():
        _create_if_not_exists(
            Format,
            "underline",
            name,
            value,
        )

    #
    # Script
    #

    scripts = {
        "Normal": 0,
        "Superscript": 1,
        "Subscript": 2,
    }

    for name, value in scripts.items():
        _create_if_not_exists(
            Format,
            "font_script",
            name,
            value,
        )

    #
    # Alignment
    #

    aligns = [
        "left",
        "center",
        "right",
        "fill",
        "justify",
        "center_across",
        "distributed",
    ]

    for value in aligns:
        _create_if_not_exists(
            Format,
            "align",
            value.replace("_", " ").title(),
            value,
        )

    valigns = [
        "top",
        "vcenter",
        "bottom",
        "vjustify",
        "vdistributed",
    ]

    for value in valigns:
        _create_if_not_exists(
            Format,
            "valign",
            value,
            value,
        )

    #
    # Rotation
    #

    for value in [0, 45, 90, 270]:
        _create_if_not_exists(
            Format,
            "rotation",
            str(value),
            value,
        )

    #
    # Indent
    #

    for i in range(0, 11):
        _create_if_not_exists(
            Format,
            "indent",
            str(i),
            i,
        )

    #
    # Border Style
    #

    border_styles = {
        0: "None",
        1: "Thin",
        2: "Medium",
        3: "Dashed",
        4: "Dotted",
        5: "Thick",
        6: "Double",
        7: "Hair",
        8: "Medium Dashed",
        9: "Dash Dot",
        10: "Medium Dash Dot",
        11: "Dash Dot Dot",
        12: "Medium Dash Dot Dot",
        13: "Slanted Dash Dot",
    }

    border_fields = [
        "border",
        "top",
        "bottom",
        "left",
        "right",
    ]

    for field in border_fields:
        for value, name in border_styles.items():
            _create_if_not_exists(
                Format,
                field,
                name,
                value,
            )

    #
    # Border Colors
    #

    for field in [
        "border_color",
        "top_color",
        "bottom_color",
        "left_color",
        "right_color",
    ]:
        for color in colors:
            _create_if_not_exists(
                Format,
                field,
                color,
                color,
            )

    #
    # Pattern
    #

    patterns = {
        0: "None",
        1: "Solid",
        2: "Medium Gray",
        3: "Dark Gray",
        4: "Light Gray",
        5: "Dark Horizontal",
        6: "Dark Vertical",
        7: "Dark Down",
        8: "Dark Up",
        9: "Dark Grid",
        10: "Dark Trellis",
    }

    for value, name in patterns.items():
        _create_if_not_exists(
            Format,
            "pattern",
            name,
            value,
        )

    #
    # Fill Colors
    #

    for field in ["bg_color", "fg_color"]:
        for color in colors:
            _create_if_not_exists(
                Format,
                field,
                color,
                color,
            )

    #
    # Number Format
    #

    number_formats = [
        "General",
        "0",
        "0.00",
        "#,##0",
        "#,##0.00",
        "#,##0.000",
        "0%",
        "0.00%",
        "$#,##0.00",
        "€#,##0.00",
        "¥#,##0",
        "dd/mm/yyyy",
        "dd-mm-yyyy",
        "yyyy-mm-dd",
        "mm/dd/yyyy",
        "dd mmm yyyy",
        "dd/mm/yyyy hh:mm",
        "hh:mm",
        "hh:mm:ss",
        "0.00E+00",
        "@",
    ]

    for fmt in number_formats:
        _create_if_not_exists(
            Format,
            "num_format",
            fmt,
            fmt,
        )
