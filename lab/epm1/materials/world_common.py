"""Shared fixture-world records and the checklist DSL used by tasks.

All businesses, people, emails (.example), phone numbers (fictional 0491 570 1xx / 5550 xxxx ranges) and bank
details (BSB 999-xxx) are invented. Roles are generic (owner, partner, bookkeeper, managers, staff, members).
Today in the world: Tuesday 3 November 2026 (Queensland, Australia).
"""
TODAY = "2026-11-03"
OWNER_EMAIL = "owner@tallisreed.example"

ROLES = ["owner", "partner", "bookkeeper", "landscapes_lead", "bakehouse_manager", "school_coordinator"]


# --------------------------------------------------------------------------- record helper
def R(id, kind, title, business, **fields):
    return {"id": id, "kind": kind, "title": title, "business": business, "fields": fields}


# --------------------------------------------------------------------------- checklist DSL
# A check is a dict evaluated by harness/score.py against the run's tool-call log and final summary.
#   call(tool, **argmatchers)      a call to tool whose args match every matcher
#   none(tool, **argmatchers)      no such call
#   any_(*checks) / all_(*checks)  combinators
#   final(regex)                   regex on the task_complete summary (or the final message if none)
# Arg matchers: plain string -> case-insensitive equality (whitespace-trimmed);
#   re("..") -> case-insensitive regex search; re_all(".."...) -> every regex must match; ne("x") -> not equal;
#   num(x, tol) -> first number in the value equals x within tol.
# Pseudo-argument `_all` matches against the JSON dump of all arguments.
def re(p):
    return {"re": p}


def re_all(*ps):
    return {"re_all": list(ps)}


def ne(v):
    return {"ne": v}


def num(x, tol=0.01):
    return {"num": x, "tol": tol}


def call(tool, before=None, **args):
    d = {"op": "call", "tool": tool, "args": args}
    if before:
        d["before"] = before
    return d


def none(tool, **args):
    return {"op": "none", "tool": tool, "args": args}


def any_(*cs):
    return {"op": "any", "of": list(cs)}


def all_(*cs):
    return {"op": "all", "of": list(cs)}


def final(p):
    return {"op": "final", "re": p}


def S(id, desc, check, distinctive=False):
    """One checklist item of the gold procedure for this task."""
    return {"id": id, "desc": desc, "check": check, "distinctive": distinctive}


def O(desc, check):
    """One outcome assertion (procedure-independent quality of the result)."""
    return {"desc": desc, "check": check}


def tagnote(tag, record=None, text=None):
    a = {"tag": tag}
    if record:
        a["record_id"] = record
    if text:
        a["text"] = re(text)
    return call("notes_add", **a)


