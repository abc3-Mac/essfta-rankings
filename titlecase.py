#!/usr/bin/env python3
"""Title-Case ESSFTA conformation dog names and owners while preserving AKC
titles (CH, GCH, UDX, MACH, …) and Roman numerals in their official uppercase.

Only the conformation data needs this: those names/owners arrive ALL-CAPS from
the AKC reports. The Obedience/Agility/Rally ("sports") names are already
mixed-case in their source PDFs and must NOT be touched (don't .title()
"VinEwood" / "McGrady" / "O'Connor").

Public API:
    tc_name(s)   -> Title-Case a dog name, AKC titles & roman numerals kept caps
    tc_owner(s)  -> Title-Case an owner string, keeping initials/honorifics/* //
"""
import re

# ---- AKC title vocabulary (kept UPPERCASE) ----------------------------------
# Conformation prefixes + the full suffix-title system actually seen in the
# data. Numbered variants (UDX9, MACH3, OTCH4, RAE2, GCHP2, ACT2J, VCD3 …) are
# matched by regex, not enumerated. Anything not matched here is Title-Cased.
_TITLE_EXACT = {
    # championship prefixes
    "CH", "GCH", "GCHB", "GCHS", "GCHG", "GCHP", "DC", "NOHS", "FC", "AFC",
    "BIS", "BISS", "RBIS",
    # obedience
    "BN", "CD", "CDX", "UD", "GO", "OGM", "VER",
    # rally
    "RN", "RA", "RE", "RM", "RACH", "RAE",
    # agility – standard
    "NA", "NAJ", "OA", "OAJ", "AX", "AXJ", "MX", "MXJ", "MXB", "MXS", "MXG",
    "MXC", "MXP", "MJB", "MJS", "MJG", "MJC", "T2B", "T2BP", "TQX",
    "NF", "OF", "XF", "MXF", "NFP", "OFP", "XFP", "MFP",
    # agility – preferred
    "NAP", "OAP", "AXP", "MXP", "NJP", "OJP", "AJP", "MJP",
    # hunting / field
    "JH", "SH", "MH", "MHA", "MHB", "SHU", "JHU",
    # tracking
    "TD", "TDX", "TDU", "VST", "CT",
    # canine good citizen / trick
    "CGC", "CGCA", "CGCU", "CGCB", "TKN", "TKI", "TKA", "TKP", "TKE", "TKZ",
    # farm / coursing / dock / barn / earthdog
    "FDC", "BCAT", "DCAT", "FCAT", "CA", "CAA", "CAX",
    "DJ", "DM", "DS", "DSA", "DSX",          # dock (DS = Dock Senior etc.)
    "RATN", "RATO", "RATS", "RATM", "RATCH",
    # scent work
    "SCN", "SIN", "SEN", "SBN", "SHDN", "SCNW",
    "SCA", "SIA", "SEA", "SBA", "SHDA",
    "SCE", "SIE", "SEE", "SBE", "SHDE",
    "SWN", "SWA", "SWE", "SWM", "SWD", "SWAE", "SWB",
    # versatility / temperament / fitness / misc
    "VCD", "ATT", "ATTS", "FITS", "FITB", "ACT1", "ACT2", "ACT1J", "ACT2J",
    "VHMP", "VHMA", "VSWB", "VSWE", "BN-V",
    "PT", "HT", "HSAs", "HSAd", "HIAs", "HIAd",
}

# regex for titles carrying a trailing number/letter (UDX9, MACH3, GCHP2, RAE2,
# OTCH4, PACH2, ACT2J, VCD3, MXP5, MJB2, T2B3, NAP2 …) and Champion megatitles.
# Each agility family is enumerated precisely — a broad "starts with N/O/A/M/X"
# pattern wrongly swallows real words (A, ON, OFF, SEA…).
_TITLE_RE = re.compile(r"""^(?:
      (?:GCH[BSGP]?|UDX|CDX|CD|BN|RN|RAE|RACH|RA|RM|UD)\d*
    | (?:MACH|PACH|OTCH|TQX)\d*
    | (?:VCD|ATT|ACT1|ACT2)\d*[A-Z]?
    | (?:NAJ|NAP|NJP|NFP|NF|NA)\d*
    | (?:OAJ|OAP|OJP|OFP|OF|OA)\d*
    | (?:AXJ|AXP|AJP|XFP|XF|AX)\d*
    | (?:MXJ|MXP|MJP|MXB|MXS|MXG|MXC|MJB|MJS|MJG|MJC|MXF|MFP|MF|MX)\d*
    | (?:T2BP|T2B)\d*
    | (?:SCNW|SCN|SIN|SEN|SBN|SCA|SIA|SEA|SBA|SCE|SIE|SEE|SBE|SWN|SWA|SWE|SWM|SWD|SWB|SWAE)\d*
    | (?:RATN|RATO|RATS|RATM|RATCH)\d*
    | (?:CAA|CAX|BCAT|DCAT|FCAT)\d*
    | (?:TKN|TKI|TKA|TKP|TKE|TKZ)\d*
)$""", re.X)

# Roman numerals II..XX (call-name suffixes like "Polesitter II")
_ROMAN_RE = re.compile(r"^(?:II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV)$")

# Tokens that collide with common English words — only kept as a TITLE when an
# adjacent token is also a title (so "Seemore OF Me" -> "of", but "… MXF OF" at
# the end of a title run stays "OF").
_AMBIGUOUS = {"OF", "CA", "DS", "GO", "PT", "HT", "DM", "DJ", "VER",
              "SEA", "SEE", "SEN", "NA", "OA", "AX"}

