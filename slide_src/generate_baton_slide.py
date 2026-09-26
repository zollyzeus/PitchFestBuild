"""One-pager PPTX for the Baton pitch: concept, AI role, business value."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ---- palette ----
NAVY = RGBColor(0x1B, 0x23, 0x40)
NAVY_SOFT = RGBColor(0xCA, 0xDC, 0xFC)   # light ice-blue, for text on navy
CARD_BG = RGBColor(0xED, 0xF1, 0xF8)
AMBER = RGBColor(0xF2, 0xA9, 0x3B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x55, 0x5F, 0x75)

HEAD_FONT = "Cambria"
BODY_FONT = "Calibri"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = 13.333, 7.5

slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout


def no_line(shape):
    shape.line.fill.background()


def solid(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    no_line(shape)


def set_round_radius(shape, frac):
    """0..0.5 adjustment for ROUNDED_RECTANGLE corner radius."""
    try:
        shape.adjustments[0] = frac
    except Exception:
        pass


def add_text(x, y, w, h, text, size, color, bold=False, italic=False, font=BODY_FONT,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.0, wrap=True):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.name = font
        run.font.color.rgb = color
    return box


def add_bullets(x, y, w, h, items, size, color, font=BODY_FONT, space_after=6):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.line_spacing = 1.08
        p.space_after = Pt(space_after)
        r_bullet = p.add_run()
        r_bullet.text = "●  "
        r_bullet.font.size = Pt(size - 2)
        r_bullet.font.color.rgb = AMBER
        r_bullet.font.name = font
        r_bullet.font.bold = True
        r_text = p.add_run()
        r_text.text = item
        r_text.font.size = Pt(size)
        r_text.font.color.rgb = color
        r_text.font.name = font
    return box


# ---------------------------------------------------------------- header
header = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(SW), Inches(1.35))
solid(header, NAVY)
header.shadow.inherit = False

add_text(0.5, 0.20, 8.6, 0.62, "Baton", 34, WHITE, bold=True, font=HEAD_FONT)
add_text(0.5, 0.82, 8.6, 0.42,
         "Knowledge transfer you can prove is complete",
         15, NAVY_SOFT, italic=True, font=BODY_FONT)

badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(10.15), Inches(0.36), Inches(2.68), Inches(0.62))
solid(badge, AMBER)
set_round_radius(badge, 0.5)
badge.shadow.inherit = False
btf = badge.text_frame
btf.word_wrap = True
btf.vertical_anchor = MSO_ANCHOR.MIDDLE
btf.margin_left = Inches(0.05)
btf.margin_right = Inches(0.05)
btf.margin_top = 0
btf.margin_bottom = 0
p1 = btf.paragraphs[0]
p1.alignment = PP_ALIGN.CENTER
r1 = p1.add_run()
r1.text = "PITCHFEST 2026"
r1.font.size = Pt(11)
r1.font.bold = True
r1.font.name = BODY_FONT
r1.font.color.rgb = NAVY
p2 = btf.add_paragraph()
p2.alignment = PP_ALIGN.CENTER
p2.space_before = Pt(0)
r2 = p2.add_run()
r2.text = "ENTERPRISE AI TRACK"
r2.font.size = Pt(9)
r2.font.bold = True
r2.font.name = BODY_FONT
r2.font.color.rgb = NAVY

# ---------------------------------------------------------------- three columns
COL_Y = 1.65
COL_H = 4.85
COL_W = 3.9
GAP = 0.3
COL_X = [0.5, 0.5 + COL_W + GAP, 0.5 + 2 * (COL_W + GAP)]

titles = ["The problem", "How AI does it", "Business value"]


def card(cx):
    rect = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(cx), Inches(COL_Y), Inches(COL_W), Inches(COL_H))
    solid(rect, CARD_BG)
    set_round_radius(rect, 0.04)
    rect.shadow.inherit = False
    return rect


def badge_circle(cx, number):
    d = 0.6
    oval = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx + 0.3), Inches(COL_Y + 0.3), Inches(d), Inches(d))
    solid(oval, NAVY)
    oval.shadow.inherit = False
    tf = oval.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(number)
    r.font.size = Pt(22)
    r.font.bold = True
    r.font.color.rgb = WHITE
    r.font.name = BODY_FONT


for i, cx in enumerate(COL_X):
    card(cx)
    badge_circle(cx, i + 1)
    add_text(cx + 1.05, COL_Y + 0.30, COL_W - 1.35, 0.6, titles[i], 19, NAVY, bold=True,
              font=BODY_FONT, anchor=MSO_ANCHOR.MIDDLE)

# --- column 1: the problem
add_bullets(
    COL_X[0] + 0.3, COL_Y + 1.15, COL_W - 0.6, COL_H - 1.45,
    [
        "KT is a meeting and a checklist: the giver believes they explained, the taker believes they understood",
        "Nobody tests whether the two accounts match",
        "Gaps surface months later as incidents and slow ramp-up",
        "Project managers cannot see KT status, blockers or who is holding it up",
    ],
    14, NAVY,
)

# --- column 2: how AI does it
add_bullets(
    COL_X[1] + 0.3, COL_Y + 1.15, COL_W - 0.6, COL_H - 1.45,
    [
        "PM enters project, roles, stack, dev/test environments and duration",
        "AI writes tailored questions across 12 KT angles, separately for giver and taker",
        "Answers are recorded independently, then compared for gaps and mismatches",
        "Gaps become action items for giver or taker; their responses are reviewed",
        "Code decides: close, keep open for redress, or escalate",
    ],
    13.5, NAVY,
)

# --- column 3: business value (stats row + bullets)
STAT_Y = COL_Y + 1.15
stat_w = (COL_W - 0.6 - 2 * 0.15) / 3
stats = [("4/4", "planted gaps\ndetected"), ("97%", "final readiness,\nup from 57%"), ("0/8", "false alarms on\nsound angles")]
for j, (num, cap) in enumerate(stats):
    sx = COL_X[2] + 0.3 + j * (stat_w + 0.15)
    add_text(sx, STAT_Y, stat_w, 0.55, num, 26, AMBER, bold=True, font=HEAD_FONT,
              align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM)
    add_text(sx, STAT_Y + 0.55, stat_w, 0.5, cap, 9.5, MUTED, font=BODY_FONT,
              align=PP_ALIGN.CENTER)

add_bullets(
    COL_X[2] + 0.3, STAT_Y + 1.25, COL_W - 0.6, COL_H - (1.25 + STAT_Y - COL_Y) - 0.3,
    [
        "KT closes on evidence, not on a signed checklist",
        "Manager tracker: stage, day n of N, deadline, who each item waits on",
        "Full audit trail of questions, answers, actions and the decision",
    ],
    14, NAVY,
)

# ---------------------------------------------------------------- footer
add_text(
    0.5, 6.85, 12.333, 0.4,
    "Stack: Python · Streamlit · Google Gemini (structured output) · simulated giver and taker personas, one run, synthetic project · no GPU needed",
    10.5, MUTED, italic=True, font=BODY_FONT, align=PP_ALIGN.CENTER,
)


# ================================================================ slide 2: workflow
slide = prs.slides.add_slide(prs.slide_layouts[6])
hdr = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(SW), Inches(1.0))
solid(hdr, NAVY)
hdr.shadow.inherit = False
add_text(0.5, 0.12, 12.3, 0.5, "Baton workflow: from project brief to a closed, evidenced KT", 26, WHITE, bold=True, font=HEAD_FONT)
add_text(0.5, 0.63, 12.3, 0.3, "Independent giver and taker Q&A, gap assessment, action items, review, and a decision the manager can track",
         13, NAVY_SOFT, italic=True)

flow = [
    ("1 Brief", "PM enters project, roles, tech stack, dev/test env, duration, extra prompts"),
    ("2 Q&A", "Giver and taker answer separately. Round 1: 12 angles. Round 2: follow-ups on weak angles"),
    ("3 Assess", "AI compares both sides per angle; quotes verified in code; readiness scored"),
    ("4 Actions", "Gaps become action items for giver or taker; each replies with proof or a justification to ignore"),
    ("5 Review", "AI reviews responses; vague or weak justifications are rejected with a reason"),
    ("6 Decide", "Code rule: Close, keep open for one redress round, or Escalate to manager"),
]
FN = len(flow)
FG = 0.14
FW = (12.333 - (FN - 1) * FG) / FN
FY, FH = 1.22, 2.05
for i, (t, d) in enumerate(flow):
    fx = 0.5 + i * (FW + FG)
    r = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(fx), Inches(FY), Inches(FW), Inches(FH))
    solid(r, CARD_BG)
    set_round_radius(r, 0.05)
    r.shadow.inherit = False
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(fx), Inches(FY), Inches(FW), Inches(0.42))
    solid(bar, NAVY if i < FN - 1 else AMBER)
    bar.shadow.inherit = False
    add_text(fx + 0.12, FY + 0.04, FW - 0.2, 0.34, t, 13, WHITE if i < FN - 1 else NAVY, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    add_text(fx + 0.12, FY + 0.55, FW - 0.24, FH - 0.6, d, 10.5, NAVY)

add_text(0.5, FY + FH + 0.06, 12.333, 0.28,
         "Redress loop: unresolved items return to their owner once, with the reviewer's note. Still unresolved: escalated.",
         10.5, MUTED, italic=True, align=PP_ALIGN.CENTER)

cols = [
    ("Scoring and live eval", [
        "Readiness = weighted share of 12 angles: architecture, environments, CI/CD, incidents, security, in-flight work and more",
        "Covered only if both sides give verifiable quotes and the taker's answer matches the giver's",
        "Close needs every action accepted and readiness at or above the manager's target (default 80%)",
        "Live readiness trail: 57% → 66% → 95% → 97%; closed after 1 redress round",
    ]),
    ("Manager tracker", [
        "Every KT: stage, day n of N, deadline, days left, overdue flag",
        "Who each KT is waiting on: giver, taker or manager",
        "Action items across KTs with owner, severity, due date, state",
        "Timeline of stage changes, time in stage, readiness trend, override with a note",
    ]),
    ("AI, code and human", [
        "AI: writes the questions, compares answers, recommends actions, reviews responses",
        "Code: verifies quotes, scores readiness, applies the close / redress / escalate rule, tracks dates",
        "Giver and taker: answer independently; act on items or justify ignoring them",
        "Manager: sets inputs and target; owns escalations and overrides",
    ]),
]
CW3 = (12.333 - 2 * 0.2) / 3
CY3 = 3.72
for i, (t, items) in enumerate(cols):
    cx = 0.5 + i * (CW3 + 0.2)
    r = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(cx), Inches(CY3), Inches(CW3), Inches(3.05))
    solid(r, CARD_BG)
    set_round_radius(r, 0.04)
    r.shadow.inherit = False
    add_text(cx + 0.2, CY3 + 0.12, CW3 - 0.4, 0.34, t, 14, NAVY, bold=True)
    add_bullets(cx + 0.2, CY3 + 0.55, CW3 - 0.4, 2.4, items, 10.5, NAVY, space_after=4)

add_text(0.5, 6.95, 12.333, 0.3,
         "Eval: simulated giver and taker personas with 4 planted weak angles, one synthetic project, one run (69 s end to end). The target is a stopping rule, not proof of completeness.",
         9.5, MUTED, italic=True, align=PP_ALIGN.CENTER)

prs.save("Baton_One_Pager.pptx")
print("wrote Baton_One_Pager.pptx")