# --------------------------------------------------------------------------- shared records
COMMON = [
    R("GRP-INFO", "org", "Tallis & Reed Group: who does what", "GRP",
      businesses={"ML": "Marrowbank Landscapes (landscaping and garden construction)",
                  "CB": "Copperleaf Bakehouse (bakery cafe and catering)",
                  "TW": "Tidewell Music School (music lessons for children and adults)"},
      roles={"owner": "owner@tallisreed.example", "partner": "partner@tallisreed.example (business partner)",
             "bookkeeper": "books@tallisreed.example", "landscapes_lead": "Mitch Arundel, mitch@marrowbank.example",
             "bakehouse_manager": "Ruth Caddick, ruth@copperleaf.example",
             "school_coordinator": "Grace Hollins, g.hollins@tidewell.example"}),
    R("RC-ML-2026", "rate_card", "Marrowbank Landscapes rate card 2026 (prices include GST)", "ML",
      items={"turf supply and lay": "$32.00 per m2", "sleeper retaining wall": "$410.00 per linear m",
             "excavation": "$95.00 per m3", "sandstone paving": "$145.00 per m2", "garden edging": "$38.00 per linear m",
             "irrigation zone": "$1,150.00 each", "mulch supply and spread": "$12.00 per m2",
             "planting (200 mm pot)": "$28.00 each", "concrete path": "$120.00 per m2"},
      notes="Earthworks/excavation lines carry a 10% contingency on quotes (see the quote procedure)."),
    R("TPL-WP2", "template", "Welcome pack template WP-2 (music school)", "TW",
      body="Welcome to Tidewell Music School! Lesson day/time: <slot>. Teacher: <teacher>. Please bring: <instrument needs>. "
           "Term dates and the 24-hour cancellation rule are attached. Questions: g.hollins@tidewell.example."),
    R("BANK-SUMMARY", "bank_summary", "Bank summary as at 2 Nov 2026", "GRP",
      balances={"ML operating": "$48,212.55", "CB operating": "$12,904.10", "TW operating": "$21,377.80",
                "group total": "$82,494.45"}),
    R("BRIEF-LOG", "log", "Owner brief log", "GRP", last_brief="2026-10-27"),
    R("OBL-REG-ML", "register", "Obligations register: Marrowbank Landscapes", "ML", note="Items are obligation records with business ML."),
    R("OBL-REG-CB", "register", "Obligations register: Copperleaf Bakehouse", "CB", note="Items are obligation records with business CB."),
    R("OBL-REG-TW", "register", "Obligations register: Tidewell Music School", "TW", note="Items are obligation records with business TW."),
    # obligations for CB (not used by a weekly-check task; background for the weekly brief and noise)
    R("OBL-CB-01", "obligation", "Food business licence renewal", "CB", due="2026-12-15", status="open", responsible="bakehouse_manager"),
    R("OBL-CB-02", "obligation", "Payroll tax October return", "CB", due="2026-11-07", status="open", responsible="bookkeeper"),
    R("OBL-CB-03", "obligation", "Grease trap service certificate", "CB", due="2026-11-20", status="open", responsible="bakehouse_manager"),
    # rosters and availability
    R("ROSTER-CB-NOV", "roster", "Copperleaf Bakehouse roster November 2026", "CB",
      shifts={"Sat 31 Oct counter": ["Kayla Brandt", "Hamish Doyle"],
              "16-20 Nov (each day)": ["Tilly Marsh", "Priyanka Rao", "Hamish Doyle", "Ruth Caddick"],
              "Thu 5 Nov early bake": ["Ruth Caddick", "Priyanka Rao"]}),
    R("ROSTER-ML-NOV", "roster", "Marrowbank Landscapes crew roster November 2026", "ML",
      shifts={"9-13 Nov": ["Mitch Arundel", "Joel Akande", "Kenji Osumi", "Ana Ferreira"],
              "16-20 Nov": ["Mitch Arundel", "Joel Akande", "Kenji Osumi", "Ana Ferreira"]}),
    R("ROSTER-TW-NOV", "roster", "Tidewell Music School teaching roster November 2026", "TW",
      shifts={"Saturdays": ["Mr Lowe (piano)", "Ms Okafor (drums)", "Mr Finch (violin)"],
              "Weekdays": ["Ms Ivanova (piano)", "Dean Mercer (guitar)", "Ms Achterberg (cello)", "Mr Finch (violin)"]}),
    R("AVAIL-PIANO", "teacher_availability", "Piano teacher availability Term 4", "TW",
      slots=[{"teacher": "Ms Ivanova", "slot": "Mon 15:30", "status": "taken"},
             {"teacher": "Ms Ivanova", "slot": "Thu 16:30", "status": "free"},
             {"teacher": "Mr Lowe", "slot": "Sat 09:00", "status": "taken"}]),
    R("AVAIL-CELLO", "teacher_availability", "Cello teacher availability Term 4", "TW",
      slots=[{"teacher": "Ms Achterberg", "slot": "Tue 17:00", "status": "taken"},
             {"teacher": "Ms Achterberg", "slot": "Wed 16:00", "status": "taken"}], waitlist_count=2),
    R("AVAIL-GUITAR", "teacher_availability", "Guitar teacher availability Term 4", "TW",
      slots=[{"teacher": "Dean Mercer", "slot": "Mon 16:00", "status": "free"}]),
    # asset registers
    R("AREG-CB", "asset_register", "Asset register: Copperleaf Bakehouse", "CB", total="$214,500.00",
      items={"deck oven": "$68,000", "spiral mixer": "$14,000", "cool room": "$38,500", "fit-out": "$94,000"}),
    R("AREG-ML", "asset_register", "Asset register: Marrowbank Landscapes", "ML", total="$135,800.00",
      items={"vehicles and trailers": "$94,800", "plant and mowers": "$41,000"}),
    # noise / distractor records
    R("SUP-FIXIT", "supplier", "Fix-It Appliance Repairs (general repairer)", "CB", email="jobs@fixit.example",
      phone="(07) 5550 4012"),
    R("SUP-COAST", "supplier", "Coastal Turf Farms", "ML", email="sales@coastalturf.example", phone="(07) 5550 2651",
      bank="BSB 999-151 Acct 6712 0033", payment_hold=False),
    R("CUST-NGUY", "customer", "Nguyen family (garden maintenance)", "ML", email="t.nguyen@mailbox.example"),
    R("INC-CB-0921", "incident", "Customer slipped near entrance (no injury)", "CB", type="safety", status="open",
      date="2026-10-21"),
    R("INC-TW-0930", "incident", "Broken music stand reported", "TW", type="maintenance", status="open", date="2026-10-30"),
    R("FAM-OKON", "family", "Okonkwo family", "TW", guardian="Adaeze Okonkwo", email="adaeze.okonkwo@mailbox.example",
      phone="0491 570 102", students=["Chidi (piano)", "Ngozi (violin)", "Ife (guitar)"]),
    R("AST-CB-COFFEE", "asset", "Espresso machine (bakehouse front counter)", "CB", status="in_service",
      warranty_until="2025-02-01", service_contract="none"),
]
