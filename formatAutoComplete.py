import sublime
import sublime_plugin
from string import Formatter
import re


def getStringRegion(view, region, around=False):
    """
    If region resides within a single string, return a Region which encompasses the whole
    string. Otherwise, returns the original region.
    """
    # Shrink the end by one unit, keeping a <= b, because we really care about the character
    # right before the end cursor, not after.
    region = sublime.Region(region.a, max(region.a, region.b - 1))

    # Mark sure the entire selected region lies within a quoted string
    for pos in range(region.a, region.b + 1):
        if view.score_selector(pos, "string.quoted") <= 0:
            return None

    # Turn on 'round' implicitly if...
    # The start of the selection is a quote
    if view.score_selector(region.a, "punctuation.definition.string") > 0:
        around = True
    # The end of the selection is a quote
    if view.score_selector(region.b, "punctuation.definition.string") > 0:
        around = True
    # The selected region is abutted by quotes on either side
    if (view.score_selector(region.a - 1, "punctuation.definition.string") > 0 and
        view.score_selector(region.b + 1, "punctuation.definition.string") > 0):
        around = True

    # Predicates for if we should continue expanding the selection foreward/back
    if around:
        # We should only stop when we're on a quote, but the next character isn't a quote
        shouldExpandA = lambda a:((not (view.score_selector(a, "punctuation.definition.string") > 0 and not view.score_selector(a - 1, "punctuation.definition.string") > 0)) and (view.score_selector(a - 1, "string.quoted") > 1))
        shouldExpandB = lambda b:((not (view.score_selector(b - 1, "punctuation.definition.string") > 0 and not view.score_selector(b, "punctuation.definition.string") > 0)) and (view.score_selector(b, "string.quoted") > 1))
    else:
        # We should only stop as soon as we see a quote
        shouldExpandA = lambda a:((not view.score_selector(a - 1, "punctuation.definition.string") > 0) and (view.score_selector(a - 1, "string.quoted") > 1))
        shouldExpandB = lambda b:((not view.score_selector(b, "punctuation.definition.string") > 0) and (view.score_selector(b, "string.quoted") > 1))

    # Expand the selection by expanding the start, then the end
    expandedRegion = sublime.Region(region.a, region.b)
    expandedA = region.a
    expandedB = region.b
    while shouldExpandA(expandedA):
        expandedA = expandedA - 1
    while shouldExpandB(expandedB):
        expandedB = expandedB + 1

    return sublime.Region(expandedA, expandedB)


def createKwdArgsFromStr(st):
    """Takes a string that will be formatted using <string>.format(...)
    and returns the keyword arguments.

    For example, you have this string
    st = "Hello, my name is {name} and I'm {age} years old"
    This plugin will parse the string, and create the format keyword arguments
    createKwdArgsFromStr(st) -> 'name=, age='
    """
    parsed = Formatter().parse(st)
    keys = list({t[1] for t in parsed if t[1] is not None})
    for i in range(len(keys)):
        if re.match('\d+', keys[i]):
            # non kwd args should be left blank
            keys[i] = ""

    things = []
    for idx, k in enumerate(keys):
        if k == "":
            things.append("${i}".format(i=idx + 1))
        else:
            things.append(k + "=${i}".format(i=idx + 1))

    return ", ".join(things)


class FormatAutocompleteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        region = self.view.sel()[0]

        region = region if region.a <= region.b else sublime.Region(region.b, region.a)
        stRegion = getStringRegion(self.view, region, False)

        if stRegion is not None:
            stRegion = stRegion if region.a <= region.b else sublime.Region(stRegion.b, stRegion.a)

        if stRegion:
            st = self.view.substr(stRegion)
            kwd = createKwdArgsFromStr(st)
            if len(kwd) > 0:
                fmt = ".format({kwd})".format(kwd=kwd)

                self.view.sel().clear()
                self.view.sel().add(stRegion.b + 1)
                self.view.run_command("insert_snippet", {
                    "contents": fmt
                })
