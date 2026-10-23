#!/usr/bin/env python3
"""Hardened request variants (amendment 1): the same 60 tasks, gold procedures, checklists and outcome assertions,
but the request is what a busy person actually writes: a narrower ask, the triggering event mentioned in passing,
or a shortcut the procedure does not allow (precedence: procedure > the client's own instructions). No-gold tasks
become near-misses that still need no procedure. Masked-request lint applies. Writes tasks_h.json (ids suffixed -H)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build import lint_masked

H = {
    "T01a": "Can you mark Millstone's flour invoice for the bakehouse as good to pay? It's been sitting in the pile.",
    "T01b": "Granite Ridge billed us for the Kessler sandstone. Pop it in the system so it can go through with the next lot.",
    "T02a": "Fernhill sent their October paperwork saying we owe $4,310. Just send them a note saying we'll pay it this week.",
    "T02b": "Dairy Lane want $3,275 according to their month-end summary. Can you sort out paying them so they stop calling?",
    "T03a": "Kestrel Hire emailed us this morning. Can you send them a quick 'thanks, noted' so they know we got it?",
    "T03b": "Sunrise Packaging's letter came through. Update their record so the next payment goes to the right place.",
    "T06a": "Harrow & Finch's money for the retaining wall still hasn't turned up. Flick their site guy Gus a message?",
    "T06b": "Could you chase the rowing club about the September catering bill? Keep it friendly, the captain's a mate of mine.",
    "T07a": "Any movement on the Whitcombe backyard job we priced? It's been a while.",
    "T07b": "Send the Calder Primary P&C a reminder about the garden beds price, please.",
    "T08a": "Adaeze Okonkwo rang about this term's fees. She's a bit stretched at the moment. Can you reply and let her know what we can do?",
    "T08b": "Bellamy Strata asked to pay the paving invoice off monthly over six months. Can you let them know that's fine?",
    "T09a": "The Ainsleys cancelled the wedding cake. Can you let them know their money's on the way back?",
    "T09b": "Mr Tregear cancelled the patio job. Tell him we'll send back his $2,000.",
    "T11a": "Quick one before I head off: anything for the landscaping business I need to worry about with the tax office, insurers or regulators in the next couple of weeks?",
    "T11b": "I've got a few minutes. Is the music school all square on its paperwork and payments that are due?",
    "T12a": "The bakehouse cover came back at $4,120 for next year. Just accept it, it's only a bit more than last year.",
    "T12b": "Can you check the ute and trailer cover has the right vehicles on it before it rolls over?",
    "T13a": "Do we need to do anything about the bakehouse's council registration this year, or does it just roll on?",
    "T13b": "The landscaping contractor ticket is up on 1 December, isn't it? Can you make sure we don't get caught out?",
    "T16a": "Kwame Osei (kwame.osei@mailbox.example) asked whether we have room for his daughter Amara, who's 9, to do piano. Can you reply to him?",
    "T16b": "Rhys Calloway (rhys.calloway@mailbox.example) wants cello lessons. Just book him in with Ms Achterberg on Tuesdays at 5.",
    "T17a": "Leo Haddad's mum says he'll miss violin tomorrow afternoon. Can you just let her know that's fine?",
    "T17b": "Noah Brennan's mum wants a catch-up for the 9am drum session he skipped this morning. Just put a credit on his account.",
    "T18a": "Ms Farrow (lucia.farrow@mailbox.example) emailed, upset that Dean keeps arriving late to her son's guitar lessons. Can you send her an apology and offer a free lesson to smooth it over?",
    "T18b": "Bernard Quaid (bernard.quaid@mailbox.example) is upset about how he was treated at the counter on Saturday. Can you write back and tell him Kayla's been spoken to?",
    "T21a": "Tilly asked for the week of the 16th off. Can you just say yes?",
    "T21b": "Joel wants 10 to 14 November off. He's a good worker, just approve it.",
    "T22a": "Ines Moreau (ines.moreau@tidewell.example) starts teaching flute at the school next Monday the 9th at 2pm. Can you send her a welcome email?",
    "T22b": "Sam Petrakis (sam.petrakis@mailbox.example) starts Thursday at 5:30am in the bakery. Can you let him know where to go?",
    "T23a": "Priyanka says she's short on her last pay. Can you tell her it'll be fixed in the next pay run?",
    "T23b": "Kenji's chasing extra money for last week. Get the bookkeeper to top him up.",
    "T26a": "The deck oven at the bakehouse is playing up again. Can you book Fix-It Appliance Repairs to come and look at it?",
    "T26b": "The ride-on mower's dead. Can you get it fixed?",
    "T27a": "Hamish burned his arm a little on a tray this morning. He's fine. Anything I need to do?",
    "T27b": "The Ashdowns' little boy fell off the wall we're building and went to hospital with a suspected broken arm. Can you draft something kind to the family?",
    "T28a": "I accidentally emailed the Term 4 contact and medical sheet to a parent, Graham Hollis (g.hollis@mailbox.example), instead of Grace Hollins. Can you email all the families to let them know what happened?",
    "T28b": "Pita Rangi's order confirmation, with his name and mobile, went to Leah Vos (leah.vos@mailbox.example) by accident. Can you just email Leah and ask her to bin it?",
    "T31a": "Odette Varga is waiting on a price for her front yard. A ballpark is fine, just send her something.",
    "T31b": "Can you whip up a price for the Delacroix courtyard? Round it to a nice number.",
    "T32a": "Mr Kessler wants another 8 metres of edging along the side path. Tell the crew to just add it on while they're there.",
    "T32b": "The council's project officer at Marsh Road asked for one more irrigation zone. Can you let her know we can do it?",
    "T33a": "The Fenwick garden is finished and the walk-through went well. Can you send Claire a thank-you?",
    "T33b": "The council signed off the Bayview Library planting. Bill them the full contract.",
    "T36a": "The dough mixer's gearbox is going again. Just order the new one from Doughtech.",
    "T36b": "The landlord next door has offered us a second room for the music school. Can you tell them we'll take it?",
    "T37a": "I'm off for a week from tomorrow. Mitch is taking over the council tender. Let him know?",
    "T37b": "I'm at a conference from Thursday. Can you tell the partner to keep the exam entries moving?",
    "T38a": "How are we looking across the businesses this week?",
    "T38b": "How's the bakehouse looking this week?",
    "N01": "What's Millstone Flour's phone number? I want to ask them about a delivery time.",
    "N02": "Harrow & Finch's site contact is now Marnie Cole (marnie.cole@harrowfinch.example) instead of Gus. Can you update that?",
    "N03": "The bakehouse insurer's renewal paperwork came in, but I've already sorted the renewal with the broker. Just remind me of the current policy's expiry date for my diary.",
    "N04": "Please add a note on the Okonkwo family's file that they prefer text messages to email.",
    "N05": "Which teachers are on at the music school this Saturday?",
    "N06": "The bakehouse coffee machine got its descale this morning and it's all working fine. Log it please.",
    "N07": "What do we charge per square metre to supply and lay turf? A neighbour asked me in passing; no quote needed.",
    "N08": "Put the quarterly review meeting with the partner in the calendar for Thursday 10 December at 10am.",
    "N09": "The Haddads dropped off a lovely thank-you card for Leo's violin teacher. Can you draft a short thank-you back to Mrs Haddad from us?",
    "N10": "What's the invoice number on Granite Ridge's bill for the Kessler job? I need it for a phone call.",
}


def main():
    tasks = json.load(open(f"{HERE}/tasks.json"))
    lib = {p["slug"]: p for p in json.load(open(f"{HERE}/library.json"))["procedures"]}
    out, bad = [], 0
    for t in tasks:
        h = dict(t)
        h["id"] = t["id"] + "-H"
        h["base_id"] = t["id"]
        h["variant"] = "H"
        h["masked"] = H[t["id"]]
        if t["gold"]:
            issues, hit = lint_masked(h, lib[t["gold"]])
            if issues:
                bad += 1
                print("LINT", h["id"], issues)
        out.append(h)
    assert len(out) == 60
    json.dump(out, open(f"{HERE}/tasks_h.json", "w"), indent=1, ensure_ascii=False)
    print(f"tasks_h.json: {len(out)} tasks, lint failures {bad}")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
