# -*- coding: utf-8 -*-
"""Vietnamese date/time formats for SCMD Pro.

This module is loaded via FORMAT_MODULE_PATH. It standardizes user-facing
Django/Admin/template formatting to dd/mm/yyyy while preserving ISO input
formats where browsers, URLs or API clients require them.
"""

DATE_FORMAT = "d/m/Y"
DATETIME_FORMAT = "d/m/Y H:i"
TIME_FORMAT = "H:i"
SHORT_DATE_FORMAT = "d/m/Y"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"
YEAR_MONTH_FORMAT = "m/Y"
MONTH_DAY_FORMAT = "d/m"
FIRST_DAY_OF_WEEK = 1

DATE_INPUT_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",  # HTML5 date input / API compatibility.
]
DATETIME_INPUT_FORMATS = [
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%Y-%m-%dT%H:%M",  # HTML5 datetime-local compatibility.
    "%Y-%m-%d %H:%M:%S",
]