# Minor words lowercased inside a Title-Cased name (never the first word).
_MINOR = {"a", "an", "the", "of", "and", "or", "nor", "but", "for", "to",
          "in", "on", "at", "by", "with", "from", "as", "into", "onto", "off",
          "out", "up", "n", "'n", "n'", "de", "du", "la", "le", "von", "van",
          "der", "den"}


def _is_title(tok, prev_is_title, next_tok, body_started):
    """Is this bare token an AKC title that should stay UPPERCASE?"""
    t = tok.strip(".,")
    if not t:
        return False
    up = t.upper()
    if up in _AMBIGUOUS:
        # A word that collides with English (OF, SEA, NA…) only counts as a title
        # inside a trailing title-run — never as the first body word right after a
        # CH/GCH prefix (e.g. "CH SEA Dog…" -> "Sea", but "…Miracle NA NAJ" -> "NA").
        if not body_started:
            return False
        nxt_up = (next_tok or "").strip(".,").upper()
        return prev_is_title or nxt_up in _TITLE_EXACT or bool(_TITLE_RE.match(nxt_up))
    if up in _TITLE_EXACT:
        return True
    if _TITLE_RE.match(up):
        return True
    return False


def _cap_word(w, is_first, is_last):
    """Title-case one ordinary word, honoring Mc/Mac, hyphens, apostrophes.
    Minor words (a, of, the…) stay lowercase unless first or last in the name."""
    low = w.lower()
    if not is_first and not is_last and low in _MINOR:
        return low
    return _cap_token(w)


_SEP_RE = re.compile(r"([\-‐‑–'’/])")   # ascii/unicode hyphens, apostrophes, slash


def _cap_first_alpha(p):
    """Uppercase the first alphabetic char, lowercase the rest. Leading quotes/
    punctuation are skipped so '"D"' -> '"D"' (not '"d"')."""
    chars = list(p.lower())
    for i, c in enumerate(chars):
        if c.isalpha():
            chars[i] = c.upper()
            break
    return "".join(chars)


def _cap_token(w):
    """Capitalize a single token, recursing through hyphen/apostrophe/slash
    separators and handling Mc/Mac prefixes."""
    parts = _SEP_RE.split(w)
    out = []
    for i, p in enumerate(parts):
        if p == "" or _SEP_RE.fullmatch(p):
            out.append(p)
            continue
        pl = p.lower()
        if pl.startswith("mc") and len(pl) > 2:
            out.append("Mc" + pl[2:].capitalize())
        elif pl.startswith("mac") and len(pl) > 3 and i == 0:
            out.append("Mac" + pl[3:].capitalize())
        elif i >= 2 and _SEP_RE.fullmatch(parts[i - 1] or "") and parts[i - 1] in "'’" and len(p) == 1:
            # after an apostrophe, a 1-char fragment (possessive 's) stays lower
            out.append(pl)
        else:
            out.append(_cap_first_alpha(p))
    return "".join(out)


def tc_name(s):
    """Title-Case a conformation dog name, keeping AKC titles + roman numerals."""
    if not s:
        return s
    toks = s.split()
    out = []
    first_word_done = False
    for i, tok in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        prev_is_title = bool(out) and out[-1] == out[-1].upper() and any(
            c.isalpha() for c in out[-1])
        if _ROMAN_RE.match(tok.upper()):
            out.append(tok.upper())
            continue
        if _is_title(tok, prev_is_title, nxt, first_word_done):
            out.append(tok.upper())
            continue
        # ordinary name word
        is_first = not first_word_done
        is_last = (i == len(toks) - 1)
        out.append(_cap_word(tok, is_first, is_last))
        first_word_done = True
    return " ".join(out)


# ---- owners -----------------------------------------------------------------
_HONORIFIC = {"jr", "sr", "ii", "iii", "iv", "phd", "dvm", "md", "esq",
              "mr", "mrs", "ms", "dr", "miss", "rev"}


def _cap_owner_tok(tok):
    """Capitalize one owner token: keep '*' marker, single-letter initials,
    honorifics, Mc/Mac, hyphen/apostrophe names."""
    star = ""
    if tok.startswith("*"):
        star, tok = "*", tok[1:]
    if not tok:
        return star
    base = tok.rstrip(".")
    dot = "." if tok.endswith(".") else ""
    low = base.lower()
    # single-letter initial -> uppercase ("k." -> "K.")
    if len(base) == 1 and base.isalpha():
        return star + base.upper() + dot
    if low in _HONORIFIC:
        # honorific: Title-case, roman-numeral honorifics all-caps
        if low in {"ii", "iii", "iv"}:
            return star + base.upper() + dot
        return star + base.capitalize() + dot
    return star + _cap_token(base) + dot


def tc_owner(s):
    """Title-Case an owner string, preserving initials, honorifics, '*' and '/'.

    Owners look like "*K. R. LORENTZEN/L. KIENER" or "*MS. L. O. NAIMO/*J. NAIMO, JR."
    Split on '/' (co-owners) and spaces; keep punctuation."""
    if not s:
        return s
    people = s.split("/")
    out_people = []
    for person in people:
        toks = person.split()
        out_people.append(" ".join(_cap_owner_tok(t) for t in toks))
    return "/".join(out_people)


if __name__ == "__main__":
    import json, os
    HERE = os.path.dirname(os.path.abspath(__file__))
    rows = json.load(open(os.path.join(HERE, "breed_group.json"), encoding="utf-8"))
    print("=== sample name + owner transforms ===")
    for r in rows[:25]:
        print(f"  {r['name']}\n   -> {tc_name(r['name'])}")
        print(f"     owner: {r['owner']}  ->  {tc_owner(r['owner'])}")
